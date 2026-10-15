# T8 — Security review and hardening 🤝

**Branch:** `t8-security` · **Size:** S · **Depends on:** Phase 3 (integration done)

## Goal
An independent check that the repo is safe to make public and safe to run locally.

## Read first
- `docs/SPEC.md` §7, §10, §14
- All of `app/`, `static/`, `.gitignore`, `.env.example`, `.pre-commit-config.yaml`,
  `.github/workflows/`

## You own
- `SECURITY.md`
- Small, targeted fixes anywhere. **Every fix needs its own commit** with a clear message,
  and must be listed in your summary.
  Do **not** change `app/contracts.py` or the behaviour described in the spec. Report
  those instead.

## Checklist
- [ ] **Secrets:** run `gitleaks detect` over the **full git history** and
      `detect-secrets scan`. `.env` is ignored; `.env.example` holds placeholders only.
- [ ] **Keys never reach the client:** check every API response and the static files.
- [ ] **No keys in logs:** check exception handlers and logging config.
- [ ] **The server binds to `127.0.0.1`** only (check `make dev` and the uvicorn config).
- [ ] **The Ollama loopback guard** can't be bypassed (e.g. `http://127.0.0.1.evil.com`,
      `http://[::ffff:...]`, uppercase hosts, credentials in the URL). Add tests for these.
- [ ] **Uploads:** size and type limits on `/api/transcribe`; no temp files left behind.
- [ ] **XSS:** report data is rendered with `textContent` only; Chart.js loads with SRI.
- [ ] **CORS:** not enabled, or same-origin only.
- [ ] **Dependencies:** pinned versions; `pip-audit` is clean, or findings are documented.
- [ ] **Personal data:** `sessions/` and audio files are ignored; nothing personal is
      tracked (`git ls-files`).
- [ ] **CI:** gitleaks and tests run on every push and PR.
- [ ] Run `/security-review` and address the findings.

## SECURITY.md contents
- the threat model in 5–8 bullets;
- what data goes where in each mode;
- key handling and rotation advice;
- the note about Ollama v0.12.3 (loopback only, not patched);
- how to report an issue.

## Prompt to paste
```
You are working on the AI Role Fitter repo. Read docs/SPEC.md and
docs/tasks/T8-security-review.md, then complete task T8 exactly as briefed.
Work through every checklist item and report pass/fail with evidence. Make
only small, targeted fixes, one commit each; never change app/contracts.py or
spec'd behaviour, report those instead. Do not read or print .env. When
finished, give me the checklist results, the list of fixes, and any open risks.
```
