# AI Role Fitter — Product Spec

**Status:** Agreed v1.1 (role-fit reframe) · **Owner:** Alex · **Last updated:** 2026-10-15

This document is the single source of truth for what we are building. Every Claude Code
agent working on this repo should read it before starting. If something here conflicts
with a task brief, this spec wins — flag the conflict rather than guessing.

---

## 1. Summary

A voice-first web app that interviews you about how you use AI and shows **how well your
AI skills fit the ElevenLabs Forward Deployed Engineer (FDE) role**. It scores you on a
7-dimension rubric, weights the scores against a role profile built from the ElevenLabs
FDE job spec, and produces a visual report: a fit percentage, where you meet the role,
where the gaps are, and specific steps to close them.

It is built as a portfolio demo for that same role, and is deliberately framed as a
customer deployment: *"A company scaling its FDE team wants candidates and new hires to
see how their AI skills map to the role, and what to work on first."*

The output is **indicative and for self-development**. It comes from a short,
self-reported interview, and is not a hiring decision. The report says so.

## 2. Goals and non-goals

### Goals
1. **Show FDE skills:** Python, clean architecture, API integration, explaining complex
   things simply, end-to-end ownership, customer framing.
2. **Show strong use of ElevenLabs:** Scribe v2 speech-to-text **and** text-to-speech.
3. **Show enterprise thinking:** a switchable LLM, including a fully local privacy mode,
   plus measured latency and cost, and secure handling of keys and data.
4. **Be demo-proof:** works with no keys (mock mode), without a mic (typed answers), and
   without internet for the LLM step (local mode).
5. **Be safe to publish on GitHub:** no secrets, no personal data, and secret scanning in
   place.

### Non-goals (v1)
- User accounts, multi-user storage, or a database.
- Hosting on the public internet. It runs on `localhost` only.
- Real-time streaming conversation. Each question and answer is a separate turn.
- Mobile layout polish. Desktop Chrome is the target, though the layout must not break on
  narrow screens.
- Any ElevenLabs product beyond STT and TTS. The Agents Platform is on the roadmap only.
- Multiple roles or a role picker. v1 has one role: ElevenLabs FDE. The role profile is a
  data file, so more roles can be added later without code changes.
- Making or supporting hiring decisions.

## 3. Users

| User | Need |
|---|---|
| **Alex (presenter)** | Run a smooth 5-minute live demo; talk through the architecture and trade-offs. |
| **Interviewer (ElevenLabs)** | Understand it in 60 seconds from the README; optionally run it with no keys. |
| **Fictional customer (FDE team lead)** | A clear, trustworthy picture of how one person's AI skills map to the FDE role, plus a development plan. |

## 4. User journey

1. **Start screen:** title, a one-line explanation, a **target role card** ("ElevenLabs
   Forward Deployed Engineer", with the 3–4 things the role weights most), and an LLM mode toggle
   (**Claude** / **Local (Qwen 2.5 1.5B)** / **Mock**). A status strip shows which services
   are configured and reachable. In Local mode it also shows a privacy note: "Answers stay
   on this device. Speech is transcribed by ElevenLabs."
2. **Interview, 7 questions:** for each one —
   - The question text is shown and read aloud (ElevenLabs TTS). A "Replay" button is
     available.
   - The user clicks **Record**, speaks, and clicks **Stop**. Audio goes to ElevenLabs
     Scribe and the transcript appears in an editable text box.
   - Alternatively, the user types an answer.
   - **Next** is enabled once the answer is non-empty.
   - A progress indicator shows "Question 3 of 8".
3. **Adaptive follow-up (question 8):** the LLM writes one follow-up question aimed at the
   dimension that matters most to the role where the evidence is weakest or least clear.
   It is answered the same way.
4. **Assessing:** a progress state with an honest time estimate (Claude about 20s, Local
   about 2 min).
5. **Report:** leads with the role fit (see §8). It has "Download JSON" and "Start again"
   buttons.
6. **Sample report:** viewable from the start screen without doing an interview.

## 5. Interview content

### 5.1 Rubric dimensions

| ID | Dimension | What a 5 looks like |
|---|---|---|
| `breadth` | Tool and model breadth | Uses several tools and models deliberately and knows their strengths. |
| `prompting` | Prompting and context | Gives structured context, examples and constraints; iterates systematically. |
| `verification` | Critical evaluation | Checks outputs routinely, understands hallucination, has concrete verification habits. |
| `building` | Building with AI APIs | Has shipped integrations or agents, understands evals, latency and cost. |
| `voice_audio` | Voice and audio AI | Has used or built with STT/TTS/voice agents, knows the use cases and limits, and designs for accessibility. |
| `responsible` | Responsible use | Thinks about data sensitivity, consent, bias and policy before using AI. |
| `customer_value` | Turning AI into value | Can find use cases, scope a pilot, measure impact and explain AI to non-experts. |

### 5.2 Score scale (per dimension, integer 1–5)

| Score | Label | Descriptor |
|---|---|---|
| 1 | Unaware | No meaningful use or understanding shown. |
| 2 | Exploring | Occasional, ad-hoc use; surface understanding. |
| 3 | Practising | Regular, purposeful use; some good habits. |
| 4 | Building | Builds workflows or integrations; strong habits; can teach others. |
| 5 | Leading | Expert depth; shapes how others and organisations use AI. |

**Scoring rule:** a score must be supported by something the user actually said. If a
dimension has no evidence, score it 1 and set `evidence_quote` to `""`. Never invent
quotes.

### 5.3 AI literacy level (secondary, from the mean of the 7 scores)

| Mean | Level |
|---|---|
| < 2.0 | Explorer |
| 2.0 – 2.9 | Practitioner |
| 3.0 – 3.9 | Builder |
| ≥ 4.0 | Leader |

The level is calculated in Python, never by the LLM, so it is deterministic. It is shown
as a secondary badge; the role fit (§5.5) is the headline.

### 5.4 Role profile: ElevenLabs Forward Deployed Engineer

Stored as data in `app/roles/elevenlabs_fde.json` (schema `RoleProfile`, §9). It is built
from the ElevenLabs FDE job spec:
- owning delivery end to end for strategic customers;
- working daily with customer engineers and executives;
- Python, software architecture and API integration;
- explaining complex technical ideas clearly;
- first-principles problem solving;
- enthusiasm for audio AI and accessibility.

| Dimension | Weight | Target score | Why it matters for the role |
|---|---|---|---|
| `building` | 3 | 4 | Python, software architecture and API integration; designs and ships tailored integrations. |
| `customer_value` | 3 | 4 | Owns delivery end to end for strategic customers; works with their engineers and executives. |
| `voice_audio` | 2 | 3 | The product is voice and audio AI; the spec asks for genuine enthusiasm for audio AI and accessibility. |
| `prompting` | 2 | 4 | Gets the best out of models when building customer solutions. |
| `verification` | 2 | 4 | First-principles problem solving; ships reliable solutions in high-stakes customer settings. |
| `responsible` | 1 | 3 | Enterprise customers expect careful handling of their data. |
| `breadth` | 1 | 3 | Knows the wider AI landscape customers are comparing against. |

The weights and targets are the role's opinion of what matters. They are editable data,
and the README explains how they were chosen.

### 5.5 Role fit calculation (deterministic, in Python)

For each dimension *d*, with score *s*, target *t* and weight *w*:

- `dimension_fit = min(s / t, 1.0)`. Exceeding the target doesn't earn extra credit.
- `gap = max(t − s, 0)`
- `priority = w × gap`, which orders the gaps and the recommendations.

`fit_percent = round(100 × Σ(w × dimension_fit) / Σw)`

| Fit % | Fit band |
|---|---|
| ≥ 85 | Strong fit |
| 70 – 84 | Good fit |
| 50 – 69 | Developing fit |
| < 50 | Early stage |

`meets` = the dimensions where `s ≥ t`. `gaps` = the dimensions where `s < t`, sorted by
priority, highest first.

### 5.6 Questions (fixed order)

| # | Dimension | Question |
|---|---|---|
| 1 | `breadth` | Walk me through the AI tools you use in a typical week. What do you use each one for? |
| 2 | `prompting` | Tell me about a recent time you got a really good result from an AI model. What did you give it, and how did you get there? |
| 3 | `verification` | How do you decide whether you can trust an AI's output? Tell me about a time it got something wrong. |
| 4 | `building` | Have you built anything on top of an AI API, such as a script, an integration or an agent? What was it, how did you design it, and what was hard? |
| 5 | `voice_audio` | Where have you used, or where would you use, voice or audio AI, like speech-to-text, text-to-speech or voice agents? |
| 6 | `responsible` | What do you think about before putting company or customer data into an AI tool? |
| 7 | `customer_value` | A customer's engineering team wants to add voice AI to their product but doesn't know where to start. How would you approach the first two weeks with them? |
| 8 | *(adaptive)* | Claude mode: generated by the LLM. Local and mock modes: picked by a rule (highest-weight dimension with the thinnest answer), because the local LLM took ~86s. It targets the dimension that matters most to the role (high weight) where the evidence is weakest or least clear. Max 40 words, one question only. |

## 6. Functional requirements

| ID | Requirement |
|---|---|
| F1 | Questions are read aloud with ElevenLabs TTS. If TTS is unavailable, show the text only, without an error modal. |
| F2 | Answers are recorded in the browser (MediaRecorder, webm/opus) and transcribed with ElevenLabs Scribe v2. |
| F3 | Every answer can be typed or edited before submitting. |
| F4 | The LLM mode can be chosen on the start screen: `claude`, `ollama` or `mock`. The default comes from `.env`. |
| F5 | One adaptive follow-up question is generated after question 7. |
| F6 | The assessment returns a schema-valid `Report` (§9). Invalid LLM output is retried once, then a clear error is shown. |
| F7 | The report leads with the role fit (fit %, band, meets, gaps), then renders a radar chart of your scores against the role's targets, per-dimension evidence and rationale, strengths, and 3–5 recommendations aimed at the top-priority gaps. |
| F8 | The report footer shows the metrics: STT/TTS/LLM timings, provider and model, and estimated cost. |
| F9 | The sample report is viewable without keys. |
| F10 | Mock mode works end to end with zero keys and zero network access. |
| F11 | Sessions are saved to `sessions/` (git-ignored) **only** if `SAVE_SESSIONS=true`. |
| F12 | The role profile is loaded from a JSON file (`ROLE_PROFILE`) and validated at startup. An invalid profile stops the app with a clear message. |
| F13 | The report always shows the disclaimer: "Indicative, based on a short self-reported interview. Not a hiring assessment." |
| F14 | Audio for the 7 fixed questions is synthesised once and cached in git-ignored `tts_cache/`; follow-up questions are never cached. Saves most of the ElevenLabs TTS credits per interview. |
| F15 | Caching to cut API spend: (a) Claude prompt caching on the stable system prompt (rubric + role; ~2.4k tokens read at 10% price within 5 min); (b) an in-memory response cache so identical answers are never re-assessed (also saves ~3 min in local mode); never written to disk. The report footer shows cache use and cost. |

## 7. Non-functional requirements

| Area | Requirement |
|---|---|
| **Security** | API keys are read only on the server from `.env` and never sent to the browser or logged. The server binds to `127.0.0.1` only. |
| **Local-only LLM** | The Ollama URL must resolve to a loopback host (`127.0.0.1`, `localhost`, `::1`), otherwise the app refuses to start local mode. |
| **Privacy** | Transcripts are kept in memory by default. The UI states clearly what leaves the device in each mode. |
| **Secrets in Git** | `.env`, `sessions/` and `*.webm` are git-ignored. `detect-secrets` runs as a pre-commit hook. gitleaks runs in CI. |
| **Latency (Claude mode)** | Report in ≤ 30s at p50; STT ≤ 3s for a 30-second answer; TTS first audio ≤ 2s. |
| **Latency (Local mode)** | Report in ≤ 3 min on Alex's 2017 Intel MacBook Pro (8GB). A progress state is shown throughout. |
| **Cost** | ≤ $0.15 per full interview in Claude mode. |
| **Reliability** | Every external call has a timeout and a friendly error message. Nothing crashes the page. |
| **Portability** | Python 3.12, macOS Ventura on Intel. No build step for the frontend. |

## 8. Report

- **Role fit header:**
  - "Fit for ElevenLabs Forward Deployed Engineer";
  - the fit % as a large number with a ring or bar, and the fit band;
  - a 2–3 sentence summary;
  - the AI literacy level as a small secondary badge;
  - the disclaimer (F13).
- **Meets / gaps:** two lists.
  - *Where you meet the role:* each dimension at or above target.
  - *Gaps to close:* each dimension below target, sorted by priority, showing
    "score → target" and the role's reason it matters (from the role profile).
- **Radar chart:** 7 axes on a 1–5 scale with **two series**: your scores and the role's
  targets (Chart.js, loaded from cdnjs with SRI).
- **Dimension cards (7):** name, score vs target, evidence quote in quotation marks,
  rationale, and the role's weight shown as "High / Medium / Low importance for this
  role". Sorted by priority, so the biggest gaps lead.
- **Strengths** (2–3 bullets) and the LLM's narrative **Gaps** (2–3 bullets).
- **Development plan (3–5 recommendations):** title, why it matters *for the FDE role*, a
  first step doable this week, and effort (low/medium/high). Each is linked to a
  dimension; they're ordered by gap priority.
- **Footer:** provider and model, timings, estimated cost, and generation time.
- **Actions:** Download JSON, Start again.

## 9. Data contracts (frozen after Phase 1)

These live in `app/contracts.py`. They may only be changed in the lead session.

```python
DimensionId = Literal[
    "breadth",
    "prompting",
    "verification",
    "building",
    "voice_audio",
    "responsible",
    "customer_value",
]


class Answer(BaseModel):
    question_id: str  # "q1".."q7", "followup"
    dimension_id: DimensionId | None  # None only for followup if LLM didn't say
    question: str
    transcript: str
    source: Literal["voice", "typed"]


class DimensionScore(BaseModel):
    dimension_id: DimensionId
    score: int  # 1..5
    evidence_quote: str  # verbatim from transcript, or ""
    rationale: str  # ≤ 40 words


class Recommendation(BaseModel):
    title: str
    why: str
    first_step: str
    dimension_id: DimensionId
    effort: Literal["low", "medium", "high"]


class Assessment(BaseModel):  # what the LLM must return
    summary: str
    dimensions: list[DimensionScore]  # exactly 7, one per DimensionId
    strengths: list[str]  # 2..3
    gaps: list[str]  # 2..3
    recommendations: list[Recommendation]  # 3..5


class Metrics(BaseModel):
    stt_ms: list[int] = []
    tts_ms: list[int] = []
    llm_followup_ms: int | None = None
    llm_assess_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    est_cost_usd: float | None = None


class RoleRequirement(BaseModel):
    dimension_id: DimensionId
    weight: int  # 1..3
    target: int  # 1..5
    why: str  # why it matters for this role, ≤ 30 words


class RoleProfile(BaseModel):  # loaded from app/roles/*.json
    id: str  # "elevenlabs_fde"
    title: str  # "ElevenLabs Forward Deployed Engineer"
    summary: str  # one line, shown on the start screen
    source: str  # where the profile comes from (job spec reference)
    requirements: list[RoleRequirement]  # exactly 7, one per DimensionId


class DimensionFit(BaseModel):
    dimension_id: DimensionId
    score: int
    target: int
    weight: int
    fit: float  # min(score/target, 1.0)
    gap: int  # max(target - score, 0)
    priority: int  # weight * gap


class RoleFit(BaseModel):  # computed in Python, never by the LLM
    role_id: str
    role_title: str
    fit_percent: int  # 0..100
    band: Literal["Strong fit", "Good fit", "Developing fit", "Early stage"]
    dimensions: list[DimensionFit]  # sorted by priority, highest first
    meets: list[DimensionId]
    gaps: list[DimensionId]  # sorted by priority, highest first


class Report(BaseModel):  # what the API returns
    assessment: Assessment
    role_fit: RoleFit
    overall_score: float  # mean, computed in Python
    level: Literal["Explorer", "Practitioner", "Builder", "Leader"]
    provider: Literal["claude", "ollama", "mock"]
    model: str
    generated_at: datetime
    metrics: Metrics
```

### Provider interfaces

The role profile is passed to the LLM so that the summary, the follow-up question and the
recommendations are aimed at the role. The LLM still scores against the generic rubric
(§5.2); it never sees or calculates the fit %.

```python
class LLMProvider(Protocol):
    name: str          # "claude" | "ollama" | "mock"
    model: str
    async def follow_up(self, answers: list[Answer], role: RoleProfile) -> tuple[str, DimensionId | None, LLMUsage]
    async def assess(self, answers: list[Answer], role: RoleProfile) -> tuple[Assessment, LLMUsage]

class VoiceProvider(Protocol):
    async def transcribe(self, audio: bytes, mime_type: str) -> str
    async def synthesize(self, text: str) -> bytes   # audio/mpeg
```

`LLMUsage` has `input_tokens`, `output_tokens` and `duration_ms`.

**Implementation notes (settled in Phase 1; the code in `app/contracts.py` is authoritative):**
- Providers are constructed with the settings object: `ClaudeLLM(settings)`,
  `OllamaLLM(settings)`, `ElevenLabsVoice(settings)`. The factories in `app/llm/__init__.py`
  and `app/voice/__init__.py` import them lazily, so a provider that isn't built yet gives a
  clear `ConfigError` rather than a crash.
- Errors: raise `LLMError`, `VoiceError` or `ConfigError` (subclasses of `AppError`) with a
  user-safe `code` and `message`. The API turns them into `{error: {code, message}}`.
- `VoiceProvider.synthesize` may return `b""`, meaning "no audio", and the API then returns
  204. `VoiceProvider` and `LLMProvider` also have a `name`.
- An optional `async def reachable(self) -> bool` on a provider is used by `/api/health`.
- Request bodies are the `TTSRequest`, `FollowUpRequest` and `AssessRequest` models.

## 10. HTTP API

| Method and path | Request | Response |
|---|---|---|
| `GET /api/health` | — | `{llm_default, providers: {claude, ollama, mock}: {configured, reachable}, voice: {configured}}` |
| `GET /api/questions` | — | `[{id, dimension_id, text}]` (7 items) |
| `GET /api/role` | — | `RoleProfile` (for the start-screen role card and the report) |
| `POST /api/tts` | `{text}` | `audio/mpeg` · `204` if voice is not configured |
| `POST /api/transcribe` | multipart `audio` | `{text, duration_ms}` · `503` if voice is not configured |
| `POST /api/follow-up` | `{provider, answers[]}` | `{question: {id:"followup", dimension_id, text}, duration_ms}` |
| `POST /api/assess` | `{provider, answers[], client_metrics}` | `Report` |
| `GET /api/sample-report` | — | `Report` (from `samples/sample_report.json`) |
| `GET /api/demo-answers` | — | `Answer[]` from `samples/demo_answers.json` (for `?demo=1`) · `404` if absent |
| `GET /` | — | the static frontend |

Errors use the shape `{error: {code, message}}` with a suitable HTTP status. Messages are
safe to show to the user and never include keys or stack traces.

## 11. Architecture

```
Browser (static HTML/JS, Chart.js)
   │  fetch /api/*
   ▼
FastAPI (127.0.0.1:8000)
   ├── voice/ ── ElevenLabs   (TTS: eleven_flash_v2_5 · STT: scribe_v2)   | mock
   ├── llm/   ── Claude API   (claude-haiku-5-5 by default, structured JSON output)
   │          ── Ollama        (127.0.0.1:11434, qwen2.5:1.5b, JSON schema format)
   │          ── Mock          (deterministic keyword scoring)
   ├── rubric.py  (dimensions, questions, levels, prompt loading)
   ├── roles/elevenlabs_fde.json  (role profile: weights, targets, reasons)
   ├── fit.py     (deterministic role-fit calculation)
   └── contracts.py (Pydantic models + Protocols)
```

**Key design decisions**
- **Adapters behind Protocols:** each external service is swappable and testable, which is
  the FDE "fit into the customer's stack" story.
- **The LLM scores; Python calculates:** the role fit, level and mean are deterministic,
  and the LLM output is validated against the schema. The same answers always give the
  same fit for the same scores, and the maths is explainable to a customer.
- **The role is data, not code:** a new role is a new JSON file. That's the "configure,
  don't rebuild" story for customer deployments.
- **Claude reliability:** the Claude calls use structured outputs and server-side refusal
  fallbacks (`fallbacks: "default"`).
- **Ollama reliability:** Ollama calls use the `format` JSON schema; one retry if
  validation fails.
- **No frontend build step:** fewer moving parts for a demo and a reviewer.

## 12. Configuration (`.env`)

| Variable | Default | Notes |
|---|---|---|
| `LLM_PROVIDER` | `claude` | `claude` / `ollama` / `mock` |
| `ANTHROPIC_API_KEY` | — | Required for Claude mode |
| `CLAUDE_MODEL` | `claude-haiku-5-5` | ~$0.002 per interview; the eval was measured on it. `claude-opus-5-5` also works (~40× the price) |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Must be a loopback host |
| `OLLAMA_MODEL` | `qwen2.5:1.5b` | |
| `OLLAMA_TIMEOUT_S` | `360` | Slow on the Intel CPU: one report took ~184s |
| `VOICE_PROVIDER` | `auto` | `auto` (ElevenLabs if a key is set, else typed answers) / `elevenlabs` / `mock` / `none` |
| `ELEVENLABS_API_KEY` | — | Without it, voice is disabled and answers are typed |
| `ELEVENLABS_VOICE_ID` | `JBFqnCBsd6RMkjVDRZzb` | |
| `ELEVENLABS_TTS_MODEL` | `eleven_flash_v2_5` | Low latency |
| `ELEVENLABS_STT_MODEL` | `scribe_v2` | |
| `SAVE_SESSIONS` | `false` | Writes to git-ignored `sessions/` |
| `ROLE_PROFILE` | `app/roles/elevenlabs_fde.json` | The target role |

## 13. Testing and evaluation

- **Unit tests (pytest):** contracts, level calculation, **role-fit maths** (worked
  examples, boundaries of each band, exceeding the target), role profile validation, the
  localhost guard, mock providers, and API routes. External APIs are faked with `respx`.
- **Contract tests:** every provider's output must validate as an `Assessment`.
- **Evaluation set:** 3 fictional personas (novice, practitioner, expert FDE-type) in
  `tests/fixtures/personas/`, each with expected score ranges **and an expected fit
  band**. `make eval PROVIDER=claude|ollama` reports how many scores land in range,
  whether the fit band matches, and the latency.
  This is the "how do you know it works?" answer for the interview.
- **CI (GitHub Actions):** ruff, pytest (mock only, no keys), and gitleaks.

## 14. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Local model gives weak or invalid scores | Schema-constrained output, one retry, eval set to measure it, and clear "privacy mode" framing. |
| Local mode is slow on the Intel CPU | Honest progress UI; a pre-recorded local run for the demo. |
| A key leaks into Git | `.gitignore`, detect-secrets pre-commit, gitleaks in CI, and a dedicated revocable key with a spend limit. |
| Live demo network failure | Mock mode, typed answers, and the sample report. |
| Ollama v0.12.3 is no longer patched | Loopback only, no network exposure, auto-update off; remove after the interviews. |
| LLM invents evidence | Prompt rule, plus a check that each `evidence_quote` is a substring of the transcripts; otherwise it is blanked. |
| The fit % is read as a hiring verdict | A fixed disclaimer on the report (F13); framed as self-development; non-goal stated; weights are visible and explained. |
| Bias against people who are less articulate when speaking | Typed answers are always allowed; the scoring rule rewards substance, not polish; the eval personas include plain-spoken answers. |
| The role profile misrepresents the real job | Built only from the published job spec, with the source cited in the profile and the README. |

## 15. Demo script (5 minutes)

1. **(30s)** The customer framing: a company scaling its FDE team wants people to see how
   their AI skills map to the role.
2. **(2 min)** Live interview: answer 2 or 3 questions by voice, then skip ahead to the
   pre-filled answers.
3. **(1 min)** The report: your fit % for the ElevenLabs FDE role, the radar chart of you
   vs the role, the gaps, and the development plan.
4. **(1 min)** Architecture: show the role profile JSON ("a new role is a new file"),
   switch to Local mode, explain the privacy, latency and cost trade-offs, and show the
   eval results.
5. **(30s)** Roadmap: the ElevenLabs Agents Platform, more roles, team dashboards.

## 16. Roadmap (post-v1)

- Run the whole interview on the ElevenLabs Agents Platform for a real-time conversation.
- More role profiles and a role picker, plus "best-fit role" across several roles.
- Generate a role profile from a pasted job description (LLM-drafted, human-approved).
- Team view: aggregate results across a team for its lead.
- Multilingual interviews (Scribe and multilingual TTS).
- Re-assessment over time, showing progress towards the role.
