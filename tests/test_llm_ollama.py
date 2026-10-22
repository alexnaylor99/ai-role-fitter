"""Ollama provider tests. The server is faked with respx: no network, no model."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.config import ROOT, Settings
from app.contracts import DIMENSION_IDS, ConfigError, LLMError
from app.fit import load_role
from app.llm.ollama import OllamaLLM

ROLE = load_role(ROOT / "app" / "roles" / "elevenlabs_fde.json")
URL = "http://127.0.0.1:11434"
CHAT = f"{URL}/api/chat"


def _llm(**overrides) -> OllamaLLM:
    return OllamaLLM(Settings(_env_file=None, **overrides))


def _assessment(quote: str = "", **overrides) -> dict:
    data = {
        "summary": "Solid practitioner.",
        "dimensions": [
            {"dimension_id": d, "score": 3, "evidence_quote": quote, "rationale": "r"}
            for d in DIMENSION_IDS
        ],
        "strengths": ["a", "b"],
        "gaps": ["c", "d"],
        "recommendations": [
            {
                "title": "t",
                "why": "w",
                "first_step": "f",
                "dimension_id": "building",
                "effort": "low",
            }
        ]
        * 3,
    }
    data.update(overrides)
    return data


def _reply(content: str | dict, **extra) -> httpx.Response:
    if isinstance(content, dict):
        content = json.dumps(content)
    body = {
        "message": {"role": "assistant", "content": content},
        "prompt_eval_count": 100,
        "eval_count": 50,
        **extra,
    }
    return httpx.Response(200, json=body)


@respx.mock
async def test_assess_valid_output(sample_answers):
    route = respx.post(CHAT).mock(return_value=_reply(_assessment()))
    assessment, usage = await _llm().assess(sample_answers, ROLE)

    assert len(assessment.dimensions) == 7
    assert usage.input_tokens == 100 and usage.output_tokens == 50
    assert usage.duration_ms >= 0
    body = json.loads(route.calls[0].request.content)
    assert body["stream"] is False
    assert body["model"] == "qwen2.5:1.5b"
    assert body["options"] == {"temperature": 0.2, "num_ctx": 8192}
    assert body["format"]["required"][0] == "summary"
    assert body["messages"][0]["role"] == "system"
    assert ROLE.title in body["messages"][0]["content"]


@respx.mock
async def test_assess_retries_once_with_the_error(sample_answers):
    route = respx.post(CHAT).mock(
        side_effect=[
            _reply("not json at all"),
            _reply(_assessment()),
        ]
    )
    assessment, usage = await _llm().assess(sample_answers, ROLE)

    assert len(assessment.dimensions) == 7
    assert route.call_count == 2
    assert usage.input_tokens == 200 and usage.output_tokens == 100  # summed over both calls
    retry = json.loads(route.calls[1].request.content)
    assert "previous reply was not valid" in retry["messages"][1]["content"]


@respx.mock
async def test_assess_fails_after_two_bad_replies(sample_answers):
    route = respx.post(CHAT).mock(return_value=_reply("{}"))
    with pytest.raises(LLMError) as err:
        await _llm().assess(sample_answers, ROLE)
    assert err.value.code == "llm_invalid_output"
    assert route.call_count == 2


@respx.mock
async def test_repairs_clamp_scores_add_missing_and_trim(sample_answers):
    data = _assessment(
        strengths=["1", "2", "3", "4", "5"],
        gaps=["1", "2", "3", "4"],
        recommendations=_assessment()["recommendations"] * 3,  # nine of them
    )
    data["dimensions"][0]["score"] = 9  # too high
    data["dimensions"][1]["score"] = 0  # too low
    data["dimensions"][2]["score"] = "four"  # not a number
    data["dimensions"][3]["score"] = 3.6  # not an integer
    data["dimensions"] = data["dimensions"][:5]  # two dimensions missing
    data["dimensions"].append({"dimension_id": "made_up", "score": 5, "rationale": "x"})
    data["dimensions"].append(dict(data["dimensions"][4], score=1))  # duplicate id
    route = respx.post(CHAT).mock(return_value=_reply(data))

    assessment, _ = await _llm().assess(sample_answers, ROLE)

    assert route.call_count == 1  # repaired, no retry needed
    assert [d.dimension_id for d in assessment.dimensions] == list(DIMENSION_IDS)
    scores = {d.dimension_id: d.score for d in assessment.dimensions}
    assert scores[DIMENSION_IDS[0]] == 5
    assert scores[DIMENSION_IDS[1]] == 1
    assert scores[DIMENSION_IDS[2]] == 1
    assert scores[DIMENSION_IDS[3]] == 4
    assert scores[DIMENSION_IDS[4]] == 3  # the first of the duplicates wins
    for missing in DIMENSION_IDS[5:]:
        dim = assessment.score_for(missing)
        assert dim.score == 1 and dim.evidence_quote == ""
    assert len(assessment.strengths) == 3
    assert len(assessment.gaps) == 3
    assert len(assessment.recommendations) == 5


@respx.mock
async def test_evidence_guard_blanks_invented_quotes(sample_answers):
    real = sample_answers[0].transcript.split(".")[0]
    data = _assessment()
    data["dimensions"][0]["evidence_quote"] = real
    data["dimensions"][1]["evidence_quote"] = "A sentence nobody ever said."
    respx.post(CHAT).mock(return_value=_reply(data))

    assessment, _ = await _llm().assess(sample_answers, ROLE)

    assert assessment.dimensions[0].evidence_quote == real
    assert assessment.dimensions[1].evidence_quote == ""


@respx.mock
async def test_follow_up_is_instant_and_makes_no_model_call(sample_answers):
    route = respx.post(CHAT).mock(return_value=_reply("unused"))
    question, dimension, usage = await _llm().follow_up(sample_answers[:7], ROLE)

    assert not route.called  # rule-based: no ~86s wait for the local model
    assert dimension in {"building", "customer_value"}  # the role's weight-3 dimensions
    assert question.endswith("?")
    assert usage.input_tokens == 0


@pytest.mark.parametrize(
    "url", ["http://example.com:11434", "http://127.0.0.1.evil.com", "http://192.168.1.5:11434"]
)
def test_non_loopback_url_is_refused(url):
    with pytest.raises(ConfigError):
        _llm(ollama_url=url)


@respx.mock
async def test_loopback_is_rechecked_before_every_request(sample_answers):
    route = respx.post(CHAT).mock(return_value=_reply(_assessment()))
    llm = _llm()
    llm._url = "http://evil.example.com"  # something changed it after construction
    with pytest.raises(ConfigError):
        await llm.assess(sample_answers, ROLE)
    assert not route.called


@respx.mock
async def test_timeout_is_a_friendly_error(sample_answers):
    respx.post(CHAT).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(LLMError) as err:
        await _llm().assess(sample_answers, ROLE)
    assert err.value.code == "ollama_timeout"


@respx.mock
async def test_server_down_and_missing_model(sample_answers):
    respx.post(CHAT).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(LLMError) as err:
        await _llm().assess(sample_answers, ROLE)
    assert err.value.code == "ollama_unreachable"

    respx.post(CHAT).mock(return_value=httpx.Response(404, json={"error": "model not found"}))
    with pytest.raises(LLMError) as err:
        await _llm().assess(sample_answers, ROLE)
    assert err.value.code == "ollama_model_missing"


@respx.mock
async def test_timeout_setting_is_used():
    assert _llm(ollama_timeout_s=12.0)._timeout == 12.0


@respx.mock
async def test_reachable_true_when_model_listed():
    respx.get(f"{URL}/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "qwen2.5:1.5b"}]})
    )
    assert await _llm().reachable() is True


@respx.mock
async def test_reachable_false_when_model_missing_or_server_down():
    route = respx.get(f"{URL}/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "llama3:8b"}]})
    )
    assert await _llm().reachable() is False

    route.mock(side_effect=httpx.ConnectError("refused"))
    assert await _llm().reachable() is False


@respx.mock
async def test_too_few_recommendations_are_topped_up_not_rejected(sample_answers):
    # Real case: an expert at target on most dimensions got only 2 recommendations,
    # and the retry repeated it. The report should be kept and topped up to 3.
    data = _assessment()
    for d in data["dimensions"]:
        d["score"] = 5 if d["dimension_id"] != "customer_value" else 3
    data["recommendations"] = data["recommendations"][:2]
    data["recommendations"][0]["dimension_id"] = "customer_value"
    data["recommendations"][1]["dimension_id"] = "customer_value"
    route = respx.post(CHAT).mock(return_value=_reply(data))

    assessment, _ = await _llm().assess(sample_answers, ROLE)

    assert route.call_count == 1  # no wasted retry
    assert len(assessment.recommendations) == 3
    added = assessment.recommendations[2]
    assert added.dimension_id == "building"  # new dimension: the role's top weight
