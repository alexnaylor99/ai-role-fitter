"""Deterministic keyword-based LLM stand-in. No keys, no network. Used for demos and tests."""

from __future__ import annotations

import re
import time

from app.contracts import (
    DIMENSION_IDS,
    Answer,
    Assessment,
    DimensionId,
    DimensionScore,
    LLMUsage,
    Recommendation,
    RoleProfile,
)
from app.rubric import DIMENSIONS, FOLLOW_UP_QUESTIONS, RECOMMENDATION_TEMPLATES

KEYWORDS: dict[str, list[str]] = {
    "breadth": ["chatgpt", "claude", "gemini", "copilot", "cursor", "perplexity", "llama",
                "mistral", "notebooklm", "midjourney", "elevenlabs", "model"],
    "prompting": ["context", "example", "few-shot", "system prompt", "iterat", "constraint",
                  "structured", "step by step", "template", "persona"],
    "verification": ["check", "verif", "hallucinat", "source", "test", "cross-check",
                     "fact", "review", "wrong", "eval"],
    "building": ["api", "python", "sdk", "integration", "agent", "script", "deploy",
                 "endpoint", "webhook", "latency", "rag", "tool call"],
    "voice_audio": ["speech", "voice", "audio", "text-to-speech", "tts", "stt", "transcri",
                    "dubbing", "accessib", "podcast"],
    "responsible": ["privacy", "gdpr", "pii", "consent", "policy", "bias", "anonymi",
                    "confidential", "security", "retention"],
    "customer_value": ["customer", "stakeholder", "pilot", "discovery", "use case", "roi",
                       "metric", "workshop", "success", "scope"],
}  # fmt: skip


def _text_by_dimension(answers: list[Answer]) -> dict[str, list[str]]:
    texts: dict[str, list[str]] = {d: [] for d in DIMENSION_IDS}
    for a in answers:
        if a.dimension_id:
            texts[a.dimension_id].append(a.transcript)
    return texts


def _score(texts: list[str], dimension_id: str) -> tuple[int, str]:
    joined = " ".join(texts).lower()
    hits = [k for k in KEYWORDS[dimension_id] if k in joined]
    quote = ""
    if hits:
        for text in texts:
            for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
                if any(k in sentence.lower() for k in hits):
                    quote = sentence.strip()
                    break
            if quote:
                break
    # Two keywords per score step, so short answers don't score highly: 0→1, 1-2→2, 3-4→3 …
    return 1 + min(4, (len(hits) + 1) // 2), quote


class MockLLM:
    name = "mock"
    model = "mock-keyword-v1"

    async def follow_up(
        self, answers: list[Answer], role: RoleProfile
    ) -> tuple[str, DimensionId | None, LLMUsage]:
        start = time.perf_counter()
        texts = _text_by_dimension(answers)
        # Most important dimension (weight) with the weakest evidence (score).
        target = max(
            role.requirements,
            key=lambda r: r.weight * (5 - _score(texts[r.dimension_id], r.dimension_id)[0]),
        ).dimension_id
        ms = int((time.perf_counter() - start) * 1000)
        return FOLLOW_UP_QUESTIONS[target], target, LLMUsage(duration_ms=ms)

    async def assess(self, answers: list[Answer], role: RoleProfile) -> tuple[Assessment, LLMUsage]:
        start = time.perf_counter()
        texts = _text_by_dimension(answers)
        dims = []
        for d in DIMENSION_IDS:
            score, quote = _score(texts[d], d)
            rationale = (
                f"Keyword match on {DIMENSIONS[d]['name']} gives {score}/5 (mock scoring)."
                if score > 1
                else "No clear evidence in the answers."
            )
            dims.append(
                DimensionScore(
                    dimension_id=d, score=score, evidence_quote=quote, rationale=rationale
                )
            )

        by_score = sorted(dims, key=lambda d: (-d.score, DIMENSION_IDS.index(d.dimension_id)))
        # Recommendations target the role's highest-priority gaps (weight × gap).
        scores = {d.dimension_id: d.score for d in dims}
        priority = sorted(
            role.requirements,
            key=lambda r: -r.weight * max(r.target - scores[r.dimension_id], 0),
        )
        recs = [
            Recommendation(
                title=RECOMMENDATION_TEMPLATES[r.dimension_id][0],
                why=RECOMMENDATION_TEMPLATES[r.dimension_id][1],
                first_step=RECOMMENDATION_TEMPLATES[r.dimension_id][2],
                dimension_id=r.dimension_id,
                effort="low" if r.weight == 1 else "medium",
            )
            for r in priority[:3]
        ]

        assessment = Assessment(
            summary=(
                f"Mock assessment for the {role.title} role, based on keywords in your answers. "
                "Switch to Claude or the local model for a real assessment."
            ),
            dimensions=dims,
            strengths=[f"{DIMENSIONS[d.dimension_id]['name']}" for d in by_score[:2]],
            gaps=[f"{DIMENSIONS[d.dimension_id]['name']}" for d in by_score[-2:]],
            recommendations=recs,
        )
        ms = int((time.perf_counter() - start) * 1000)
        return assessment, LLMUsage(input_tokens=0, output_tokens=0, duration_ms=ms)
