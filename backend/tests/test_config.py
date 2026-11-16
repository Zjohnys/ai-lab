import pytest

from app.core.config import Settings


def test_defaults_point_to_local_ollama() -> None:
    settings = Settings(_env_file=None)

    assert settings.llm_provider == "ollama"
    assert settings.ollama_base_url.startswith("http://localhost")


def test_environment_variable_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAT_MODEL", "qwen3:4b")

    settings = Settings(_env_file=None)

    assert settings.chat_model == "qwen3:4b"
