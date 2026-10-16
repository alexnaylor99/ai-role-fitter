"""ElevenLabs voice provider: Scribe v2 speech-to-text and Flash v2.5 text-to-speech."""

from __future__ import annotations

import asyncio

import httpx

from app.config import Settings
from app.contracts import VoiceError

BASE_URL = "https://api.elevenlabs.io/v1"
STT_TIMEOUT_S = 30.0
TTS_TIMEOUT_S = 15.0
MAX_AUDIO_BYTES = 25 * 1024 * 1024
RETRY_BACKOFF_S = 0.5
TTS_OUTPUT_FORMAT = "mp3_44100_128"


class ElevenLabsVoice:
    name = "elevenlabs"

    def __init__(self, settings: Settings):
        self._settings = settings

    def _headers(self) -> dict[str, str]:
        key = self._settings.elevenlabs_api_key
        return {"xi-api-key": key.get_secret_value() if key else ""}

    async def _post(self, url: str, timeout: float, what: str, **kwargs) -> httpx.Response:
        """POST with one retry on 429/5xx or a transport error. Errors carry user-safe text."""
        last_status: int | None = None
        for attempt in range(2):
            if attempt:
                await asyncio.sleep(RETRY_BACKOFF_S)
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, headers=self._headers(), **kwargs)
            except httpx.TimeoutException as exc:
                if attempt == 0:
                    last_status = None
                    continue
                raise VoiceError(
                    "voice_timeout", f"The voice service timed out during {what}."
                ) from exc
            except httpx.HTTPError as exc:
                raise VoiceError(
                    "voice_unreachable", f"Could not reach the voice service for {what}."
                ) from exc
            status = response.status_code
            if status == 429 or status >= 500:
                last_status = status
                continue
            if status in (401, 403):
                raise VoiceError(
                    "voice_auth", "The voice service rejected the API key.", status_code=502
                )
            if status >= 400:
                raise VoiceError("voice_failed", f"The voice service could not complete {what}.")
            return response
        if last_status == 429:
            raise VoiceError(
                "voice_rate_limited",
                "The voice service is busy. Please try again shortly.",
                status_code=429,
            )
        if last_status is None:
            raise VoiceError("voice_timeout", f"The voice service timed out during {what}.")
        raise VoiceError("voice_unavailable", "The voice service is unavailable right now.")

    async def transcribe(self, audio: bytes, mime_type: str) -> str:
        if not audio:
            raise VoiceError("empty_audio", "No audio was recorded.", status_code=400)
        if len(audio) > MAX_AUDIO_BYTES:
            raise VoiceError(
                "audio_too_large", "The recording is too long (25 MB maximum).", status_code=413
            )
        response = await self._post(
            f"{BASE_URL}/speech-to-text",
            STT_TIMEOUT_S,
            "transcription",
            files={"file": ("audio", audio, mime_type or "application/octet-stream")},
            data={"model_id": self._settings.elevenlabs_stt_model},
        )
        try:
            text = response.json()["text"]
        except (ValueError, KeyError, TypeError) as exc:
            raise VoiceError(
                "voice_bad_response", "The voice service sent an invalid reply."
            ) from exc
        if not isinstance(text, str):
            raise VoiceError("voice_bad_response", "The voice service sent an invalid reply.")
        return text.strip()

    async def synthesize(self, text: str) -> bytes:
        if not text.strip():
            return b""
        response = await self._post(
            f"{BASE_URL}/text-to-speech/{self._settings.elevenlabs_voice_id}",
            TTS_TIMEOUT_S,
            "speech synthesis",
            params={"output_format": TTS_OUTPUT_FORMAT},
            json={"text": text, "model_id": self._settings.elevenlabs_tts_model},
        )
        return response.content

    async def reachable(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{BASE_URL}/models", headers=self._headers())
        except httpx.HTTPError:
            return False
        return response.status_code == 200
