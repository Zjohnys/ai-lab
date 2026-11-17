from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence

from app.llm.types import ChatChunk, ChatMessage, GenerationOptions, ModelInfo


class LLMProviderError(Exception):
    """Any failure while talking to the model provider."""


class ProviderUnavailableError(LLMProviderError):
    """The provider could not be reached (for example, Ollama is not running)."""


class ModelNotFoundError(LLMProviderError):
    """The requested model is not installed in the provider."""


class LLMProvider(ABC):
    """The only door between the application and a language model.

    Features depend on this interface, never on a concrete provider, so that
    tests can use FakeProvider and another backend can be plugged in later.
    """

    @abstractmethod
    def chat_stream(
        self,
        model: str,
        messages: Sequence[ChatMessage],
        options: GenerationOptions | None = None,
    ) -> AsyncIterator[ChatChunk]:
        """Yield the answer piece by piece; the final chunk has done=True and stats."""

    @abstractmethod
    async def embed(self, model: str, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """Return the models installed in the provider."""

    async def aclose(self) -> None:  # noqa: B027 - optional hook, not abstract on purpose
        """Release network resources. Providers without any can keep this default."""
