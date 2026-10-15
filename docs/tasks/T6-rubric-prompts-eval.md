# T6 — Rubric prompts and evaluation set 🤝

**Branch:** `t6-rubric-prompts-eval` · **Size:** M · **Depends on:** Phase 1

## Goal
Write the real LLM prompts and a small evaluation set that measures whether the scoring is
sensible. This gives the answer to "how do you know it works?" in the interview.

## Read first
- `docs/SPEC.md` §5 (all), §9, §13, §14
- `app/rubric.py`, `app/prompts/` (placeholders), `app/contracts.py`, `app/llm/mock.py`,
  `app/roles/elevenlabs_fde.json`, `app/fit.py`

## You own
- `app/prompts/assess.md`, `app/prompts/follow_up.md`
- `app/rubric.py`: content only (descriptors, question text from SPEC §5.6). Keep the
  function signatures unchanged.
- `tests/fixtures/personas/*.json`, `tests/eval.py`, `tests/test_eval_fixtures.py`
- `samples/demo_answers.json` (used by the UI's `?demo=1`)

## Do not edit
`app/contracts.py`, `app/llm/*.py`, `app/main.py`, `app/fit.py`, `app/roles/`, `static/`.
If you think the role profile's weights, targets or wording should change, put the
suggestion in your summary.

## Requirements
- **`assess.md`:**
  - the rubric table, the score descriptors and the scoring rule from SPEC §5.2;
  - "only quote the user verbatim; empty quote if no evidence";
  - one score per dimension;
  - the role profile (title, and each requirement's weight, target and reason) is
    injected through the prompt builder;
  - **scores use the generic rubric only. The role must not change a score.** The role
    shapes only the summary and the recommendations;
  - the summary speaks to fit for the role, without stating a percentage;
  - recommendations target the highest-priority gaps (weight × gap), are specific to the
    FDE role and doable this week;
  - British English;
  - no scoring of the level or the fit (Python does both).
  Keep it model-agnostic and short enough to work on the 1.5B local model: plain
  structure, no long examples.
- **`follow_up.md`:** pick the dimension that matters most to the role (high weight)
  where the evidence is weakest or least clear, and ask one open, conversational question
  of 40 words or fewer. Return the dimension ID too.
- **Personas (3):** `novice`, `practitioner`, `expert` (an FDE-type engineer). Each has
  realistic answers to the 7 questions plus a follow-up, `expected` score ranges per
  dimension (e.g. `[1,2]`), and an `expected_band` for the FDE role fit. At least one
  persona answers in a plain, unpolished speaking style, to check that substance is scored
  rather than polish. All fictional, with no real names or companies.
- **`tests/eval.py`** (run via `make eval PROVIDER=...`): runs each persona through
  `assess()` and `app/fit.py`, and prints a table of dimension scores against the expected
  ranges, the percentage in range, the fit % and band against the expected band, and the
  latency. Exit code 0 always. It's a report, not a gate.
- **`tests/test_eval_fixtures.py`:** checks that the fixtures are valid `Answer` lists and
  the ranges are well formed (this runs in CI).
- **`samples/demo_answers.json`:** a strong "practitioner" set the presenter can use live.

## Acceptance criteria
- [ ] `make eval PROVIDER=mock` runs and prints the table.
- [ ] `make check` passes.
- [ ] Optional: if keys or Ollama are available, include eval output for `claude` and
      `ollama` in your summary.

## Prompt to paste
```
You are working on the AI Role Fitter repo. Read docs/SPEC.md and
docs/tasks/T6-rubric-prompts-eval.md, then complete task T6 exactly as briefed.
Only edit the files listed under "You own"; keep function signatures in
app/rubric.py unchanged and never edit app/contracts.py. All persona content
must be fictional. Do not read or print .env. When finished, run `make check`
and `make eval PROVIDER=mock`, and give me a short summary with the eval table.
```
