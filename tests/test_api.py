import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.contracts import Report
from app.main import app
from app.voice.mock import MOCK_TRANSCRIPT


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _answers(sample_answers):
    return [a.model_dump() for a in sample_answers]


def test_health_in_mock_mode(client):
    body = client.get("/api/health").json()
    assert body["llm_default"] == "mock"
    assert body["providers"]["mock"]["configured"] is True
    assert body["providers"]["claude"]["configured"] is False
    assert body["voice"]["configured"] is False


def test_questions_and_role(client):
    assert len(client.get("/api/questions").json()) == 7
    role = client.get("/api/role").json()
    assert role["id"] == "elevenlabs_fde"


def test_sample_report_is_a_valid_report(client):
    res = client.get("/api/sample-report")
    assert res.status_code == 200
    Report.model_validate(res.json())


def test_full_mock_interview(client, sample_answers):
    answers = _answers(sample_answers)
    follow = client.post("/api/follow-up", json={"answers": answers[:7]})
    assert follow.status_code == 200
    assert follow.json()["question"]["id"] == "followup"

    res = client.post(
        "/api/assess",
        json={"provider": "mock", "answers": answers, "client_metrics": {"stt_ms": [900]}},
    )
    assert res.status_code == 200
    report = Report.model_validate(res.json())
    assert report.provider == "mock"
    assert 0 <= report.role_fit.fit_percent <= 100
    assert report.role_fit.role_id == "elevenlabs_fde"
    assert report.metrics.stt_ms == [900]
    assert report.metrics.est_cost_usd == 0.0


def test_claude_without_key_gives_clear_error(client, sample_answers):
    res = client.post(
        "/api/assess", json={"provider": "claude", "answers": _answers(sample_answers)}
    )
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "claude_not_configured"


def test_ollama_refuses_non_local_url(client, sample_answers, monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://example.com:11434")
    get_settings.cache_clear()
    res = client.post(
        "/api/assess", json={"provider": "ollama", "answers": _answers(sample_answers)}
    )
    assert res.json()["error"]["code"] == "ollama_not_local"


def test_invalid_request_has_error_shape(client):
    res = client.post("/api/assess", json={"answers": []})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "invalid_request"


def test_tts_without_voice_is_204(client):
    assert client.post("/api/tts", json={"text": "Hello"}).status_code == 204


def test_transcribe_without_voice_is_503(client):
    res = client.post("/api/transcribe", files={"audio": ("a.webm", b"x", "audio/webm")})
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "voice_not_configured"


def test_transcribe_with_mock_voice(client, monkeypatch):
    monkeypatch.setenv("VOICE_PROVIDER", "mock")
    get_settings.cache_clear()
    res = client.post(
        "/api/transcribe", files={"audio": ("a.webm", b"fake-audio", "audio/webm;codecs=opus")}
    )
    assert res.status_code == 200
    assert res.json()["text"] == MOCK_TRANSCRIPT


def test_transcribe_rejects_non_audio(client, monkeypatch):
    monkeypatch.setenv("VOICE_PROVIDER", "mock")
    get_settings.cache_clear()
    res = client.post("/api/transcribe", files={"audio": ("a.txt", b"hi", "text/plain")})
    assert res.status_code == 415


def test_sessions_not_saved_by_default(client, sample_answers, tmp_path, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "SESSIONS_DIR", tmp_path / "sessions")
    client.post("/api/assess", json={"answers": _answers(sample_answers)})
    assert not (tmp_path / "sessions").exists()


def test_sessions_saved_when_enabled(client, sample_answers, tmp_path, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "SESSIONS_DIR", tmp_path / "sessions")
    monkeypatch.setenv("SAVE_SESSIONS", "true")
    get_settings.cache_clear()
    client.post("/api/assess", json={"answers": _answers(sample_answers)})
    assert len(list((tmp_path / "sessions").glob("session-*.json"))) == 1


def test_frontend_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "AI Role Fitter" in res.text


class _CountingVoice:
    """Fake voice that records how often audio is synthesised (no network)."""

    name = "counting"

    def __init__(self):
        self.calls = 0

    async def transcribe(self, audio: bytes, mime_type: str) -> str:
        return "x"

    async def synthesize(self, text: str) -> bytes:
        self.calls += 1
        return b"ID3-fake-mp3"


@pytest.fixture
def counting_voice(monkeypatch, tmp_path):
    import app.main as main

    voice = _CountingVoice()
    monkeypatch.setattr(main, "get_voice", lambda settings: voice)
    monkeypatch.setattr(main, "TTS_CACHE_DIR", tmp_path / "tts_cache")
    return voice


def test_fixed_question_audio_is_synthesised_once(client, counting_voice):
    from app.rubric import QUESTIONS

    text = QUESTIONS[0]["text"]
    first = client.post("/api/tts", json={"text": text})
    second = client.post("/api/tts", json={"text": text})
    assert first.headers["X-TTS-Cache"] == "miss"
    assert second.headers["X-TTS-Cache"] == "hit"
    assert second.content == first.content == b"ID3-fake-mp3"
    assert counting_voice.calls == 1


def test_follow_up_audio_is_never_cached(client, counting_voice, tmp_path):
    text = "A personalised follow-up question?"
    client.post("/api/tts", json={"text": text})
    res = client.post("/api/tts", json={"text": text})
    assert res.headers["X-TTS-Cache"] == "miss"
    assert counting_voice.calls == 2
    assert not (tmp_path / "tts_cache").exists()
