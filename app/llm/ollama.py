"""Ollama (local) LLM provider (SPEC §9, §11): privacy mode, nothing leaves this machine.

Talks to a local Ollama server over loopback only. A small model gets the JSON schema via
Ollama's `format` option, then the output is repaired and validated by Pydantic.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx
from pydantic import ValidationError

from app.config import Settings, ensure_loopback_url
from app.contracts import (
    DIMENSION_IDS,
    Answer,
    Assessment,
    DimensionId,
    LLMError,
    LLMUsage,
    RoleProfile,
)
from app.llm.claude import guard_evidence
from app.rubric import build_assess_prompt, build_follow_up_prompt

MAX_FOLLOW_UP_WORDS = 40
FOLLOW_UP_MAX_TOKENS = 120
OPTIONS: dict[str, Any] = {"temperature": 0.2, "num_ctx": 8192}

_STRING = {"type": "string"}
_DIMENSION = {"type": "string", "enum": list(DIMENSION_IDS)}

# Hand-written to match `Assessment`. List lengths aren't in the schema (small models cope
# badly with them); `_repair` and Pydantic enforce them instead.
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
                    "score": {"type": "integer"},
                    "evidence_quote": _STRING,
                    "rationale": _STRING,
                },
                "required": ["dimension_id", "score", "evidence_quote", "rationale"],
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
            },
        },
    },
    "required": ["summary", "dimensions", "strengths", "gaps", "recommendations"],
}

_MAX_ITEMS = {"strengths": 3, "gaps": 3, "recommendations": 5}


def _repair(data: Any) -> Any:
    """Fix the slips a small model makes, before Pydantic validates. Each repair is noted."""
    if not isinstance(data, dict):
        return data

    # Repair 1: drop dimensions with an unknown id, and duplicates (keep the first).
    # Repair 2: clamp each score to 1-5 (a non-numeric score becomes 1).
    # Repair 3: add any missing dimension with score 1 and an empty quote.
    seen: dict[str, dict[str, Any]] = {}
    raw_dims = data.get("dimensions")
    for item in raw_dims if isinstance(raw_dims, list) else []:
        if not isinstance(item, dict) or item.get("dimension_id") not in DIMENSION_IDS:
            continue
        if item["dimension_id"] in seen:
            continue
        try:
            score = round(float(item.get("score")))
        except (TypeError, ValueError):
            score = 1
        seen[item["dimension_id"]] = {
            **item,
            "score": max(1, min(5, score)),
            "evidence_quote": item.get("evidence_quote") or "",
            "rationale": item.get("rationale") or "No rationale given.",
        }
    for dimension_id in DIMENSION_IDS:
        seen.setdefault(
            dimension_id,
            {
                "dimension_id": dimension_id,
                "score": 1,
                "evidence_quote": "",
                "rationale": "The model gave no score for this dimension.",
            },
        )
    data = {**data, "dimensions": [seen[d] for d in DIMENSION_IDS]}

    # Repair 4: trim strengths, gaps and recommendations to the spec's maximums.
    for key, limit in _MAX_ITEMS.items():
        if isinstance(data.get(key), list):
            data[key] = data[key][:limit]
    return data


def _first_question(text: str) -> str:
    """Take the first question sentence from free text and cap it at 40 words."""
    text = " ".join(text.split()).strip(" \"'`*")
    sentences = [s.strip() for s in re.findall(r"[^.!?]*[.!?]+[\"']?|[^.!?]+$", text) if s.strip()]
    chosen = next((s for s in sentences if s.rstrip("\"'").endswith("?")), None)
    if chosen is None:
        chosen = sentences[0] if sentences else ""
    chosen = chosen.strip(" \"'`*")
    words = chosen.split()
    if len(words) > MAX_FOLLOW_UP_WORDS:
        chosen = " ".join(words[:MAX_FOLLOW_UP_WORDS]).rstrip(",;:.") + "?"
    return chosen


class OllamaLLM:
    name = "ollama"

    def __init__(self, settings: Settings):
        self._url = ensure_loopback_url(settings.ollama_url).rstrip("/")
        self.model = settings.ollama_model
        self._timeout = settings.ollama_timeout_s

    async def reachable(self) -> bool:
        """True if the server answers and the configured model is pulled."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await self._send(client, "GET", "/api/tags")
            names = {m.get("name") for m in response.json().get("models", [])}
        except (LLMError, httpx.HTTPError, ValueError, AttributeError):
            return False
        return self.model in names or f"{self.model}:latest" in names

    async def follow_up(
        self, answers: list[Answer], role: RoleProfile
    ) -> tuple[str, DimensionId | None, LLMUsage]:
        system, user = build_follow_up_prompt(answers, role)
        user += "\n\nReply with the question only, as a single sentence."
        start = time.perf_counter()
        usage = LLMUsage(input_tokens=0, output_tokens=0)
        body = await self._chat(system, user, usage, extra={"num_predict": FOLLOW_UP_MAX_TOKENS})
        question = _first_question(body["message"]["content"])
        if not question:
            raise LLMError("llm_invalid_output", "The local model returned no question.")
        usage.duration_ms = int((time.perf_counter() - start) * 1000)
        # A plain-text reply doesn't name its target dimension, so none is reported.
        return question, None, usage

    async def assess(self, answers: list[Answer], role: RoleProfile) -> tuple[Assessment, LLMUsage]:
        system, user = build_assess_prompt(answers, role)
        start = time.perf_counter()
        usage = LLMUsage(input_tokens=0, output_tokens=0)
        message = user
        for attempt in range(2):
            body = await self._chat(system, message, usage, schema=ASSESSMENT_SCHEMA)
            content = body["message"]["content"]
            try:
                assessment = Assessment.model_validate(_repair(json.loads(content)))
                break
            except (json.JSONDecodeError, ValidationError) as exc:
                if attempt == 1:
                    raise LLMError(
                        "llm_invalid_output",
                        "The local model returned an answer in the wrong format twice. "
                        "Please try again.",
                    ) from exc
                message = (
                    f"{user}\n\nYour previous reply was not valid: {str(exc)[:600]}\n"
                    "Reply again with corrected JSON only."
                )
        usage.duration_ms = int((time.perf_counter() - start) * 1000)
        return guard_evidence(assessment, answers), usage

    async def _chat(
        self,
        system: str,
        user: str,
        usage: LLMUsage,
        *,
        schema: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {**OPTIONS, **(extra or {})},
        }
        if schema is not None:
            payload["format"] = schema
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await self._send(client, "POST", "/api/chat", json=payload)
        try:
            body = response.json()
            body["message"]["content"]  # noqa: B018 — checks the shape
        except (ValueError, KeyError, TypeError) as exc:
            raise LLMError(
                "ollama_bad_response", "The local model sent a reply we couldn't read."
            ) from exc
        # Ollama reports token counts per call; add them up across a retry.
        usage.input_tokens = (usage.input_tokens or 0) + int(body.get("prompt_eval_count") or 0)
        usage.output_tokens = (usage.output_tokens or 0) + int(body.get("eval_count") or 0)
        return body

    async def _send(
        self, client: httpx.AsyncClient, method: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        # Re-checked before every request, not just at construction.
        url = ensure_loopback_url(self._url) + path
        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMError(
                "ollama_timeout", "The local model took too long to respond. Please retry."
            ) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise LLMError(
                    "ollama_model_missing",
                    f"The local model isn't installed. Run: ollama pull {self.model}",
                ) from exc
            raise LLMError("ollama_error", "The local model returned an error.") from exc
        except httpx.HTTPError as exc:
            raise LLMError(
                "ollama_unreachable", "Couldn't reach the local model. Is Ollama running?"
            ) from exc
        return response
