import pytest
from pydantic import ValidationError

from app.contracts import Answer, DimensionScore, RoleProfile
from tests.conftest import make_assessment


def test_assessment_requires_each_dimension_once():
    a = make_assessment()
    dims = list(a.dimensions)
    dims[1] = DimensionScore(dimension_id="breadth", score=2, rationale="dup")
    with pytest.raises(ValidationError, match="exactly once"):
        a.model_validate({**a.model_dump(), "dimensions": [d.model_dump() for d in dims]})


def test_assessment_rejects_six_dimensions():
    data = make_assessment().model_dump()
    data["dimensions"] = data["dimensions"][:6]
    with pytest.raises(ValidationError):
        type(make_assessment()).model_validate(data)


@pytest.mark.parametrize("score", [0, 6])
def test_scores_must_be_1_to_5(score):
    with pytest.raises(ValidationError):
        DimensionScore(dimension_id="breadth", score=score, rationale="x")


def test_recommendation_count_limits():
    data = make_assessment().model_dump()
    data["recommendations"] = data["recommendations"][:2]
    with pytest.raises(ValidationError):
        type(make_assessment()).model_validate(data)


def test_answer_rejects_empty_transcript():
    with pytest.raises(ValidationError):
        Answer(question_id="q1", question="Q?", transcript="")


def test_role_profile_requires_seven_unique_requirements():
    req = {"dimension_id": "breadth", "weight": 1, "target": 3, "why": "x"}
    with pytest.raises(ValidationError):
        RoleProfile(id="r", title="R", summary="s", source="s", requirements=[req] * 7)
