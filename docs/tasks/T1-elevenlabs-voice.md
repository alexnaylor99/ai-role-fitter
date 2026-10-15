# T1 — ElevenLabs voice adapter 🤝

**Branch:** `t1-elevenlabs-voice` · **Size:** S · **Depends on:** Phase 1

## Goal
Implement `VoiceProvider` (SPEC §9) using the ElevenLabs REST API: Scribe v2 for
speech-to-text and Flash v2.5 for text-to-speech.

## Read first
- `docs/SPEC.md` §6 (F1, F2), §7, §9, §12
- `app/contracts.py` (`VoiceProvider`), `app/config.py`, `app/voice/mock.py`,
  `app/voice/__init__.py`

## You own
- `app/voice/elevenlabs.py`
- `tests/test_voice_elevenlabs.py`

## Do not edit
Everything else, **especially `app/contracts.py`**. If you need a factory change in
`app/voice/__init__.py`, describe it in your summary instead.

## Requirements
- Use `httpx.AsyncClient`. Send the `xi-api-key` header from settings and never log it.
- **STT:** `POST https://api.elevenlabs.io/v1/speech-to-text`, multipart with `file` (the
  audio bytes plus their mime type) and `model_id` = `settings.elevenlabs_stt_model`
  (`scribe_v2`). Return `response["text"].strip()`.
- **TTS:** `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128`
  with JSON `{text, model_id}`. Return the MP3 bytes.
- Timeouts: 30s for STT and 15s for TTS. Retry once on 429 or 5xx, with a short backoff.
- Turn failures into a `VoiceError(code, message)` exception. Define it in your module if
  it isn't in the contracts. The message must be user-safe: no key, no raw body.
- Reject empty audio, and audio over 25MB, before calling the API.

## Acceptance criteria
- [ ] Tests use `respx` to fake both endpoints: success, 401, 429-then-success, timeout,
      empty audio.
- [ ] A test asserts the API key never appears in exception messages or logs.
- [ ] `make check` passes. No real network calls in tests.

## Prompt to paste
```
You are working on the AI Role Fitter repo. Read docs/SPEC.md and
docs/tasks/T1-elevenlabs-voice.md, then complete task T1 exactly as briefed.
Only edit the files listed under "You own". Never edit app/contracts.py; if the
contract seems wrong, stop and tell me. Do not read or print .env. Use respx for
all HTTP in tests; make no real API calls. When finished, run `make check`,
fix any failures, and give me a short summary: what you built, test results,
and anything the lead session needs to wire up.
```
