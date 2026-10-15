# T5 — Report UI 🤝

**Branch:** `t5-report-ui` · **Size:** M · **Depends on:** Phase 1

## Goal
Render a `Report` (SPEC §9) as the visual report described in SPEC §8.

## Read first
- `docs/SPEC.md` §5.2–§5.5, §6 (F7, F13), §8, §9
- `samples/sample_report.json`, `static/index.html` (the `#report` container)

## You own
- `static/report.js`
- The `#report` section of `static/index.html`
- A `/* report */` section appended to the **end** of `static/styles.css`. Use only the
  existing CSS variables; don't change rules above it.

## Do not edit
`static/interview.js`, other HTML sections, and everything under `app/`.

## Requirements
- Expose `window.renderReport(report)`. It hides the other sections and shows `#report`.
- **Role fit header** (the headline, from `report.role_fit`):
  - "Fit for {role_title}";
  - `fit_percent` as a large number with a ring or bar, and the `band`;
  - the summary;
  - the AI literacy `level` as a small secondary badge, with the mean to 1 decimal place;
  - the disclaimer text from SPEC F13, always visible.
- **Meets / gaps to close:** two lists, side by side, stacking on narrow screens.
  - Gaps follow `role_fit.gaps` order and show "score → target" plus the role's `why`.
  - Fetch the role profile from `GET /api/role` for the `why` text and display names.
- **Radar chart:**
  - Chart.js from **cdnjs**, pinned version with an SRI `integrity` attribute;
  - 7 axes with the dimension display names, scale 1–5;
  - **two series:** "You" (filled) and "Role target" (dashed outline);
  - colours from CSS variables, readable in light and dark mode.
- **Dimension cards:**
  - sorted by `role_fit.dimensions` order (priority, highest first);
  - score shown as "3 / 5 · target 4" plus the label (Practising);
  - importance chip from the weight: 3 = High, 2 = Medium, 1 = Low;
  - evidence in quotation marks, or "No evidence given" when empty;
  - the rationale.
- **Strengths and narrative gaps:** two lists from `assessment.strengths` and
  `assessment.gaps`.
- **Development plan:** the recommendations, titled "Your development plan for this role":
  title, why, first step, an effort chip, and the linked dimension's name.
- **Footer:** provider and model, STT/TTS averages, LLM time, estimated cost ("$0.00
  (local)" for Ollama), and generation time.
- **Actions:**
  - Download JSON (Blob, filename `ai-role-fit-YYYY-MM-DD.json`);
  - Start again (reloads the page).
- All text is set with `textContent`, **never `innerHTML` with report data**. The data
  comes from an LLM, so treat it as untrusted.
- Print-friendly: `@media print` hides the buttons.

## Acceptance criteria
- [ ] Opening the sample report from the start screen renders every section correctly.
- [ ] Works with edge cases: an empty quote, 3 recommendations, 5 recommendations, very
      long text, no gaps (100% fit), and every dimension a gap.
- [ ] No horizontal scroll at 375px; light and dark mode both readable.
- [ ] `make check` passes. Include notes or screenshots in your summary.

## Prompt to paste
```
You are working on the AI Role Fitter repo. Read docs/SPEC.md and
docs/tasks/T5-report-ui.md, then complete task T5 exactly as briefed.
Only edit the files/sections listed under "You own". Do not touch app/ or
static/interview.js. Treat report data as untrusted (textContent only). Run the
app (`make dev`) and check the sample report in the browser pane at desktop
and 375px widths. When finished, run `make check` and give me a short summary.
```
