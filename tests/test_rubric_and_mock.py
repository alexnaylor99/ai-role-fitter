import pytest

from app.config import ROOT
from app.contracts import DIMENSION_IDS
from app.fit import load_role
from app.llm.mock import MockLLM
from app.rubric import (
    QUESTIONS,
    build_assess_prompt,
    build_follow_up_prompt,
    level_for,
    overall_score,
)
from tests.conftest import make_assessment

ROLE = load_role(ROOT / "app" / "roles" / "elevenlabs_fde.json")


def test_seven_questions_one_per_dimension():
    assert [q["dimension_id"] for q in QUESTIONS] == list(DIMENSION_IDS)
    assert len({q["id"] for q in QUESTIONS}) == 7


@pytest.mark.parametrize(
    ("mean", "level"),
    [(1.0, "Explorer"), (1.99, "Explorer"), (2.0, "Practitioner"), (2.99, "Practitioner"),
     (3.0, "Builder"), (3.99, "Builder"), (4.0, "Leader"), (5.0, "Leader")],
)  # fmt: skip
def test_level_boundaries(mean, level):
    assert level_for(mean) == level


def test_overall_score_is_mean():
    assert overall_score(make_assessment(default=3)) == 3.0


def test_prompts_include_role_rubric_and_answers(sample_answers):
    for build in (build_assess_prompt, build_follow_up_prompt):
        system, user = build(sample_answers, ROLE)
        assert ROLE.title in system
        assert "weight 3, target 4" in system
        assert "Leading" in system  # score scale
        assert "{{" not in system  # every placeholder filled
        assert sample_answers[3].transcript in user


async def test_mock_assess_is_valid_and_deterministic(sample_answers):
    llm = MockLLM()
    first, usage = await llm.assess(sample_answers, ROLE)
    second, _ = await llm.assess(sample_answers, ROLE)
    assert first == second
    assert usage.duration_ms >= 0
    transcripts = " ".join(a.transcript for a in sample_answers)
    for d in first.dimensions:
        assert d.evidence_quote == "" or d.evidence_quote in transcripts


async def test_mock_follow_up_targets_a_dimension(sample_answers):
    text, dimension_id, _ = await MockLLM().follow_up(sample_answers[:7], ROLE)
    assert dimension_id in DIMENSION_IDS
    assert 0 < len(text.split()) <= 40
