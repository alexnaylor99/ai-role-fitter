"""ElevenLabs voice adapter, with all HTTP faked by respx (no network, no real key)."""

from __future__ import annotations

import logging

import httpx
import pytest
import respx

from app.config import Settings
from app.contracts import VoiceError
from app.voice import elevenlabs
from app.voice.elevenlabs import ElevenLabsVoice

KEY = "sk-test-SECRET-KEY-123"
STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/JBFqnCBsd6RMkjVDRZzb"


@pytest.fixture
def voice(monkeypatch):
    async def no_sleep(_):
        return None

    monkeypatch.setattr(elevenlabs.asyncio, "sleep", no_sleep)
    return ElevenLabsVoice(Settings(elevenlabs_api_key=KEY, _env_file=None))


@respx.mock
async def test_transcribe_success(voice):
    route = respx.post(STT_URL).respond(json={"text": "  hello world \n"})
    assert await voice.transcribe(b"audio", "audio/webm") == "hello world"
    request = route.calls.last.request
    assert request.headers["xi-api-key"] == KEY
    assert b"scribe_v2" in request.content
    assert b"audio/webm" in request.content


@respx.mock
async def test_synthesize_success(voice):
    route = respx.post(TTS_URL).respond(content=b"MP3DATA")
    assert await voice.synthesize("Hi there") == b"MP3DATA"
    request = route.calls.last.request
    assert request.url.params["output_format"] == "mp3_44100_128"
    assert request.headers["xi-api-key"] == KEY
    assert b"eleven_flash_v2_5" in request.content


@respx.mock
async def test_401_is_user_safe(voice):
    respx.post(STT_URL).respond(401, json={"detail": f"bad key {KEY}"})
    with pytest.raises(VoiceError) as info:
        await voice.transcribe(b"audio", "audio/webm")
    assert info.value.code == "voice_auth"
    assert KEY not in info.value.message
    assert "bad key" not in info.value.message


@respx.mock
async def test_429_then_success(voice):
    route = respx.post(TTS_URL).mock(
        side_effect=[httpx.Response(429), httpx.Response(200, content=b"OK")]
    )
    assert await voice.synthesize("Hi") == b"OK"
    assert route.call_count == 2


@respx.mock
async def test_persistent_5xx_gives_error_after_one_retry(voice):
    route = respx.post(STT_URL).respond(503, text="upstream exploded")
    with pytest.raises(VoiceError) as info:
        await voice.transcribe(b"audio", "audio/webm")
    assert route.call_count == 2
    assert "exploded" not in info.value.message


@respx.mock
async def test_timeout(voice):
    route = respx.post(STT_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(VoiceError) as info:
        await voice.transcribe(b"audio", "audio/webm")
    assert info.value.code == "voice_timeout"
    assert route.call_count == 2


@respx.mock
async def test_empty_audio_makes_no_call(voice):
    route = respx.post(STT_URL).respond(json={"text": "x"})
    with pytest.raises(VoiceError) as info:
        await voice.transcribe(b"", "audio/webm")
    assert info.value.code == "empty_audio"
    assert not route.called


@respx.mock
async def test_oversized_audio_makes_no_call(voice):
    route = respx.post(STT_URL).respond(json={"text": "x"})
    with pytest.raises(VoiceError) as info:
        await voice.transcribe(b"x" * (25 * 1024 * 1024 + 1), "audio/webm")
    assert info.value.code == "audio_too_large"
    assert not route.called


@respx.mock
async def test_malformed_reply(voice):
    respx.post(STT_URL).respond(json={"nope": 1})
    with pytest.raises(VoiceError) as info:
        await voice.transcribe(b"audio", "audio/webm")
    assert info.value.code == "voice_bad_response"


@respx.mock
async def test_key_never_in_errors_or_logs(voice, caplog):
    caplog.set_level(logging.DEBUG)
    respx.post(STT_URL).respond(401, text=KEY)
    respx.post(TTS_URL).mock(side_effect=httpx.ConnectError(f"failed with {KEY}"))
    errors = []
    for call in (voice.transcribe(b"a", "audio/webm"), voice.synthesize("hi")):
        with pytest.raises(VoiceError) as info:
            await call
        errors.append(info.value)
    for err in errors:
        assert KEY not in str(err)
        assert KEY not in err.message
        assert KEY not in repr(err)
    assert KEY not in caplog.text
