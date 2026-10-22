"""FastAPI app: HTTP API (SPEC §10) and the static frontend. Binds to 127.0.0.1 only."""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import LOOPBACK_HOSTS, ROOT, get_settings
from app.contracts import (
    AppError,
    AssessRequest,
    FollowUpRequest,
    Metrics,
    Report,
    RoleProfile,
    TTSRequest,
)
from app.fit import compute_role_fit, load_role
from app.llm import estimate_cost, get_llm
from app.rubric import FOLLOW_UP_QUESTIONS, QUESTIONS, level_for, overall_score
from app.voice import get_voice

log = logging.getLogger("ai_role_fitter")

MAX_AUDIO_BYTES = 25 * 1024 * 1024
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
SAMPLES_DIR = ROOT / "samples"
SESSIONS_DIR = ROOT / "sessions"
TTS_CACHE_DIR = ROOT / "tts_cache"  # git-ignored
# Fixed texts whose audio can be cached: the 7 questions, plus the rule-based follow-ups used
# in local and mock modes. Claude's follow-ups are written per person and never cached.
FIXED_QUESTION_TEXTS = frozenset(
    [q["text"] for q in QUESTIONS] + list(FOLLOW_UP_QUESTIONS.values())
)


@lru_cache
def get_role() -> RoleProfile:
    return load_role(get_settings().role_profile_path)


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_role()  # fail fast on an invalid role profile (F12)
    yield


app = FastAPI(title="AI Role Fitter", lifespan=lifespan)


# --- Errors: always {error: {code, message}}, never keys or stack traces -------------


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


# --- Local requests only ----------------------------------------------------------


@app.middleware("http")
async def _local_requests_only(request: Request, call_next):
    """Refuse requests whose Host isn't this machine, and cross-site writes.

    Binding to 127.0.0.1 isn't enough on its own: with DNS rebinding a web page can point
    its own domain at 127.0.0.1 and then call this API (and spend the API keys) as if it
    were same-origin. The browser still sends the page's domain as the Host header.
    """
    host_header = request.headers.get("host", "")
    host = urlsplit(f"//{host_header}").hostname or ""
    if host not in LOOPBACK_HOSTS:
        return _error(400, "bad_host", "This app only accepts requests to 127.0.0.1.")
    # A page on another site can still send a "simple" cross-site POST (e.g. a multipart
    # form to /api/transcribe) without a CORS preflight. Browsers always send Origin on
    # those, so refuse any write whose Origin isn't this app.
    origin = request.headers.get("origin")
    if request.method not in SAFE_METHODS and origin is not None:
        if urlsplit(origin).netloc.lower() != host_header.lower():
            return _error(403, "cross_origin", "Requests from other sites are not allowed.")
    return await call_next(request)


@app.exception_handler(AppError)
async def _app_error(_: Request, exc: AppError) -> JSONResponse:
    return _error(exc.status_code, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    return _error(
        422, "invalid_request", f"Invalid request: {where or 'body'} {first.get('msg', '')}"
    )


@app.middleware("http")
async def _unexpected(request: Request, call_next):
    # A middleware, not an exception handler: Starlette re-raises after running a handler
    # for Exception, so uvicorn would log the full traceback and message anyway.
    try:
        return await call_next(request)
    except Exception as exc:
        log.error("Unexpected error: %s", type(exc).__name__)  # type only: may hold data
        return _error(500, "internal_error", "Something went wrong. Please try again.")


# --- Routes ------------------------------------------------------------------------


@app.get("/api/health")
async def health() -> dict:
    s = get_settings()
    ollama = {"configured": False, "reachable": False}
    try:
        provider = get_llm("ollama", s)
        ollama["configured"] = True
        reachable = getattr(provider, "reachable", None)
        ollama["reachable"] = bool(reachable and await reachable())
    except AppError:
        pass
    claude_built = True
    try:
        import app.llm.claude  # noqa: F401
    except ImportError:
        claude_built = False
    return {
        "llm_default": s.llm_provider,
        "providers": {
            "claude": {"configured": s.claude_key_set and claude_built, "reachable": None},
            "ollama": ollama,
            "mock": {"configured": True, "reachable": True},
        },
        "voice": {"configured": get_voice(s) is not None},
    }


@app.get("/api/questions")
async def questions() -> list[dict[str, str]]:
    return QUESTIONS


@app.get("/api/role")
async def role() -> RoleProfile:
    return get_role()


@app.post("/api/tts")
async def tts(body: TTSRequest) -> Response:
    s = get_settings()
    voice = get_voice(s)
    if voice is None:
        return Response(status_code=204)

    # Fixed question texts never change, so their audio is synthesised once and reused:
    # most of an interview's TTS credits. Personalised follow-ups are never cached.
    cache_path = None
    if body.text in FIXED_QUESTION_TEXTS:
        key = f"{voice.name}|{s.elevenlabs_voice_id}|{s.elevenlabs_tts_model}|{body.text}"
        cache_path = TTS_CACHE_DIR / f"{hashlib.sha256(key.encode()).hexdigest()}.mp3"
        if cache_path.is_file():
            return Response(
                content=cache_path.read_bytes(),
                media_type="audio/mpeg",
                headers={"X-TTS-Cache": "hit"},
            )

    audio = await voice.synthesize(body.text)
    if not audio:
        return Response(status_code=204)
    if cache_path is not None:
        # Write then rename, so a crash or a parallel request never serves a partial file.
        TTS_CACHE_DIR.mkdir(exist_ok=True)
        tmp_path = cache_path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        tmp_path.write_bytes(audio)
        tmp_path.replace(cache_path)
    return Response(content=audio, media_type="audio/mpeg", headers={"X-TTS-Cache": "miss"})


@app.post("/api/transcribe")
async def transcribe(audio: Annotated[UploadFile, File()]) -> dict:
    voice = get_voice(get_settings())
    if voice is None:
        raise AppError("voice_not_configured", "Voice isn't set up. Please type your answer.", 503)
    mime = (audio.content_type or "").split(";")[0]
    if not mime.startswith("audio/"):
        raise AppError("bad_audio_type", "Please upload an audio recording.", 415)
    data = await audio.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise AppError(
            "audio_too_large", "That recording is too long. Please keep it shorter.", 413
        )
    start = time.perf_counter()
    text = await voice.transcribe(data, mime)
    return {"text": text, "duration_ms": int((time.perf_counter() - start) * 1000)}


@app.post("/api/follow-up")
async def follow_up(body: FollowUpRequest) -> dict:
    s = get_settings()
    llm = get_llm(body.provider or s.llm_provider, s)
    text, dimension_id, usage = await llm.follow_up(body.answers, get_role())
    return {
        "question": {"id": "followup", "dimension_id": dimension_id, "text": text},
        "duration_ms": usage.duration_ms,
    }


@app.post("/api/assess")
async def assess(body: AssessRequest) -> Report:
    s = get_settings()
    role_profile = get_role()
    llm = get_llm(body.provider or s.llm_provider, s)
    assessment, usage = await llm.assess(body.answers, role_profile)

    metrics = (body.client_metrics or Metrics()).model_copy()
    metrics.llm_assess_ms = usage.duration_ms
    metrics.input_tokens = usage.input_tokens
    metrics.output_tokens = usage.output_tokens
    metrics.cache_read_tokens = usage.cache_read_tokens
    metrics.cache_write_tokens = usage.cache_write_tokens
    metrics.cached_response = usage.cached_response
    metrics.est_cost_usd = estimate_cost(llm.model, usage)

    mean = overall_score(assessment)
    report = Report(
        assessment=assessment,
        role_fit=compute_role_fit(assessment, role_profile),
        overall_score=mean,
        level=level_for(mean),
        provider=llm.name,
        model=llm.model,
        generated_at=datetime.now(UTC),
        metrics=metrics,
    )
    if s.save_sessions:
        _save_session(body, report)
    return report


@app.get("/api/sample-report")
async def sample_report() -> Report:
    return Report.model_validate_json((SAMPLES_DIR / "sample_report.json").read_text())


@app.get("/api/demo-answers")
async def demo_answers() -> Response:
    path = SAMPLES_DIR / "demo_answers.json"
    if not path.exists():
        raise AppError("not_found", "No demo answers available.", 404)
    return FileResponse(path, media_type="application/json")


def _save_session(body: AssessRequest, report: Report) -> None:
    SESSIONS_DIR.mkdir(exist_ok=True)
    stamp = report.generated_at.strftime("%Y%m%d-%H%M%S")
    payload = {"answers": [a.model_dump() for a in body.answers], "report": report.model_dump()}
    path: Path = SESSIONS_DIR / f"session-{stamp}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


# Static frontend last, so /api/* routes take precedence.
app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")
