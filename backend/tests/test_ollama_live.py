"""Tests against a real Ollama server. Deselected by default; run with: uv run pytest -m live -s"""

import pytest

from app.core.config import get_settings
from app.llm import ChatMessage, GenerationOptions, ModelNotFoundError
from app.llm.ollama import OllamaProvider

pytestmark = [pytest.mark.anyio, pytest.mark.live]


async def test_real_model_streams_an_answer_with_stats() -> None:
    settings = get_settings()
    provider = OllamaProvider(settings.ollama_base_url, settings.request_timeout_seconds)
    try:
        chunks = [
            chunk
            async for chunk in provider.chat_stream(
                settings.chat_model,
                [ChatMessage(role="user", content="Responda apenas com a palavra: pronto")],
                GenerationOptions(temperature=0.0, max_tokens=32),
            )
        ]
    finally:
        await provider.aclose()

    text = "".join(chunk.content for chunk in chunks)
    stats = chunks[-1].stats
    assert chunks[-1].done is True
    assert stats is not None
    assert stats.output_tokens > 0
    assert stats.tokens_per_second > 0
    assert "pronto" in text.lower()
    print(
        f"\n{settings.chat_model}: {len(chunks)} chunks, {stats.output_tokens} tokens, "
        f"{stats.tokens_per_second:.1f} tokens/s, load {stats.load_seconds:.1f}s, text={text!r}"
    )


async def test_real_server_lists_the_chat_model() -> None:
    settings = get_settings()
    provider = OllamaProvider(settings.ollama_base_url)
    try:
        names = [model.name for model in await provider.list_models()]
    finally:
        await provider.aclose()

    assert settings.chat_model in names


async def test_real_server_reports_a_missing_model() -> None:
    provider = OllamaProvider(get_settings().ollama_base_url)
    try:
        with pytest.raises(ModelNotFoundError):
            async for _ in provider.chat_stream(
                "this-model-does-not-exist:1b", [ChatMessage(role="user", content="oi")]
            ):
                pass
    finally:
        await provider.aclose()
