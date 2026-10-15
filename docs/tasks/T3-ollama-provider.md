# T3 — Ollama (local) LLM provider 🤝

**Branch:** `t3-ollama-provider` · **Size:** M · **Depends on:** Phase 1

## Goal
Implement `LLMProvider` (SPEC §9) against a **local** Ollama v0.12.3 server running
`qwen2.5:1.5b`. This is the "privacy mode": no answer text leaves the machine.

## Read first
- `docs/SPEC.md` §5, §6 (F5, F6), §7 (Local-only LLM, latency), §9, §12, §14
- `app/contracts.py`, `app/config.py` (loopback guard), `app/rubric.py`, `app/llm/mock.py`

## You own
- `app/llm/ollama.py`
- `tests/test_llm_ollama.py`

## Do not edit
Everything else, **especially `app/contracts.py`** and `app/prompts/`.

## Requirements
- Use `httpx.AsyncClient` against `settings.ollama_url`.
  **Re-check the loopback guard** before every request: refuse if the host isn't
  `127.0.0.1`, `localhost` or `::1`.
- **Assess:** `POST /api/chat` with `stream: false`, `format` = the JSON schema for
  `Assessment`, `options: {temperature: 0.2, num_ctx: 8192}`. Validate with Pydantic. Retry
  once on failure, with the validation error included in the retry message.
- Small-model robustness:
  - clamp scores to 1–5;
  - if a dimension is missing, add it with score 1 and an empty quote;
  - trim lists to the spec's maximums.
  Document each repair in a code comment.
- **Follow-up:** a plain-text call. Take the first question sentence and cap it at 40
  words.
- **Role-aware:** both methods take the `RoleProfile` (SPEC §5.4, §9) and pass it to the
  prompt builders in `app/rubric.py`. Don't build prompt text in this module. The LLM
  never calculates the fit %.
- **Evidence guard:** the same as T2. Blank quotes that aren't in the transcripts.
- Timeout from `settings.ollama_timeout_s` (240s by default).
- `reachable()` helper: `GET /api/tags`, returning True if the model is listed. Used by
  `/api/health`.
- `LLMUsage`: use `prompt_eval_count` and `eval_count` from the response, plus the
  duration. Cost is $0.

## Acceptance criteria
- [ ] Tests (`respx`): valid output, invalid then valid retry, the repair cases, a
      non-loopback URL being refused, timeout, and `reachable()` true and false.
- [ ] `make check` passes.
- [ ] Optional manual check, if Ollama is running: `make eval PROVIDER=ollama`. Report the
      timings.

## Prompt to paste
```
You are working on the AI Role Fitter repo. Read docs/SPEC.md and
docs/tasks/T3-ollama-provider.md, then complete task T3 exactly as briefed.
Only edit the files listed under "You own". Never edit app/contracts.py or
app/prompts/; if the contract seems wrong, stop and tell me. Never point the
provider at a non-loopback host. Do not read or print .env. Use respx in tests.
When finished, run `make check`, fix any failures, and give me a short summary:
what you built, test results, timings if you ran it locally, and anything the
lead session needs to wire up.
```
