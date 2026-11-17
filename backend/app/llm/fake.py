import hashlib
import re
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass

from app.llm.provider import LLMProvider, LLMProviderError
from app.llm.types import ChatChunk, ChatMessage, GenerationOptions, GenerationStats, ModelInfo

_FAKE_TOKENS_PER_SECOND = 50.0


@dataclass(frozen=True)
class FakeCall:
    """What a test can inspect about one chat_stream call."""

    model: str
    messages: tuple[ChatMessage, ...]
    options: GenerationOptions


class FakeProvider(LLMProvider):
    """Deterministic provider for tests and CI: no network, no model, same output every time."""

    def __init__(
        self,
        reply: str = "Resposta simulada do modelo.",
        *,
        models: Sequence[str] = ("fake-model",),
        embedding_dim: int = 8,
        fail_with: LLMProviderError | None = None,
    ) -> None:
        self.reply = reply
        self.calls: list[FakeCall] = []
        self._models = tuple(models)
        self._embedding_dim = embedding_dim
        self._fail_with = fail_with

    async def chat_stream(
        self,
        model: str,
        messages: Sequence[ChatMessage],
        options: GenerationOptions | None = None,
    ) -> AsyncIterator[ChatChunk]:
        self.calls.append(FakeCall(model, tuple(messages), options or GenerationOptions()))
        if self._fail_with is not None:
            raise self._fail_with

        # One "token" per word, keeping the whitespace so the pieces join back exactly.
        pieces = re.findall(r"\S+\s*", self.reply)
        for piece in pieces:
            yield ChatChunk(content=piece)

        generation_seconds = len(pieces) / _FAKE_TOKENS_PER_SECOND
        yield ChatChunk(
            done=True,
            stats=GenerationStats(
                prompt_tokens=sum(len(message.content.split()) for message in messages),
                output_tokens=len(pieces),
                generation_seconds=generation_seconds,
                total_seconds=generation_seconds,
            ),
        )

    async def embed(self, model: str, texts: Sequence[str]) -> list[list[float]]:
        if self._fail_with is not None:
            raise self._fail_with
        return [self._vector_for(text) for text in texts]

    async def list_models(self) -> list[ModelInfo]:
        if self._fail_with is not None:
            raise self._fail_with
        return [ModelInfo(name=name, size_bytes=0) for name in self._models]

    def _vector_for(self, text: str) -> list[float]:
        """Same text, same vector. The values carry no meaning; they only need to be stable."""
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [digest[i % len(digest)] / 127.5 - 1.0 for i in range(self._embedding_dim)]
