"""Shared data contracts and provider interfaces (SPEC §9).

FROZEN after Phase 1. Only the lead session may change this file. If a handoff task
needs a change, stop and report it instead of editing here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol, get_args

from pydantic import BaseModel, Field, model_validator

DimensionId = Literal[
    "breadth",
    "prompting",
    "verification",
    "building",
    "voice_audio",
    "responsible",
    "customer_value",
]
DIMENSION_IDS: tuple[str, ...] = get_args(DimensionId)

ProviderName = Literal["claude", "ollama", "mock"]
Level = Literal["Explorer", "Practitioner", "Builder", "Leader"]
FitBand = Literal["Strong fit", "Good fit", "Developing fit", "Early stage"]


def _require_each_dimension_once(ids: list[str], what: str) -> None:
    if sorted(ids) != sorted(DIMENSION_IDS):
        raise ValueError(f"{what} must contain each dimension exactly once")


# --- Interview -------------------------------------------------------------------------


class Answer(BaseModel):
    question_id: str = Field(min_length=1, max_length=20)  # "q1".."q7", "followup"
    dimension_id: DimensionId | None = None  # None only for a follow-up without a target
    question: str = Field(min_length=1, max_length=500)
    transcript: str = Field(min_length=1, max_length=5000)
    source: Literal["voice", "typed"] = "typed"


# --- What the LLM returns ------------------------------------------------------------


class DimensionScore(BaseModel):
    dimension_id: DimensionId
    score: int = Field(ge=1, le=5)
    evidence_quote: str = ""  # verbatim from the transcripts, or "" if no evidence
    rationale: str


class Recommendation(BaseModel):
    title: str
    why: str
    first_step: str
    dimension_id: DimensionId
    effort: Literal["low", "medium", "high"]


class Assessment(BaseModel):
    summary: str
    dimensions: list[DimensionScore] = Field(min_length=7, max_length=7)
    strengths: list[str] = Field(min_length=2, max_length=3)
    gaps: list[str] = Field(min_length=2, max_length=3)
    recommendations: list[Recommendation] = Field(min_length=3, max_length=5)

    @model_validator(mode="after")
    def _one_score_per_dimension(self) -> Assessment:
        _require_each_dimension_once([d.dimension_id for d in self.dimensions], "dimensions")
        return self

    def score_for(self, dimension_id: str) -> DimensionScore:
        return next(d for d in self.dimensions if d.dimension_id == dimension_id)


class LLMUsage(BaseModel):
    input_tokens: int | None = None  # uncached input only
    output_tokens: int | None = None
    cache_read_tokens: int | None = None  # prompt-cache hits (billed at ~10%)
    cache_write_tokens: int | None = None  # prompt-cache writes (billed at 125%)
    duration_ms: int = 0
    cached_response: bool = False  # served from the app's response cache: no API call


# --- Role profile and fit ------------------------------------------------------------


class RoleRequirement(BaseModel):
    dimension_id: DimensionId
    weight: int = Field(ge=1, le=3)
    target: int = Field(ge=1, le=5)
    why: str = Field(min_length=1, max_length=250)


class RoleProfile(BaseModel):
    id: str
    title: str
    summary: str
    source: str
    requirements: list[RoleRequirement] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def _one_requirement_per_dimension(self) -> RoleProfile:
        _require_each_dimension_once([r.dimension_id for r in self.requirements], "requirements")
        return self

    def requirement(self, dimension_id: str) -> RoleRequirement:
        return next(r for r in self.requirements if r.dimension_id == dimension_id)


class DimensionFit(BaseModel):
    dimension_id: DimensionId
    score: int
    target: int
    weight: int
    fit: float  # min(score / target, 1.0)
    gap: int  # max(target - score, 0)
    priority: int  # weight * gap


class RoleFit(BaseModel):
    role_id: str
    role_title: str
    fit_percent: int = Field(ge=0, le=100)
    band: FitBand
    dimensions: list[DimensionFit]  # sorted by priority, highest first
    meets: list[DimensionId]
    gaps: list[DimensionId]  # sorted by priority, highest first


# --- Report --------------------------------------------------------------------------


class Metrics(BaseModel):
    stt_ms: list[int] = Field(default_factory=list)
    tts_ms: list[int] = Field(default_factory=list)
    llm_followup_ms: int | None = None
    llm_assess_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_write_tokens: int | None = None
    cached_response: bool = False
    est_cost_usd: float | None = None


class Report(BaseModel):
    assessment: Assessment
    role_fit: RoleFit
    overall_score: float  # mean of the 7 scores, computed in Python
    level: Level
    provider: ProviderName
    model: str
    generated_at: datetime
    metrics: Metrics


# --- HTTP request bodies (SPEC §10) ----------------------------------------------------


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=600)


class FollowUpRequest(BaseModel):
    provider: ProviderName | None = None  # None = server default
    answers: list[Answer] = Field(min_length=1, max_length=10)


class AssessRequest(BaseModel):
    provider: ProviderName | None = None
    answers: list[Answer] = Field(min_length=1, max_length=10)
    client_metrics: Metrics | None = None


# --- Errors --------------------------------------------------------------------------


class AppError(Exception):
    """An error whose message is safe to show to the user (no keys, no stack traces)."""

    status_code = 500

    def __init__(self, code: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ConfigError(AppError):
    status_code = 503


class LLMError(AppError):
    status_code = 502


class VoiceError(AppError):
    status_code = 502


# --- Provider interfaces -------------------------------------------------------------


class LLMProvider(Protocol):
    name: ProviderName
    model: str

    async def follow_up(
        self, answers: list[Answer], role: RoleProfile
    ) -> tuple[str, DimensionId | None, LLMUsage]:
        """Return one follow-up question (≤ 40 words) and the dimension it targets."""
        ...

    async def assess(self, answers: list[Answer], role: RoleProfile) -> tuple[Assessment, LLMUsage]:
        """Score the answers against the generic rubric. Never computes the role fit."""
        ...


class VoiceProvider(Protocol):
    name: str

    async def transcribe(self, audio: bytes, mime_type: str) -> str:
        """Speech to text. Raises VoiceError on failure."""
        ...

    async def synthesize(self, text: str) -> bytes:
        """Text to speech as audio/mpeg. b"" means no audio available (UI shows text)."""
        ...
