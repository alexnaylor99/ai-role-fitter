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
        # T8: more bypass attempts
        "http://LOCALHOST.evil.com:11434",
        "http://127.0.0.1.EVIL.com",
        "http://[::ffff:7f00:1]:11434",
        "http://[0:0:0:0:0:ffff:127.0.0.1]:11434",
        "http://user@127.0.0.1:11434",
        "http://:secret@127.0.0.1:11434",
        "http://127.0.0.1@evil.com",
        "http://127.0.0.1:11434@evil.com",
        "http://127.0.0.1\\@evil.com",
        "http://evil.com#@127.0.0.1",
        "http://127.0.0.1\t.evil.com",
        "http://127.0.0.1\n.evil.com",
        "http://127.0.0.1%2eevil.com",
        "http://localhost.:11434",
        "http://127.1:11434",
        "http://2130706433:11434",
        "http://0x7f.0.0.1:11434",
        "http://127.0.0.2:11434",
        "http://[::1%25eth0]:11434",
        "http://127.0.0.1:99999",
        "file:///etc/passwd",
        "HTTP://evil.com",
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


async def test_ollama_does_not_follow_redirects_off_the_machine(monkeypatch, sample_answers):
    import respx

    from app.config import Settings
    from app.contracts import LLMError
    from app.llm.ollama import OllamaLLM

    with respx.mock(assert_all_called=False) as mock:
        mock.post("http://127.0.0.1:11434/api/chat").respond(
            307, headers={"location": "http://evil.example/api/chat"}
        )
        evil = mock.post("http://evil.example/api/chat").respond(200, json={})
        with pytest.raises(LLMError):
            await OllamaLLM(Settings(llm_provider="ollama")).assess(sample_answers, _role())
        assert not evil.called


def _role():
    from app.main import get_role

    return get_role()
