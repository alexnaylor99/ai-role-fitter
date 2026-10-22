# Security

AI Role Fitter is a single-user demo that runs on your own machine. It is not built to be
hosted on the internet, and it has no accounts or database.

## Threat model

- **Who uses it:** one person, in a browser on the same machine as the server. The server
  binds to `127.0.0.1` only and is never meant to be reachable from the network.
- **What's worth protecting:** the Anthropic and ElevenLabs API keys (they cost money),
  and the interview answers (personal, self-reported data).
- **Other websites you visit while the app runs:** the main real-world risk. A page could
  try to call the API through DNS rebinding or a cross-site form post and spend your keys.
  The server refuses any request whose `Host` isn't `127.0.0.1`, `localhost` or `::1`, and
  any write whose `Origin` isn't the app itself. CORS is not enabled.
- **LLM output is untrusted:** the report is rendered with `textContent` only, never
  `innerHTML`, under a Content-Security-Policy that allows scripts only from the app and
  cdnjs (Chart.js, pinned with SRI). Framing is blocked.
- **The local model must stay local:** `OLLAMA_URL` has to be an exact loopback host;
  suffix tricks, credentials in the URL and IPv4-mapped addresses are refused, the check
  is repeated before every request, and redirects are not followed.
- **Uploads:** `/api/transcribe` accepts `audio/*` only, up to 25 MB; uploads are held in
  memory or an anonymous temporary file and nothing is left on disk.
- **Out of scope:** an attacker who can already run code as you on your machine, and
  running the app on a shared or public network interface (don't).

## What data goes where

| Mode | Your answers (text) | Your voice recordings | Question audio |
|---|---|---|---|
| **Claude** | Anthropic API | ElevenLabs Scribe (if voice is on) | ElevenLabs TTS |
| **Local** (Ollama) | Stay on this machine | ElevenLabs Scribe (if voice is on) | ElevenLabs TTS |
| **Mock** | Stay on this machine | ElevenLabs Scribe if `VOICE_PROVIDER` resolves to ElevenLabs; nowhere with `VOICE_PROVIDER=mock` or `none` | Same as recordings |

What is kept, and where:
- **Answers and reports** are kept in server memory only. An in-memory response cache
  (up to 32 recent results, so a repeated run costs nothing) is cleared when the server
  stops and is never written to disk.
- **`sessions/`** is written only when `SAVE_SESSIONS=true`. It is git-ignored.
- **`tts_cache/`** holds audio for the fixed interview questions only, never your
  answers and never Claude's personalised follow-up. It is git-ignored and safe to delete.
- **Audio files** (`*.webm`, `*.mp3`, …) are git-ignored. The browser stores nothing
  (no cookies, no local storage).
- **Logs** show request paths and, for unexpected errors, the error type only: never
  keys, request bodies or error messages.

## API keys

- Keys live only in `.env` in the main checkout (git-ignored; `.env.example` holds
  placeholders). They are read on the server and never sent to the browser or logged.
- Use **dedicated keys for this app** with a **spend limit** set in the Anthropic and
  ElevenLabs consoles, so a leak has a small, capped blast radius.
- **Rotate** a key at once if it might have been exposed (pasted somewhere, committed,
  shown on a screen share): revoke it in the provider's console, create a new one, and
  update `.env`. Revoke both keys after the interviews are over.
- `detect-secrets` runs as a pre-commit hook and `gitleaks` scans the full git history in
  CI on every push and pull request. If a key is ever committed, rotate it first; rewriting
  history does not un-leak it.

## Ollama v0.12.3

Local mode was set up with **Ollama v0.12.3**, which is no longer receiving security
fixes. It is acceptable here only because:
- Ollama listens on `127.0.0.1:11434` by default. **Do not** set `OLLAMA_HOST=0.0.0.0` or
  otherwise expose it to the network, and leave `OLLAMA_ORIGINS` unset.
- This app only ever talks to it over loopback (see above).
- Auto-update is off so the measured performance stays stable for the demo.

Upgrade or uninstall Ollama once the interviews are over.

## Reporting a security issue

Please use GitHub's private vulnerability reporting on this repository
(**Security → Report a vulnerability**) rather than opening a public issue. Include the
steps to reproduce and what an attacker could gain.
