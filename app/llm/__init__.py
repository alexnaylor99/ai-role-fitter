"""LLM provider factory, cost estimates and the in-memory response cache.

Providers are imported lazily so a missing one fails clearly.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict

from app.config import Settings, ensure_loopback_url
from app.contracts import (
    Answer,
    Assessment,
    ConfigError,
    DimensionId,
    LLMProvider,
    LLMUsage,
    ProviderName,
    RoleProfile,
)
from app.rubric import build_assess_prompt, build_follow_up_prompt

# USD per million tokens (input, output). Local and mock providers cost nothing.
PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),  # prompts up to 100k tokens, which ours always are
    "claude-haiku-4-5": (1.0, 5.0),
}
CACHE_READ_RATE = 0.1  # prompt-cache hits cost 10% of the input price
CACHE_WRITE_RATE = 1.25  # 5-minute prompt-cache writes cost 125% of the input price


def estimate_cost(model: str, usage: LLMUsage) -> float:
    rates = PRICING.get(model)
    if not rates or usage.input_tokens is None or usage.output_tokens is None:
        return 0.0
    input_rate, output_rate = rates
    total = (
        usage.input_tokens * input_rate
        + (usage.cache_read_tokens or 0) * input_rate * CACHE_READ_RATE
        + (usage.cache_write_tokens or 0) * input_rate * CACHE_WRITE_RATE
        + usage.output_tokens * output_rate
    )
    return round(total / 1_000_000, 6)


# --- Response cache ------------------------------------------------------------------
# Identical answers + identical prompts give the same result, so a repeat (a demo
# rehearsal, a re-run with the same pre-filled answers) costs nothing and returns
# instantly — on the local model that saves ~3 minutes. Kept in memory only, never on
# disk, so transcripts are not persisted (SPEC §7 Privacy). Cleared on restart.

RESPONSE_CACHE_SIZE = 32
_response_cache: OrderedDict[str, tuple] = OrderedDict()


def _cache_key(kind: str, provider: LLMProvider, answers: list[Answer], role: RoleProfile) -> str:
    build = build_assess_prompt if kind == "assess" else build_follow_up_prompt
    system, user = build(answers, role)
    raw = json.dumps([kind, provider.name, provider.model, system, user])
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(key: str):
    if key in _response_cache:
        _response_cache.move_to_end(key)
        return _response_cache[key]
    return None


def _cache_put(key: str, value: tuple) -> None:
    _response_cache[key] = value
    _response_cache.move_to_end(key)
    while len(_response_cache) > RESPONSE_CACHE_SIZE:
        _response_cache.popitem(last=False)


def clear_response_cache() -> None:
    _response_cache.clear()


class CachedLLM:
    """Wraps a real provider with the in-memory response cache."""

    def __init__(self, inner: LLMProvider):
        self._inner = inner
        self.name = inner.name
        self.model = inner.model

    def __getattr__(self, attr: str):  # e.g. reachable()
        return getattr(self._inner, attr)

    async def follow_up(
        self, answers: list[Answer], role: RoleProfile
    ) -> tuple[str, DimensionId | None, LLMUsage]:
        key = _cache_key("follow_up", self._inner, answers, role)
        if (hit := _cache_get(key)) is not None:
            return hit[0], hit[1], LLMUsage(input_tokens=0, output_tokens=0, cached_response=True)
        question, dimension_id, usage = await self._inner.follow_up(answers, role)
        _cache_put(key, (question, dimension_id))
        return question, dimension_id, usage

    async def assess(self, answers: list[Answer], role: RoleProfile) -> tuple[Assessment, LLMUsage]:
        key = _cache_key("assess", self._inner, answers, role)
        if (hit := _cache_get(key)) is not None:
            usage = LLMUsage(input_tokens=0, output_tokens=0, cached_response=True)
            return hit[0].model_copy(deep=True), usage
        assessment, usage = await self._inner.assess(answers, role)
        _cache_put(key, (assessment.model_copy(deep=True),))
        return assessment, usage


def get_llm(name: ProviderName, settings: Settings) -> LLMProvider:
    if name == "mock":
        from app.llm.mock import MockLLM

        return MockLLM()  # instant and free: no cache needed

    if name == "claude":
        if not settings.claude_key_set:
            raise ConfigError(
                "claude_not_configured", "Claude mode needs ANTHROPIC_API_KEY in .env."
            )
        try:
            from app.llm.claude import ClaudeLLM
        except ImportError as exc:
            raise ConfigError("claude_not_available", "Claude mode isn't built yet.") from exc
        return CachedLLM(ClaudeLLM(settings))

    if name == "ollama":
        ensure_loopback_url(settings.ollama_url)
        try:
            from app.llm.ollama import OllamaLLM
        except ImportError as exc:
            raise ConfigError("ollama_not_available", "Local mode isn't built yet.") from exc
        return CachedLLM(OllamaLLM(settings))

    raise ConfigError("unknown_provider", f"Unknown LLM provider: {name}", status_code=400)
