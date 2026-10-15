"""LLM provider factory. Providers are imported lazily so a missing one fails clearly."""

from __future__ import annotations

from app.config import Settings, ensure_loopback_url
from app.contracts import ConfigError, LLMProvider, ProviderName

# USD per million tokens (input, output). Local and mock providers cost nothing.
PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
}


def estimate_cost(model: str, input_tokens: int | None, output_tokens: int | None) -> float:
    rates = PRICING.get(model)
    if not rates or input_tokens is None or output_tokens is None:
        return 0.0
    return round((input_tokens * rates[0] + output_tokens * rates[1]) / 1_000_000, 4)


def get_llm(name: ProviderName, settings: Settings) -> LLMProvider:
    if name == "mock":
        from app.llm.mock import MockLLM

        return MockLLM()

    if name == "claude":
        if not settings.claude_key_set:
            raise ConfigError(
                "claude_not_configured", "Claude mode needs ANTHROPIC_API_KEY in .env."
            )
        try:
            from app.llm.claude import ClaudeLLM
        except ImportError as exc:
            raise ConfigError("claude_not_available", "Claude mode isn't built yet.") from exc
        return ClaudeLLM(settings)

    if name == "ollama":
        ensure_loopback_url(settings.ollama_url)
        try:
            from app.llm.ollama import OllamaLLM
        except ImportError as exc:
            raise ConfigError("ollama_not_available", "Local mode isn't built yet.") from exc
        return OllamaLLM(settings)

    raise ConfigError("unknown_provider", f"Unknown LLM provider: {name}", status_code=400)
