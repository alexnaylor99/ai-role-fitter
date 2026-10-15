# T4 — Interview UI 🤝

**Branch:** `t4-interview-ui` · **Size:** M · **Depends on:** Phase 1

## Goal
Build the start screen and the interview flow (SPEC §4, steps 1–4) in plain HTML, CSS and
JS, against the API in SPEC §10.

## Read first
- `docs/SPEC.md` §4, §6, §7, §10
- `static/index.html` (the shell and its container IDs), `app/main.py` (routes)

## You own
- `static/interview.js`
- `static/styles.css` (T5 will append a `/* report */` section; leave room at the end)
- The `#start` and `#interview` sections of `static/index.html` only

## Do not edit
`static/report.js`, the `#report` section, and everything under `app/`.

## Requirements
- **Start screen:**
  - a **target role card** from `GET /api/role`: the role title, its one-line summary, and
    the 3–4 highest-weighted requirements with their reasons;
  - mode toggle (Claude / Local / Mock), defaulting to the server's default, with
    unavailable modes disabled;
  - status strip from `/api/health`;
  - the privacy note in Local mode;
  - a "View sample report" button that calls `window.renderReport(report)` (provided by
    T5) with `/api/sample-report`.
- **Each question:**
  - plays TTS from `/api/tts`, with Replay. A 204 response means text-only, with no error.
  - Record/Stop via `MediaRecorder` (webm/opus), sent to `/api/transcribe`, filling an
    editable textarea.
  - A recording timer, with a 2-minute cap per answer.
  - If mic permission is denied or voice isn't configured, fall back to typing with an
    inline note.
  - Next is enabled when the text is non-empty.
  - Progress shows "Question n of 8".
- After question 7, call `/api/follow-up`, then ask question 8 the same way.
- **Submit:** `POST /api/assess` with `answers` and `client_metrics` (the measured STT and
  TTS durations). Show the progress state with the mode-specific estimate. On success,
  call `window.renderReport(report)`.
- **Errors:** inline, friendly, with a retry option. Never lose answers already given.
- **Accessibility:**
  - every control is keyboard-usable;
  - buttons have visible focus;
  - `aria-live` for status messages.
- Light and dark mode via CSS variables. No horizontal scroll at 375px wide.
- No frameworks, no build step, no inline secrets.
- **Demo helper:** `?demo=1` pre-fills answers from `GET /api/demo-answers`, if
  present, so the presenter can skip ahead.

## Acceptance criteria
- [ ] Full mock-mode run in the browser: start, 8 typed answers, report shown.
- [ ] Voice path verified with mock voice (`VOICE_PROVIDER=mock`: fixed transcript, no TTS audio).
- [ ] Denied mic permission falls back to typing.
- [ ] `make check` passes (it runs the backend tests; the UI is checked by hand). Include
      screenshots or notes in your summary.

## Prompt to paste
```
You are working on the AI Role Fitter repo. Read docs/SPEC.md and
docs/tasks/T4-interview-ui.md, then complete task T4 exactly as briefed.
Only edit the files/sections listed under "You own". Do not touch app/ or
static/report.js. Run the app in mock mode (`make dev` with LLM_PROVIDER=mock)
and test the flow in the browser pane. When finished, run `make check` and
give me a short summary with what you verified by hand.
```
