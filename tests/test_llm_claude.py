"""Claude provider tests. The API is faked at the HTTP transport: no network, no keys.

anthropic 1.x is built on httpx2, which respx doesn't patch, so we hand the SDK an
httpx2.MockTransport instead.
"""

from __future__ import annotations

import json

import anthropic
import httpx2
import pytest

from app.config import ROOT, Settings
from app.contracts import DIMENSION_IDS, LLMError
from app.fit import load_role
from app.llm.claude import FALLBACK_BETA, ClaudeLLM

ROLE = load_role(ROOT / "app" / "roles" / "elevenlabs_fde.json")


def _assessment_json(quote: str = "", dims: tuple[str, ...] = DIMENSION_IDS) -> str:
    return json.dumps(
        {
            "summary": "Solid practitioner.",
            "dimensions": [
                {"dimension_id": d, "score": 3, "evidence_quote": quote, "rationale": "r"}
                for d in dims
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
    )


def _message(text: str, stop_reason: str = "end_turn") -> dict:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }


class FakeAPI:
    """Replies to POST /v1/messages with queued responses and records the requests."""

    def __init__(self, *responses: httpx2.Response):
        self.responses = list(responses)
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return self.responses.pop(0)

    def body(self, i: int = 0) -> dict:
        return json.loads(self.requests[i].content)


def ok(text: str, stop_reason: str = "end_turn") -> httpx2.Response:
    return httpx2.Response(200, json=_message(text, stop_reason))


def error(status: int, kind: str) -> httpx2.Response:
    return httpx2.Response(
        status, json={"type": "error", "error": {"type": kind, "message": "nope"}}
    )


FAKE_KEY = "test-key"  # pragma: allowlist secret


def make_llm(api) -> ClaudeLLM:
    """`api` is any httpx2 transport handler: a FakeAPI or a function."""
    client = anthropic.AsyncAnthropic(
        api_key=FAKE_KEY,
        max_retries=0,
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(api)),
    )
    return ClaudeLLM(Settings(_env_file=None), client=client)


async def test_assess_valid_output(sample_answers):
    api = FakeAPI(ok(_assessment_json()))
    assessment, usage = await make_llm(api).assess(sample_answers, ROLE)

    assert [d.dimension_id for d in assessment.dimensions] == list(DIMENSION_IDS)
    assert usage.input_tokens == 100 and usage.output_tokens == 50
    assert usage.duration_ms >= 0

    body = api.body()
    assert body["model"] == "claude-haiku-5-5"
    assert body["output_config"]["effort"] == "medium"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["output_config"]["format"]["schema"]["additionalProperties"] is False
    assert body["fallbacks"] == "default"
    assert FALLBACK_BETA in api.requests[0].headers["anthropic-beta"]
    assert ROLE.title in body["system"][0]["text"]
    assert body["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert sample_answers[0].transcript in body["messages"][0]["content"]


async def test_assess_retries_once_after_invalid_json(sample_answers):
    api = FakeAPI(ok("{not json"), ok(_assessment_json()))
    assessment, usage = await make_llm(api).assess(sample_answers, ROLE)

    assert len(api.requests) == 2
    assert len(assessment.dimensions) == 7
    assert usage.input_tokens == 200 and usage.output_tokens == 100  # both calls counted


async def test_assess_fails_after_two_invalid_outputs(sample_answers):
    api = FakeAPI(ok("{not json"), ok("[]"))
    with pytest.raises(LLMError) as exc:
        await make_llm(api).assess(sample_answers, ROLE)
    assert exc.value.code == "llm_invalid_output"


async def test_assess_requires_each_dimension_exactly_once(sample_answers):
    six_plus_duplicate = (*DIMENSION_IDS[:-1], DIMENSION_IDS[0])
    api = FakeAPI(
        ok(_assessment_json(dims=DIMENSION_IDS[:-1])),  # only 6
        ok(_assessment_json(dims=six_plus_duplicate)),  # 7, but one duplicated
    )
    with pytest.raises(LLMError) as exc:
        await make_llm(api).assess(sample_answers, ROLE)
    assert exc.value.code == "llm_invalid_output"
    assert len(api.requests) == 2


@pytest.mark.parametrize(
    ("stop_reason", "code"),
    [("refusal", "claude_refusal"), ("max_tokens", "claude_max_tokens")],
)
async def test_assess_stop_reasons_are_clear_errors(sample_answers, stop_reason, code):
    api = FakeAPI(ok("", stop_reason=stop_reason))
    with pytest.raises(LLMError) as exc:
        await make_llm(api).assess(sample_answers, ROLE)
    assert exc.value.code == code
    assert len(api.requests) == 1  # not retried


@pytest.mark.parametrize(
    ("status", "kind", "code"),
    [
        (401, "authentication_error", "claude_auth"),
        (403, "permission_error", "claude_permission"),
        (429, "rate_limit_error", "claude_rate_limited"),
        (529, "overloaded_error", "claude_unavailable"),
        (400, "invalid_request_error", "claude_bad_request"),
    ],
)
async def test_api_errors_map_to_user_safe_llm_errors(sample_answers, status, kind, code):
    api = FakeAPI(error(status, kind))
    with pytest.raises(LLMError) as exc:
        await make_llm(api).assess(sample_answers, ROLE)
    assert exc.value.code == code
    assert FAKE_KEY not in exc.value.message


async def test_connection_error_maps_to_llm_error(sample_answers):
    def boom(request):
        raise httpx2.ConnectError("down", request=request)

    with pytest.raises(LLMError) as exc:
        await make_llm(boom).assess(sample_answers, ROLE)
    assert exc.value.code == "claude_unreachable"


async def test_evidence_guard_blanks_invented_quotes(sample_answers):
    real = sample_answers[0].transcript.split(".")[0]  # first sentence, verbatim
    reformatted = "  " + real.upper().replace(" ", "\n  ") + " "
    api = FakeAPI(ok(_assessment_json(quote=reformatted)))
    assessment, _ = await make_llm(api).assess(sample_answers, ROLE)
    assert all(d.evidence_quote == reformatted for d in assessment.dimensions)

    api = FakeAPI(ok(_assessment_json(quote="I have shipped ten voice agents to production.")))
    assessment, _ = await make_llm(api).assess(sample_answers, ROLE)
    assert all(d.evidence_quote == "" for d in assessment.dimensions)


async def test_follow_up_returns_question_and_dimension(sample_answers):
    reply = json.dumps(
        {"question": "How do you check an AI answer?", "dimension_id": "verification"}
    )
    api = FakeAPI(ok(reply))
    question, dim, usage = await make_llm(api).follow_up(sample_answers, ROLE)

    assert question == "How do you check an AI answer?"
    assert dim == "verification"
    assert usage.output_tokens == 50
    body = api.body()
    assert body["output_config"]["effort"] == "low"
    assert body["fallbacks"] == "default"


async def test_follow_up_over_40_words_is_retried(sample_answers):
    long_q = json.dumps({"question": " ".join(["word"] * 41) + "?", "dimension_id": "building"})
    short_q = json.dumps({"question": "What did you build?", "dimension_id": None})
    api = FakeAPI(ok(long_q), ok(short_q))
    question, dim, _ = await make_llm(api).follow_up(sample_answers, ROLE)
    assert question == "What did you build?"
    assert dim is None
    assert len(api.requests) == 2


async def test_too_few_recommendations_are_topped_up_not_rejected(sample_answers):
    data = json.loads(_assessment_json())
    data["recommendations"] = data["recommendations"][:2]
    api = FakeAPI(ok(json.dumps(data)))
    assessment, _ = await make_llm(api).assess(sample_answers, ROLE)
    assert len(api.requests) == 1  # no wasted retry
    assert len(assessment.recommendations) == 3
