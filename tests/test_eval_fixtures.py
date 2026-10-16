"""The eval personas and demo answers are well formed (runs in CI; no LLM calls)."""

from __future__ import annotations

import json
import typing

import pytest

from app.config import ROOT
from app.contracts import DIMENSION_IDS, Answer, FitBand
from app.fit import band_for, compute_role_fit, load_role
from app.rubric import QUESTIONS
from tests.conftest import make_assessment
from tests.eval import PERSONAS_DIR, load_personas

ROLE = load_role(ROOT / "app" / "roles" / "elevenlabs_fde.json")
BANDS: list[str] = list(typing.get_args(FitBand))  # best first
PERSONA_FILES = sorted(PERSONAS_DIR.glob("*.json"))


def _check_answers(answers: list[Answer]) -> None:
    assert [a.question_id for a in answers] == [q["id"] for q in QUESTIONS] + ["followup"]
    for answer, q in zip(answers, QUESTIONS, strict=False):
        assert answer.dimension_id == q["dimension_id"]
        assert answer.question == q["text"]
    assert answers[-1].dimension_id in DIMENSION_IDS
    assert all(a.transcript.strip() for a in answers)


def test_three_personas():
    assert {p.stem for p in PERSONA_FILES} == {"novice", "practitioner", "expert"}


@pytest.mark.parametrize("path", PERSONA_FILES, ids=lambda p: p.stem)
def test_persona_is_well_formed(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["id"] == path.stem
    _check_answers([Answer.model_validate(a) for a in data["answers"]])

    assert set(data["expected"]) == set(DIMENSION_IDS)
    for lo, hi in data["expected"].values():
        assert isinstance(lo, int) and isinstance(hi, int)
        assert 1 <= lo <= hi <= 5

    # The expected band must be reachable from the expected ranges.
    assert data["expected_band"] in BANDS
    lows = {d: r[0] for d, r in data["expected"].items()}
    highs = {d: r[1] for d, r in data["expected"].items()}
    worst = compute_role_fit(make_assessment(lows), ROLE).band
    best = compute_role_fit(make_assessment(highs), ROLE).band
    assert BANDS.index(best) <= BANDS.index(data["expected_band"]) <= BANDS.index(worst)


def test_at_least_one_plain_spoken_persona():
    styles = [json.loads(p.read_text())["style"] for p in PERSONA_FILES]
    assert "plain spoken" in styles


def test_personas_load_in_eval_order():
    assert [p["id"] for p in load_personas()] == ["novice", "practitioner", "expert"]


def test_demo_answers_are_valid():
    data = json.loads((ROOT / "samples" / "demo_answers.json").read_text(encoding="utf-8"))
    _check_answers([Answer.model_validate(a) for a in data])


def test_band_helper_matches_spec_order():
    assert [band_for(p) for p in (90, 75, 60, 10)] == BANDS
