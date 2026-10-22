"""Claude LLM provider (SPEC §9, §11): structured outputs, refusal fallbacks, one retry."""

from __future__ import annotations

import json
import time
from typing import Any

import anthropic
from pydantic import BaseModel, ValidationError, field_validator

from app.config import Settings
from app.contracts import (
    DIMENSION_IDS,
    Answer,
    Assessment,
    DimensionId,
    LLMError,
    LLMUsage,
    RoleProfile,
)
from app.llm.evidence import guard_evidence
from app.rubric import build_assess_prompt, build_follow_up_prompt

# Server-side refusal fallbacks: `fallbacks: "default"` is gated by this beta header.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
ASSESS_MAX_TOKENS = 16000
FOLLOW_UP_MAX_TOKENS = 4000
MAX_FOLLOW_UP_WORDS = 40

_STRING = {"type": "string"}
_DIMENSION = {"type": "string", "enum": list(DIMENSION_IDS)}

# Hand-written to match `Assessment`. Structured outputs don't support minItems/maxItems,
# so list lengths and "one score per dimension" are enforced by Pydantic (with a retry).
ASSESSMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": _STRING,
        "dimensions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dimension_id": _DIMENSION,
                    "score": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
                    "evidence_quote": _STRING,
                    "rationale": _STRING,
                },
                "required": ["dimension_id", "score", "evidence_quote", "rationale"],
                "additionalProperties": False,
            },
        },
        "strengths": {"type": "array", "items": _STRING},
        "gaps": {"type": "array", "items": _STRING},
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": _STRING,
                    "why": _STRING,
                    "first_step": _STRING,
                    "dimension_id": _DIMENSION,
                    "effort": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["title", "why", "first_step", "dimension_id", "effort"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "dimensions", "strengths", "gaps", "recommendations"],
    "additionalProperties": False,
}

FOLLOW_UP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": _STRING,
        "dimension_id": {"anyOf": [_DIMENSION, {"type": "null"}]},
    },
    "required": ["question", "dimension_id"],
    "additionalProperties": False,
}


class _FollowUp(BaseModel):
    question: str
    dimension_id: DimensionId | None = None

    @field_validator("question")
    @classmethod
    def _short_question(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v.split()) > MAX_FOLLOW_UP_WORDS:
            raise ValueError(f"question must be 1-{MAX_FOLLOW_UP_WORDS} words")
        return v


class ClaudeLLM:
    name = "claude"

    def __init__(self, settings: Settings, client: anthropic.AsyncAnthropic | None = None):
        self.model = settings.claude_model
        if client is None:
            key = settings.anthropic_api_key
            client = anthropic.AsyncAnthropic(api_key=key.get_secret_value() if key else None)
        self._client = client

    async def follow_up(
        self, answers: list[Answer], role: RoleProfile
    ) -> tuple[str, DimensionId | None, LLMUsage]:
        system, user = build_follow_up_prompt(answers, role)
        result, usage = await self._structured(
            system, user, FOLLOW_UP_SCHEMA, _FollowUp, effort="low", max_tokens=FOLLOW_UP_MAX_TOKENS
        )
        return result.question, result.dimension_id, usage

    async def assess(self, answers: list[Answer], role: RoleProfile) -> tuple[Assessment, LLMUsage]:
        system, user = build_assess_prompt(answers, role)
        result, usage = await self._structured(
            system,
            user,
            ASSESSMENT_SCHEMA,
            Assessment,
            effort="medium",
            max_tokens=ASSESS_MAX_TOKENS,
        )
        return guard_evidence(result, answers), usage

    async def _structured[T: BaseModel](
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        model_cls: type[T],
        *,
        effort: str,
        max_tokens: int,
    ) -> tuple[T, LLMUsage]:
        """Call Claude with a JSON schema; validate with Pydantic; retry once if invalid."""
        start = time.perf_counter()
        usage = LLMUsage(input_tokens=0, output_tokens=0)
        for attempt in range(2):
            text = await self._call(system, user, schema, effort, max_tokens, usage)
            try:
                result = model_cls.model_validate(json.loads(text))
                break
            except (json.JSONDecodeError, ValidationError) as exc:
                if attempt == 1:
                    raise LLMError(
                        "llm_invalid_output",
                        "Claude returned an answer in the wrong format twice. Please try again.",
                    ) from exc
        usage.duration_ms = int((time.perf_counter() - start) * 1000)
        return result, usage

    async def _call(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        effort: str,
        max_tokens: int,
        usage: LLMUsage,
    ) -> str:
        try:
            response = await self._client.beta.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={
                    "effort": effort,
                    "format": {"type": "json_schema", "schema": schema},
                },
                fallbacks="default",
                betas=[FALLBACK_BETA],
            )
        except anthropic.AuthenticationError as exc:
            raise LLMError(
                "claude_auth", "Claude rejected the API key. Check ANTHROPIC_API_KEY in .env."
            ) from exc
        except anthropic.PermissionDeniedError as exc:
            raise LLMError("claude_permission", "This API key can't use the Claude model.") from exc
        except anthropic.RateLimitError as exc:
            raise LLMError(
                "claude_rate_limited", "Claude is rate limited right now. Wait a minute and retry."
            ) from exc
        except anthropic.APITimeoutError as exc:
            raise LLMError(
                "claude_timeout", "Claude took too long to respond. Please retry."
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError(
                "claude_unreachable", "Couldn't reach Claude. Check your internet connection."
            ) from exc
        except anthropic.APIStatusError as exc:
            if exc.status_code >= 500:
                raise LLMError(
                    "claude_unavailable", "Claude is having problems right now. Please retry."
                ) from exc
            raise LLMError("claude_bad_request", "Claude couldn't process the request.") from exc

        usage.input_tokens = (usage.input_tokens or 0) + response.usage.input_tokens
        usage.output_tokens = (usage.output_tokens or 0) + response.usage.output_tokens

        if response.stop_reason == "refusal":
            raise LLMError(
                "claude_refusal", "Claude declined to assess these answers. Try rephrasing them."
            )
        if response.stop_reason == "max_tokens":
            raise LLMError(
                "claude_max_tokens", "Claude's answer was cut off before it finished. Please retry."
            )
        return "".join(b.text for b in response.content if b.type == "text")
