# AI Role Fitter — Delivery Plan

Read alongside [SPEC.md](SPEC.md). This plan says **who does what, in what order**, and
**which work can be handed to a fresh Claude Code agent**.

## How the work is split

| Symbol | Meaning |
|---|---|
| 👤 **You** | A manual step only you can do (installs, keys, GitHub, decisions). |
| 🧭 **Lead session** | This main Claude Code session. It owns the shared contracts and does the integration. **Don't hand these off:** they need the full context. |
| 🤝 **Handoff** | A self-contained task. Start a **fresh** Claude Code session and paste the prompt from its brief in [`tasks/`](tasks/). |

**Why hand off at all?** A long session collects context, and quality drops as it grows.
Each handoff task:
- has its own brief;
- owns a specific set of files;
- works against frozen interfaces;
- has tests that define "done".

So a fresh agent can complete it without the history of this conversation.

## Overview

```
Phase 0 👤  Setup ─────────────────────────────────────────────┐
Phase 1 🧭  Foundation (contracts frozen, mock mode works)     │ sequential
            │
            ├── Wave A 🤝 (parallel, any order)
            │     T1 ElevenLabs voice   T2 Claude provider   T3 Ollama provider
            │     T4 Interview UI       T5 Report UI         T6 Rubric, prompts & eval
            │
Phase 3 🧭  Integration and tuning (merge, end-to-end test, real runs)
            │
            ├── Wave B 🤝 (parallel)
            │     T7 Docs (README, solution brief)   T8 Security review & hardening
            │
Phase 5 👤🧭 Release (demo rehearsal, repo → public)
```

**Recommended pace:** run 2 or 3 handoffs at a time, not all 6. Good pairs:
- T1 + T2
- T4 + T5
- T3 + T6

---

## Phase 0 — Setup 👤 (about 30 minutes)

| # | Step | Check |
|---|---|---|
| 0.1 | Install Apple's developer tools: `xcode-select --install` | `git --version` works |
| 0.2 | Install **Python 3.12** from the python.org macOS installer. Apple's built-in Python is 3.9, which is too old for the Anthropic SDK. | `python3.12 --version` |
| 0.3 | Install **Ollama v0.12.3** (Ollama.dmg from the GitHub release). Turn off auto-update. | `ollama --version` shows 0.12.3 |
| 0.4 | `ollama pull qwen2.5:1.5b`, then time `ollama run qwen2.5:1.5b "Reply with one sentence about AI skills."` | Note the time it takes |
| 0.5 | Create a **Claude API key** in the Claude Console, named `ai-role-fitter`, with a monthly spend limit (for example $10). **Don't paste it into any chat.** | Key saved somewhere safe |
| 0.6 | Create an **ElevenLabs API key**, restricted to TTS and STT if the option exists. | Key saved somewhere safe |
| 0.7 | On github.com, create a **private** repo called `ai-role-fitter`, with no README so it starts empty. | Repo URL copied |
| 0.8 | *(Optional, recommended)* Install the GitHub CLI from its official macOS `.pkg` installer, then run `gh auth login`. | `gh auth status` |
| 0.9 | Move this Claude Code session into a permanent folder, e.g. `~/Projects/ai-role-fitter`. | — |

**Tell the lead session when you're done:** the version numbers, the Ollama timing from
step 0.4, and the repo URL. Keys go into `.env` yourself, after Phase 1 creates
`.env.example`.

---

## Phase 1 — Foundation 🧭 Lead session

This is the critical path. Everything else builds on it, so it isn't handed off.

| # | Task | Output |
|---|---|---|
| 1.1 | Initialise git, the repo layout (below), Python venv, `requirements.txt` and a `Makefile` (`make dev`, `make test`, `make check`, `make eval`) | Runnable skeleton |
| 1.2 | Safety files: `.gitignore`, `.env.example`, detect-secrets pre-commit, and a CI workflow (ruff + pytest + gitleaks) | Secrets can't be committed |
| 1.3 | `app/contracts.py`: every model and Protocol from SPEC §9. **Frozen after this.** | Shared interfaces |
| 1.4 | `app/config.py`: settings and the loopback guard for `OLLAMA_URL` | Config |
| 1.5 | `app/rubric.py`: dimensions, questions, level calculation, prompt loader (placeholder prompts that take the role profile) | Content module |
| 1.5b | `app/roles/elevenlabs_fde.json` (from SPEC §5.4) and `app/fit.py` (SPEC §5.5), with fully unit-tested fit maths | Role fit works |
| 1.6 | Mock providers: `app/llm/mock.py`, `app/voice/mock.py`, and the provider factories | Works with no keys |
| 1.7 | `app/main.py`: every route in SPEC §10, wired to the factories | API complete on mocks |
| 1.8 | Minimal `static/` shell: a page with placeholder containers and IDs the UI tasks will fill in | UI scaffold |
| 1.9 | `samples/sample_report.json` (fictional persona) and baseline tests | Green tests |
| 1.10 | First commit and push to the private repo; protect `main` | Remote ready |

**Exit criteria:**
- `make check` passes;
- `make dev` serves the page;
- a typed-answer interview in mock mode produces a report as JSON, including `role_fit`;
- CI is green.

### Repo layout and file ownership

```
app/
  contracts.py        🧭 frozen
  config.py           🧭
  main.py             🧭 (routes)
  rubric.py           T6
  prompts/            T6  (assess.md, follow_up.md)
  roles/elevenlabs_fde.json  🧭 (T6 may suggest wording changes in its summary)
  fit.py              🧭
  llm/__init__.py     🧭 (factory)
  llm/mock.py         🧭
  llm/claude.py       T2
  llm/ollama.py       T3
  voice/__init__.py   🧭 (factory)
  voice/mock.py       🧭
  voice/elevenlabs.py T1
static/
  index.html          🧭 shell → T4 and T5 fill in their own sections
  interview.js        T4
  report.js           T5
  styles.css          T4 owns; T5 adds styles only under a `/* report */` section
samples/              🧭 / T6
tests/
  test_contracts.py, test_api.py, test_fit.py   🧭
  test_voice_elevenlabs.py         T1
  test_llm_claude.py               T2
  test_llm_ollama.py               T3
  fixtures/personas/, eval.py      T6
docs/
  SPEC.md, PLAN.md, tasks/         🧭
  solution-brief.md                T7
README.md                          T7
SECURITY.md                        T8
```

---

## Wave A — Parallel handoffs 🤝

| Task | Brief | Depends on | Size | Suggested model |
|---|---|---|---|---|
| **T1** ElevenLabs voice adapter | [tasks/T1-elevenlabs-voice.md](tasks/T1-elevenlabs-voice.md) | Phase 1 | S | Sonnet |
| **T2** Claude LLM provider | [tasks/T2-claude-provider.md](tasks/T2-claude-provider.md) | Phase 1 | M | Opus |
| **T3** Ollama LLM provider | [tasks/T3-ollama-provider.md](tasks/T3-ollama-provider.md) | Phase 1 | M | Sonnet |
| **T4** Interview UI | [tasks/T4-interview-ui.md](tasks/T4-interview-ui.md) | Phase 1 | M | Sonnet |
| **T5** Report UI | [tasks/T5-report-ui.md](tasks/T5-report-ui.md) | Phase 1 | M | Sonnet |
| **T6** Rubric prompts and eval set | [tasks/T6-rubric-prompts-eval.md](tasks/T6-rubric-prompts-eval.md) | Phase 1 | M | Opus |

T2 and T3 work against the placeholder prompts. T6's real prompts slot in at integration
time with no code change, because prompts are loaded from files.

## Phase 3 — Integration and tuning 🧭 Lead session

| # | Task |
|---|---|
| 3.1 | Review and merge the Wave A branches (run `/code-review` on each first). |
| 3.2 | End-to-end run in each mode, Claude / Ollama / Mock, by voice and by typing. |
| 3.3 | Run `make eval` on Claude and Ollama; tune the prompts in `app/prompts/` until the personas land in range. |
| 3.4 | Calibrate the latency estimate and cost calculation; confirm the SPEC §7 targets. |
| 3.5 | Generate the real `samples/sample_report.json` from a persona run. |
| 3.6 | Record a local-mode run (screen recording) as a demo backup. |

## Wave B — Parallel handoffs 🤝

| Task | Brief | Depends on | Size |
|---|---|---|---|
| **T7** README and solution brief | [tasks/T7-docs.md](tasks/T7-docs.md) | Phase 3 | S |
| **T8** Security review and hardening | [tasks/T8-security-review.md](tasks/T8-security-review.md) | Phase 3 | S |

## Phase 5 — Release 👤🧭

| # | Step | Who |
|---|---|---|
| 5.1 | Scan the full git history for secrets with gitleaks; it must be clean. | 🧭 |
| 5.2 | Check that no personal transcripts or audio are tracked by git. | 🧭 |
| 5.3 | Rehearse the 5-minute demo script (SPEC §15) twice, once with Wi-Fi off for the LLM step. | 👤 |
| 5.4 | Switch the repo from private to public on github.com. | 👤 |
| 5.5 | After the interviews, revoke both API keys and uninstall Ollama if you no longer need it. | 👤 |

---

## How to run a handoff 👤

1. **Create an isolated copy for the agent.** In the Claude desktop app, start a new Code
   session on the project folder with a **worktree**, or run:
   ```bash
   git worktree add ../arf-t1 -b t1-elevenlabs-voice
   ```
   This lets several agents work in parallel without overwriting each other's files.
2. **Open a fresh Claude Code session** in that folder.
3. **Paste the "Prompt to paste" block** from the task brief, unchanged.
4. **Let it run.** It should finish with `make check` passing and a summary.
5. **Review.** Run `/code-review` in that session, then commit and push the branch (or open
   a PR if `gh` is set up).
6. **Return to the lead session** and say "T1 is done on branch `t1-elevenlabs-voice`". The
   lead session merges and integrates.

**Rules every handoff agent follows** (also stated in each brief):
- Only edit the files the brief says it owns.
- **Never change `app/contracts.py`.** If the contract seems wrong, stop and report back.
- No real API calls in tests. Use `respx` to fake HTTP.
- Never read, print or commit `.env` or keys.
- Done means `make check` passes and the acceptance criteria are met.

## Progress tracker

| Phase / task | Status |
|---|---|
| Phase 0 Setup | 🟡 Done except Claude API key (step 0.5). Ollama 0.12.3 + qwen2.5:1.5b measured at ~15 tokens/s, 4.6s model load |
| Phase 1 Foundation | ✅ 68 tests, mock mode end to end, pushed |
| T1 Voice | ✅ merged |
| T2 Claude | ✅ merged (live API check pending: needs key in .env) |
| T3 Ollama | ✅ merged (live: assess ~184s, follow-up ~86s on qwen2.5:1.5b) |
| T4 Interview UI | ✅ merged |
| T5 Report UI | ✅ merged |
| T6 Rubric, prompts, eval | ✅ merged |
| Phase 3 Integration | 🟡 Claude eval 20/21, bands 3/3 (Haiku 5.5); caching added; real sample report. Local eval still to run |
| T7 Docs | ⬜ |
| T8 Security | ✅ merged: DNS-rebinding + cross-site fixes, CSP, SECURITY.md |
| Phase 5 Release | ⬜ |
