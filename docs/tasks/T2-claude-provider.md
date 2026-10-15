# T2 — Claude LLM provider 🤝

**Branch:** `t2-claude-provider` · **Size:** M · **Depends on:** Phase 1

## Goal
Implement `LLMProvider` (SPEC §9) using the official Anthropic Python SDK, returning a
schema-valid `Assessment` and a follow-up question.

## Read first
- `docs/SPEC.md` §5, §6 (F5, F6), §9, §11, §12, §14
- `app/contracts.py`, `app/config.py`, `app/rubric.py` (prompt loader), `app/llm/mock.py`
- Use the `claude-api` skill for current SDK usage. **Don't rely on memory for API
  shapes.**

## You own
- `app/llm/claude.py`
- `tests/test_llm_claude.py`

## Do not edit
Everything else, **especially `app/contracts.py`** and `app/prompts/` (owned by T6).

## Requirements
- `anthropic.AsyncAnthropic()`, with the model from `settings.claude_model`
  (`claude-opus-5-5`).
- **Assess:** use structured outputs (`output_config.format` with a hand-written JSON
  schema matching `Assessment`, `additionalProperties: false`), `effort: "medium"`, and
  server-side refusal fallbacks (`fallbacks: "default"` plus its beta header, per the
  skill). Parse the text block and validate with Pydantic. Retry once on validation
  failure.
- **Follow-up:** a short call (`effort: "low"`) that returns one question of 40 words or
  fewer, plus the target `dimension_id`.
- **Role-aware:** both methods take the `RoleProfile` (SPEC §5.4, §9) and pass it to the
  prompt builders in `app/rubric.py`. Don't build prompt text in this module. The LLM
  never calculates the fit %; `app/fit.py` does that.
- Check `stop_reason`. Treat `refusal` and `max_tokens` as clear `LLMError`s.
- **Evidence guard:** blank any `evidence_quote` that isn't a substring of the user's
  transcripts (case- and whitespace-insensitive).
- Return `LLMUsage` with the token counts and duration.
- Handle SDK errors with typed exceptions (rate limit, auth, connection), each mapped to a
  user-safe `LLMError`.

## Acceptance criteria
- [ ] Tests fake the API with `respx` or an SDK mock: valid output, invalid JSON then a
      valid retry, refusal, auth error, the evidence guard blanking a fake quote.
- [ ] Exactly 7 dimensions, one per `DimensionId`, are enforced.
- [ ] `make check` passes. No real API calls in tests.
- [ ] Optional manual check, if the user has put a key in `.env`: `make eval
      PROVIDER=claude` runs. Report the result but don't tune prompts (that's T6 and
      Phase 3).

## Prompt to paste
```
You are working on the AI Role Fitter repo. Read docs/SPEC.md and
docs/tasks/T2-claude-provider.md, then complete task T2 exactly as briefed.
Load the claude-api skill before writing SDK code. Only edit the files listed
under "You own". Never edit app/contracts.py or app/prompts/; if the contract
seems wrong, stop and tell me. Do not read or print .env. No real API calls in
tests. When finished, run `make check`, fix any failures, and give me a short
summary: what you built, test results, and anything the lead session needs to
wire up.
```
