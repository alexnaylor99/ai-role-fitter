"""Voice provider factory. Returns None when voice is off (the UI falls back to typing)."""

from __future__ import annotations

from app.config import Settings
from app.contracts import VoiceProvider


def get_voice(settings: Settings) -> VoiceProvider | None:
    choice = settings.voice_provider
    if choice == "none":
        return None
    if choice == "mock":
        from app.voice.mock import MockVoice

        return MockVoice()
    if choice == "auto" and not settings.elevenlabs_key_set:
        return None
    if not settings.elevenlabs_key_set:  # explicitly "elevenlabs" but no key
        return None
    try:
        from app.voice.elevenlabs import ElevenLabsVoice
    except ImportError:
        return None  # not built yet (T1)
    return ElevenLabsVoice(settings)
