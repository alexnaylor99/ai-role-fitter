"""Response cache and cache-aware cost estimates (no network: a fake provider counts calls)."""

from app.contracts import LLMUsage
from app.llm import CachedLLM, clear_response_cache, estimate_cost
from tests.conftest import make_assessment
from tests.test_rubric_and_mock import ROLE


class _CountingLLM:
    name = "claude"
    model = "claude-haiku-5-5"

    def __init__(self):
        self.assess_calls = 0
        self.follow_up_calls = 0

    async def assess(self, answers, role):
        self.assess_calls += 1
        return make_assessment(), LLMUsage(input_tokens=100, output_tokens=50)

    async def follow_up(self, answers, role):
        self.follow_up_calls += 1
        return "Why?", "building", LLMUsage(input_tokens=10, output_tokens=5)


async def test_identical_answers_are_assessed_once(sample_answers):
    clear_response_cache()
    inner = _CountingLLM()
    llm = CachedLLM(inner)

    _, first = await llm.assess(sample_answers, ROLE)
    second_assessment, second = await llm.assess(sample_answers, ROLE)

    assert inner.assess_calls == 1
    assert not first.cached_response
    assert second.cached_response
    assert estimate_cost(llm.model, second) == 0.0
    # The cached copy can't be changed through a returned object.
    second_assessment.summary = "changed"
    third, _ = await llm.assess(sample_answers, ROLE)
    assert third.summary == "Test summary."


async def test_different_answers_are_not_served_from_cache(sample_answers):
    clear_response_cache()
    inner = _CountingLLM()
    llm = CachedLLM(inner)
    await llm.assess(sample_answers, ROLE)
    changed = [a.model_copy() for a in sample_answers]
    changed[0].transcript = "Something different."
    await llm.assess(changed, ROLE)
    assert inner.assess_calls == 2


async def test_follow_up_is_cached_too(sample_answers):
    clear_response_cache()
    inner = _CountingLLM()
    llm = CachedLLM(inner)
    await llm.follow_up(sample_answers[:7], ROLE)
    question, dimension, usage = await llm.follow_up(sample_answers[:7], ROLE)
    assert inner.follow_up_calls == 1
    assert (question, dimension, usage.cached_response) == ("Why?", "building", True)


def test_cost_counts_prompt_cache_reads_and_writes():
    # Haiku 5.5: $0.10 in / $0.50 out per million; reads 10%, writes 125% of input.
    usage = LLMUsage(
        input_tokens=1000, output_tokens=1000, cache_read_tokens=10000, cache_write_tokens=2000
    )
    expected = (1000 * 0.10 + 10000 * 0.01 + 2000 * 0.125 + 1000 * 0.50) / 1_000_000
    assert estimate_cost("claude-haiku-5-5", usage) == round(expected, 6)


def test_unknown_model_costs_nothing():
    assert estimate_cost("some-local-model", LLMUsage(input_tokens=5, output_tokens=5)) == 0.0
