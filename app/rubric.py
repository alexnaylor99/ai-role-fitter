"""Rubric content, questions, level calculation and prompt building (SPEC §5).

T6 owns the content here (descriptors, wording) and app/prompts/. Function signatures
are shared with the providers — keep them unchanged.
"""

from __future__ import annotations

from pathlib import Path

from app.contracts import Answer, Assessment, Level, RoleProfile

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

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
        "five": "Has used or built with STT/TTS/voice agents and knows the use cases and limits.",
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
    lines = [f"Target role: {role.title}", role.summary, "Requirements (weight 1-3, target 1-5):"]
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
