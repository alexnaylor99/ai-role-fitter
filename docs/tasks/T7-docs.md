# T7 — README and solution brief 🤝

**Branch:** `t7-docs` · **Size:** S · **Depends on:** Phase 3 (integration done)

## Goal
Write the docs an ElevenLabs interviewer reads first. They should be able to understand
the project in 60 seconds and run it in 3 commands.

## Read first
- `docs/SPEC.md` (all), `docs/PLAN.md`, the code under `app/` and `static/` (skim),
  `Makefile`, `.env.example`, and the eval output in the Phase 3 notes if present.

## You own
- `README.md`
- `docs/solution-brief.md`
- `docs/architecture.svg` (or a Mermaid diagram inside the README)

## Do not edit
Code, tests, `docs/SPEC.md`, `docs/PLAN.md`.

## Requirements
**README.md**, in this order:
1. A one-line pitch and a screenshot placeholder (`docs/screenshot.png`, which the user
   adds).
2. **Why I built this:** 3 bullets linking it to the FDE role (customer framing, ElevenLabs
   STT and TTS, enterprise trade-offs).
3. **Quickstart:**
   - (a) no keys: mock mode;
   - (b) full mode: copy `.env.example`, add keys;
   - (c) local privacy mode: Ollama v0.12.3 + `qwen2.5:1.5b`.
4. Architecture diagram and 4–5 key design decisions (from SPEC §11).
5. **How role fit works:** the role profile table (weights, targets, reasons), the fit
   formula in plain English, the bands, and "add a role by adding a JSON file".
6. **Privacy and security:** what leaves the device in each mode, how keys are handled,
   secret scanning.
7. Evaluation: how scoring is tested, plus the latest eval table.
8. Latency and cost table (measured).
9. Roadmap (SPEC §16).

**docs/solution-brief.md:** a 1–2 page customer-facing brief for the fictional customer
(a company scaling its FDE team; see SPEC §1). Include how the role profile is built from
the job spec, and why the fit is indicative and not a hiring decision. Sections: problem, proposed solution, how it works, rollout plan (pilot → team → org),
success metrics, risks and mitigations, and next steps. Plain English, no code.

Style:
- concise and scannable;
- British English;
- no marketing fluff;
- every claim matches what the code actually does. Check it.

## Acceptance criteria
- [ ] Every command in the README has been run and works.
- [ ] No secrets, personal data or real customer names.
- [ ] Links and relative paths resolve.

## Prompt to paste
```
You are working on the AI Role Fitter repo. Read docs/SPEC.md, docs/PLAN.md
and docs/tasks/T7-docs.md, then complete task T7 exactly as briefed. Only edit
the files listed under "You own". Verify every README command actually works
and every claim matches the code. Do not read or print .env. When finished,
give me a short summary and anything you couldn't verify.
```
