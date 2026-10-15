"""Settings from environment / .env (SPEC §12) and the local-only guard for Ollama."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.contracts import ConfigError, ProviderName

ROOT = Path(__file__).resolve().parent.parent
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    llm_provider: ProviderName = "claude"
    anthropic_api_key: SecretStr | None = None
    claude_model: str = "claude-opus-5-5"

    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:1.5b"
    ollama_timeout_s: float = 240.0

    voice_provider: Literal["auto", "elevenlabs", "mock", "none"] = "auto"
    elevenlabs_api_key: SecretStr | None = None
    elevenlabs_voice_id: str = "JBFqnCBsd6RMkjVDRZzb"
    elevenlabs_tts_model: str = "eleven_flash_v2_5"
    elevenlabs_stt_model: str = "scribe_v2"

    role_profile: Path = Path("app/roles/elevenlabs_fde.json")
    save_sessions: bool = False

    @property
    def claude_key_set(self) -> bool:
        return bool(self.anthropic_api_key and self.anthropic_api_key.get_secret_value())

    @property
    def elevenlabs_key_set(self) -> bool:
        return bool(self.elevenlabs_api_key and self.elevenlabs_api_key.get_secret_value())

    @property
    def role_profile_path(self) -> Path:
        return self.role_profile if self.role_profile.is_absolute() else ROOT / self.role_profile


def ensure_loopback_url(url: str) -> str:
    """Return `url` if it points at this machine only; raise ConfigError otherwise.

    Strict on purpose: exact host match (no suffix tricks like 127.0.0.1.evil.com),
    no credentials in the URL, http(s) only.
    """
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        parts.port  # noqa: B018 — raises ValueError on a malformed port
    except ValueError as exc:
        raise ConfigError("ollama_not_local", "The local model URL is not valid.") from exc
    if parts.scheme not in {"http", "https"} or parts.username or parts.password:
        raise ConfigError("ollama_not_local", "The local model URL must be a plain http URL.")
    if host not in LOOPBACK_HOSTS:
        raise ConfigError(
            "ollama_not_local",
            "Local mode only talks to a model on this machine (127.0.0.1, localhost or ::1).",
        )
    return url


@lru_cache
def get_settings() -> Settings:
    # ARF_ENV_FILE lets tests run with no .env at all (set it to an empty string).
    env_file = os.environ.get("ARF_ENV_FILE", str(ROOT / ".env")) or None
    return Settings(_env_file=env_file)
