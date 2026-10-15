"""Shared test setup: no .env, no keys, mock providers, fresh caches for every test."""

from __future__ import annotations

import json

import pytest

from app.config import ROOT, get_settings
from app.contracts import DIMENSION_IDS, Answer, Assessment, DimensionScore, Recommendation

KEY_VARS = ["ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY"]


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    monkeypatch.setenv("ARF_ENV_FILE", "")  # never read the developer's real .env
    for var in KEY_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("VOICE_PROVIDER", "auto")
    monkeypatch.setenv("SAVE_SESSIONS", "false")
    _clear_caches()
    yield
    _clear_caches()


def _clear_caches() -> None:
    get_settings.cache_clear()
    from app.main import get_role

    get_role.cache_clear()


@pytest.fixture
def sample_answers() -> list[Answer]:
    data = json.loads((ROOT / "samples" / "sample_answers.json").read_text())
    return [Answer.model_validate(a) for a in data]


def make_assessment(scores: dict[str, int] | None = None, default: int = 3) -> Assessment:
    scores = scores or {}
    return Assessment(
        summary="Test summary.",
        dimensions=[
            DimensionScore(
                dimension_id=d, score=scores.get(d, default), evidence_quote="", rationale="r"
            )
            for d in DIMENSION_IDS
        ],
        strengths=["a", "b"],
        gaps=["c", "d"],
        recommendations=[
            Recommendation(
                title="t", why="w", first_step="f", dimension_id="building", effort="low"
            )
        ]
        * 3,
    )
