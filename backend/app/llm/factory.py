from app.core.config import Settings
from app.llm.fake import FakeProvider
from app.llm.ollama import OllamaProvider
from app.llm.provider import LLMProvider


def create_provider(settings: Settings) -> LLMProvider:
    """Build the provider named in settings. Only local providers exist, by design."""
    if settings.llm_provider == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            timeout_seconds=settings.request_timeout_seconds,
        )
    if settings.llm_provider == "fake":
        return FakeProvider()
    raise ValueError(
        f"Unknown LLM_PROVIDER '{settings.llm_provider}'. Supported values: ollama, fake."
    )
