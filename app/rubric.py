"""Rubric content, questions, level calculation and prompt building (SPEC §5).

T6 owns the content here (descriptors, wording) and app/prompts/. Function signatures
are shared with the providers — keep them unchanged.
"""

from __future__ import annotations

from pathlib import Path

from app.contracts import DIMENSION_IDS, Answer, Assessment, DimensionId, Level, RoleProfile

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# Follow-up questions for the rule-based picker (local and mock modes), one per dimension.
FOLLOW_UP_QUESTIONS: dict[str, str] = {
    "breadth": "Which AI tools or models have you compared for the same task, "
    "and what made you pick one over another?",
    "prompting": "Can you walk me through how you'd structure a prompt for a tricky task, "
    "and how you'd improve it if the first result was poor?",
    "verification": "When an AI gives you an answer you'll rely on, what exactly do you do "
    "to check it before you use it?",
    "building": "Tell me more about the technical side: how would you design an integration "
    "with an AI API, and what would you watch out for?",
    "voice_audio": "If you were building a voice feature for a customer, what would worry you "
    "most about speech recognition, synthetic voices or accessibility?",
    "responsible": "How would you explain to a customer what happens to their data when they "
    "use an AI feature you've built?",
    "customer_value": "How would you measure whether an AI pilot you ran for a customer "
    "actually succeeded?",
}


# Ready-written recommendations (title, why, first step): used by the mock, and to top up
# a local-model report that gives fewer than the 3 recommendations the contract needs.
RECOMMENDATION_TEMPLATES: dict[str, tuple[str, str, str]] = {
    "breadth": ("Compare three models on one task",
                "FDEs need to explain why one tool fits a customer better than another.",
                "Run the same real task through three models and note the differences."),
    "prompting": ("Build a reusable prompt template",
                  "Strong prompts make customer solutions reliable and repeatable.",
                  "Write a template with role, context, examples and output format; test it."),
    "verification": ("Add a verification habit",
                     "Customer solutions must be trustworthy in high-stakes settings.",
                     "Write a 5-item checklist for checking AI output and use it all week."),
    "building": ("Ship a small API integration",
                 "The role is hands-on Python and API integration for customers.",
                 "Build a Python script that calls an AI API end to end and handles errors."),
    "voice_audio": ("Build a voice prototype",
                    "The product is voice and audio AI; hands-on experience matters.",
                    "Use a speech-to-text and text-to-speech API to make a tiny voice demo."),
    "responsible": ("Write a one-page data policy",
                    "Enterprise customers expect clear answers on data handling.",
                    "Draft what data you would and wouldn't send to an AI tool, and why."),
    "customer_value": ("Run a mock discovery session",
                       "FDEs own delivery end to end with customers.",
                       "Write five discovery questions and a two-week pilot plan for a use case."),
}  # fmt: skip


def top_up_recommendations(
    recommendations: list[dict], scores: dict[str, int], role: RoleProfile, minimum: int = 3
) -> list[dict]:
    """Add ready-written recommendations until there are `minimum`. Picks dimensions not
    already covered: biggest role gap first (weight x gap), then the most important
    dimension with the most room to grow (weight x (5 - score)) for someone at target."""
    recs = list(recommendations)
    covered = {r.get("dimension_id") for r in recs if isinstance(r, dict)}
    ranked = sorted(
        role.requirements,
        key=lambda r: (
            -r.weight * max(r.target - scores.get(r.dimension_id, 1), 0),
            -r.weight * (5 - scores.get(r.dimension_id, 1)),
            -r.weight,
            DIMENSION_IDS.index(r.dimension_id),
        ),
    )
    # First pass: dimensions with room to grow. Second pass (someone at 5 almost
    # everywhere): stretch recommendations on the role's most important dimensions.
    candidates = [r for r in ranked if scores.get(r.dimension_id, 1) < 5]
    candidates += [r for r in ranked if r not in candidates]
    for req in candidates:
        if len(recs) >= minimum:
            break
        if req.dimension_id in covered:
            continue
        title, why, first_step = RECOMMENDATION_TEMPLATES[req.dimension_id]
        recs.append(
            {
                "title": title,
                "why": why,
                "first_step": first_step,
                "dimension_id": req.dimension_id,
                "effort": "low" if req.weight == 1 else "medium",
            }
        )
        covered.add(req.dimension_id)
    return recs


def rule_based_follow_up(answers: list[Answer], role: RoleProfile) -> tuple[str, DimensionId]:
    """Pick the follow-up without an LLM: the role's most important dimension (highest
    weight) where the answer was thinnest (fewest words). Instant and deterministic."""
    words = {d: 0 for d in DIMENSION_IDS}
    for a in answers:
        if a.dimension_id:
            words[a.dimension_id] += len(a.transcript.split())
    target = min(
        role.requirements,
        key=lambda r: (-r.weight, words[r.dimension_id], DIMENSION_IDS.index(r.dimension_id)),
    ).dimension_id
    return FOLLOW_UP_QUESTIONS[target], target


DIMENSIONS: dict[str, dict[str, str]] = {
    "breadth": {
        "name": "Tool and model breadth",
        "five": "Uses several tools and models deliberately and knows their strengths.",
    },
    "prompting": {
        "name": "Prompting and context",
        "five": "Gives structured context, examples and constraints; iterates systematically.",
    },
    "verification": {
        "name": "Critical evaluation",
        "five": "Checks outputs routinely, understands hallucination, "
        "has concrete verification habits.",
    },
    "building": {
        "name": "Building with AI APIs",
        "five": "Has shipped integrations or agents, understands evals, latency and cost.",
    },
    "voice_audio": {
        "name": "Voice and audio AI",
        "five": "Has used or built with STT/TTS/voice agents, knows the use cases and limits, "
        "and designs for accessibility.",
    },
    "responsible": {
        "name": "Responsible use",
        "five": "Thinks about data sensitivity, consent, bias and policy before using AI.",
    },
    "customer_value": {
        "name": "Turning AI into value",
        "five": "Can find use cases, scope a pilot, measure impact and explain AI to non-experts.",
    },
}

SCORE_LABELS: dict[int, tuple[str, str]] = {
    1: ("Unaware", "No meaningful use or understanding shown."),
    2: ("Exploring", "Occasional, ad-hoc use; surface understanding."),
    3: ("Practising", "Regular, purposeful use; some good habits."),
    4: ("Building", "Builds workflows or integrations; strong habits; can teach others."),
    5: ("Leading", "Expert depth; shapes how others and organisations use AI."),
}

QUESTIONS: list[dict[str, str]] = [
    {
        "id": "q1",
        "dimension_id": "breadth",
        "text": "Walk me through the AI tools you use in a typical week. "
        "What do you use each one for?",
    },
    {
        "id": "q2",
        "dimension_id": "prompting",
        "text": "Tell me about a recent time you got a really good result from an AI model. "
        "What did you give it, and how did you get there?",
    },
    {
        "id": "q3",
        "dimension_id": "verification",
        "text": "How do you decide whether you can trust an AI's output? "
        "Tell me about a time it got something wrong.",
    },
    {
        "id": "q4",
        "dimension_id": "building",
        "text": "Have you built anything on top of an AI API, such as a script, an integration "
        "or an agent? What was it, how did you design it, and what was hard?",
    },
    {
        "id": "q5",
        "dimension_id": "voice_audio",
        "text": "Where have you used, or where would you use, voice or audio AI, like "
        "speech-to-text, text-to-speech or voice agents?",
    },
    {
        "id": "q6",
        "dimension_id": "responsible",
        "text": "What do you think about before putting company or customer data into an AI tool?",
    },
    {
        "id": "q7",
        "dimension_id": "customer_value",
        "text": "A customer's engineering team wants to add voice AI to their product but "
        "doesn't know where to start. How would you approach the first two weeks with them?",
    },
]


def overall_score(assessment: Assessment) -> float:
    return round(sum(d.score for d in assessment.dimensions) / len(assessment.dimensions), 2)


def level_for(mean: float) -> Level:
    if mean >= 4.0:
        return "Leader"
    if mean >= 3.0:
        return "Builder"
    if mean >= 2.0:
        return "Practitioner"
    return "Explorer"


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def rubric_text() -> str:
    lines = ["Dimensions (id: name: what a 5 looks like):"]
    lines += [f"- {k}: {v['name']}: {v['five']}" for k, v in DIMENSIONS.items()]
    lines.append("\nScore scale:")
    lines += [f"- {n} {label}: {desc}" for n, (label, desc) in SCORE_LABELS.items()]
    return "\n".join(lines)


def role_text(role: RoleProfile) -> str:
    lines = [
        f"Target role: {role.title}",
        role.summary,
        "Requirements (weight: 3 high, 2 medium, 1 low importance; target: the score the role "
        "expects, 1-5):",
    ]
    for r in sorted(role.requirements, key=lambda r: -r.weight):
        name = DIMENSIONS[r.dimension_id]["name"]
        lines.append(f"- {r.dimension_id} ({name}): weight {r.weight}, target {r.target}. {r.why}")
    return "\n".join(lines)


def transcript_text(answers: list[Answer]) -> str:
    blocks = []
    for a in answers:
        tag = a.dimension_id or "unspecified"
        blocks.append(f"[{a.question_id} | {tag}]\nQ: {a.question}\nA: {a.transcript.strip()}")
    return "\n\n".join(blocks)


def _fill(template: str, role: RoleProfile) -> str:
    return template.replace("{{RUBRIC}}", rubric_text()).replace("{{ROLE}}", role_text(role))


def build_assess_prompt(answers: list[Answer], role: RoleProfile) -> tuple[str, str]:
    """Return (system, user) messages for the assessment call."""
    return _fill(load_prompt("assess"), role), transcript_text(answers)


def build_follow_up_prompt(answers: list[Answer], role: RoleProfile) -> tuple[str, str]:
    """Return (system, user) messages for the follow-up question call."""
    return _fill(load_prompt("follow_up"), role), transcript_text(answers)
