import pytest

from app.config import ensure_loopback_url, get_settings
from app.contracts import ConfigError


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:11434",
        "http://localhost:11434",
        "http://LOCALHOST:11434",
        "http://[::1]:11434",
        "https://127.0.0.1",
    ],
)
def test_loopback_urls_allowed(url):
    assert ensure_loopback_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1.evil.com:11434",
        "http://localhost.evil.com",
        "http://evil.com/127.0.0.1",
        "http://user:pass@127.0.0.1:11434",
        "http://evil.com@127.0.0.1",
        "http://192.168.1.10:11434",
        "http://0.0.0.0:11434",
        "http://[::ffff:127.0.0.1]:11434",
        "ftp://127.0.0.1",
        "127.0.0.1:11434",
        "http://127.0.0.1:notaport",
        "",
    ],
)
def test_non_loopback_urls_refused(url):
    with pytest.raises(ConfigError) as exc:
        ensure_loopback_url(url)
    assert exc.value.code == "ollama_not_local"


def test_settings_ignore_real_env_file_in_tests():
    s = get_settings()
    assert not s.claude_key_set
    assert not s.elevenlabs_key_set
    assert s.llm_provider == "mock"


def test_keys_are_hidden_in_repr(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-a-real-key")
    get_settings.cache_clear()
    s = get_settings()
    assert s.claude_key_set
    assert "sk-test-not-a-real-key" not in repr(s)
