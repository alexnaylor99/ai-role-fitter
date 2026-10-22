"""Evidence guard shared by every real LLM provider: never show an invented quote."""

from __future__ import annotations

import re

from app.contracts import Answer, Assessment


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def guard_evidence(assessment: Assessment, answers: list[Answer]) -> Assessment:
    """Blank any evidence_quote that isn't verbatim from one of the user's transcripts."""
    transcripts = [_normalise(a.transcript) for a in answers]
    for d in assessment.dimensions:
        quote = _normalise(d.evidence_quote)
        if quote and not any(quote in t for t in transcripts):
            d.evidence_quote = ""
    return assessment
