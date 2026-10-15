import json

import pytest

from app.config import ROOT
from app.contracts import ConfigError, RoleProfile
from app.fit import band_for, compute_role_fit, load_role
from tests.conftest import make_assessment

ROLE_PATH = ROOT / "app" / "roles" / "elevenlabs_fde.json"


@pytest.fixture
def role() -> RoleProfile:
    return load_role(ROLE_PATH)


def test_role_profile_matches_spec(role):
    # SPEC §5.4 — weights and targets for the ElevenLabs FDE role.
    expected = {
        "building": (3, 4),
        "customer_value": (3, 4),
        "voice_audio": (2, 3),
        "prompting": (2, 4),
        "verification": (2, 4),
        "responsible": (1, 3),
        "breadth": (1, 3),
    }
    assert {r.dimension_id: (r.weight, r.target) for r in role.requirements} == expected


def test_all_targets_met_is_100_percent(role):
    fit = compute_role_fit(make_assessment(default=5), role)
    assert fit.fit_percent == 100
    assert fit.band == "Strong fit"
    assert fit.gaps == []
    assert len(fit.meets) == 7


def test_exceeding_target_earns_no_extra_credit(role):
    at_target = make_assessment({r.dimension_id: r.target for r in role.requirements})
    assert compute_role_fit(at_target, role).fit_percent == 100


def test_worked_example(role):
    # building 2/4 (w3), customer_value 3/4 (w3), voice 3/3 (w2), prompting 4/4 (w2),
    # verification 2/4 (w2), responsible 3/3 (w1), breadth 3/3 (w1)
    # = (3*.5 + 3*.75 + 2 + 2 + 2*.5 + 1 + 1) / 14 = 10.75 / 14 = 76.79% -> 77
    scores = {
        "building": 2,
        "customer_value": 3,
        "voice_audio": 3,
        "prompting": 4,
        "verification": 2,
        "responsible": 3,
        "breadth": 3,
    }
    fit = compute_role_fit(make_assessment(scores), role)
    assert fit.fit_percent == 77
    assert fit.band == "Good fit"
    # priorities: building 3*2=6, verification 2*2=4, customer_value 3*1=3
    assert fit.gaps == ["building", "verification", "customer_value"]
    assert fit.dimensions[0].dimension_id == "building"
    assert fit.dimensions[0].priority == 6
    assert set(fit.meets) == {"voice_audio", "prompting", "responsible", "breadth"}


def test_all_ones(role):
    fit = compute_role_fit(make_assessment(default=1), role)
    # (3/4+3/4+2/3+2/4+2/4+1/3+1/3)... weighted: (3*.25*2 + 2*(1/3) + 2*.25*2 + 2*(1/3)) / 14
    assert fit.band == "Early stage"
    assert len(fit.gaps) == 7


@pytest.mark.parametrize(
    ("percent", "band"),
    [
        (100, "Strong fit"),
        (85, "Strong fit"),
        (84, "Good fit"),
        (70, "Good fit"),
        (69, "Developing fit"),
        (50, "Developing fit"),
        (49, "Early stage"),
        (0, "Early stage"),
    ],
)
def test_band_boundaries(percent, band):
    assert band_for(percent) == band


def test_invalid_role_profile_raises_config_error(tmp_path):
    bad = json.loads(ROLE_PATH.read_text())
    bad["requirements"] = bad["requirements"][:6]
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(ConfigError) as exc:
        load_role(path)
    assert exc.value.code == "role_profile_invalid"


def test_missing_role_profile_raises_config_error(tmp_path):
    with pytest.raises(ConfigError) as exc:
        load_role(tmp_path / "nope.json")
    assert exc.value.code == "role_profile_missing"
