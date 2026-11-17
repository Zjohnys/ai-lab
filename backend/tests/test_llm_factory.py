import pytest

from app.core.config import Settings
from app.llm.factory import create_provider
from app.llm.fake import FakeProvider
from app.llm.ollama import OllamaProvider


def test_default_settings_build_the_ollama_provider() -> None:
    assert isinstance(create_provider(Settings(_env_file=None)), OllamaProvider)


def test_fake_provider_can_be_selected() -> None:
    settings = Settings(_env_file=None, llm_provider="fake")

    assert isinstance(create_provider(settings), FakeProvider)


def test_unknown_provider_fails_with_the_supported_values() -> None:
    settings = Settings(_env_file=None, llm_provider="openai")

    with pytest.raises(ValueError, match="ollama, fake"):
        create_provider(settings)
