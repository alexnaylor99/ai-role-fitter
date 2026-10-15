# AI Role Fitter — notes for Claude Code agents

Voice interview (ElevenLabs STT/TTS) → LLM scoring (Claude / local Ollama / mock) →
deterministic role fit against the ElevenLabs FDE role → visual report.

## Read first
- `docs/SPEC.md` is the source of truth. `docs/PLAN.md` says who owns what.
- If you were given a task brief in `docs/tasks/`, follow it exactly.

## Hard rules
- **Never edit `app/contracts.py`.** Only the lead session changes it. If a contract seems
  wrong, stop and report it.
- Only edit the files your task brief says you own.
- **Never read, print or commit `.env` or any API key.** Keys stay server-side.
- Tests make **no real network calls**: fake HTTP with `respx`. CI has no keys.
- The local model must only ever be reached on a loopback host (`ensure_loopback_url`).
- Report data comes from an LLM: render it with `textContent`, never `innerHTML`.
- The LLM scores; Python computes the level and the role fit (`app/fit.py`).

## Commands
- `make setup` once, then `make dev` (http://127.0.0.1:8000).
- `make check` must pass before you finish (ruff, format, pytest, secret scan).
- `make fmt` fixes lint and formatting.
- `make eval PROVIDER=mock|claude|ollama` runs the eval personas.

## Conventions
- Python 3.12, FastAPI, Pydantic v2, httpx (async). British English in user-facing text.
- Providers are constructed with the settings object: `ClaudeLLM(settings)`,
  `OllamaLLM(settings)`, `ElevenLabsVoice(settings)`; factories live in `app/llm/__init__.py`
  and `app/voice/__init__.py`.
- Raise `LLMError` / `VoiceError` / `ConfigError` (from `app/contracts.py`) with a
  user-safe message; the API turns them into `{error: {code, message}}`.
- An optional `async def reachable(self) -> bool` on a provider is used by `/api/health`.
