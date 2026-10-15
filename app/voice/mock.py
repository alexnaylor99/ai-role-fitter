"""Voice stand-in for demos and tests: fixed transcript, no audio (UI shows text only)."""

from __future__ import annotations

from app.contracts import VoiceError

MOCK_TRANSCRIPT = (
    "This is a mock transcript. I use Claude and ChatGPT most weeks, and I built a Python "
    "script that calls an API to transcribe customer calls."
)


class MockVoice:
    name = "mock"

    async def transcribe(self, audio: bytes, mime_type: str) -> str:
        if not audio:
            raise VoiceError("empty_audio", "No audio was recorded.", status_code=400)
        return MOCK_TRANSCRIPT

    async def synthesize(self, text: str) -> bytes:
        return b""  # no audio: the UI shows the question text only
