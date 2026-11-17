"""OllamaProvider tests. No server and no model: httpx.MockTransport answers the requests."""

import json
from collections.abc import Callable

import httpx
import pytest

from app.llm import (
    ChatMessage,
    GenerationOptions,
    LLMProviderError,
    ModelNotFoundError,
    ProviderUnavailableError,
)
from app.llm.ollama import OllamaProvider

pytestmark = pytest.mark.anyio

QUESTION = [ChatMessage(role="user", content="Oi")]

Handler = Callable[[httpx.Request], httpx.Response]


def make_provider(handler: Handler) -> OllamaProvider:
    client = httpx.AsyncClient(
        base_url="http://ollama.test", transport=httpx.MockTransport(handler)
    )
    return OllamaProvider(client=client)


def ndjson(*lines: dict[str, object]) -> bytes:
    return "".join(json.dumps(line) + "\n" for line in lines).encode()


STREAM = ndjson(
    {"message": {"role": "assistant", "content": "", "thinking": "Pensando."}, "done": False},
    {"message": {"role": "assistant", "content": "Olá"}, "done": False},
    {"message": {"role": "assistant", "content": ", mundo"}, "done": False},
    {
        "message": {"role": "assistant", "content": ""},
        "done": True,
        "total_duration": 3_000_000_000,
        "load_duration": 500_000_000,
        "prompt_eval_count": 12,
        "prompt_eval_duration": 250_000_000,
        "eval_count": 72,
        "eval_duration": 2_000_000_000,
    },
)


async def test_chat_stream_yields_content_thinking_and_final_stats() -> None:
    provider = make_provider(lambda request: httpx.Response(200, content=STREAM))

    chunks = [chunk async for chunk in provider.chat_stream("qwen3:8b", QUESTION)]

    assert "".join(chunk.content for chunk in chunks) == "Olá, mundo"
    assert chunks[0].thinking == "Pensando."
    assert [chunk.done for chunk in chunks] == [False, False, False, True]
    stats = chunks[-1].stats
    assert stats is not None
    assert stats.prompt_tokens == 12
    assert stats.output_tokens == 72
    assert stats.load_seconds == pytest.approx(0.5)
    assert stats.generation_seconds == pytest.approx(2.0)
    assert stats.total_seconds == pytest.approx(3.0)
    assert stats.tokens_per_second == pytest.approx(36.0)


async def test_chat_stream_sends_the_expected_payload() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=STREAM)

    provider = make_provider(handler)
    options = GenerationOptions(temperature=0.7, num_ctx=4096, max_tokens=64, seed=42, think=True)

    async for _ in provider.chat_stream("qwen3:8b", QUESTION, options):
        pass

    assert seen[0].url.path == "/api/chat"
    assert json.loads(seen[0].content) == {
        "model": "qwen3:8b",
        "messages": [{"role": "user", "content": "Oi"}],
        "stream": True,
        "think": True,
        "options": {"temperature": 0.7, "num_ctx": 4096, "num_predict": 64, "seed": 42},
    }


async def test_default_options_turn_thinking_off_and_omit_optional_fields() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=STREAM)

    provider = make_provider(handler)

    async for _ in provider.chat_stream("qwen3:8b", QUESTION):
        pass

    payload = json.loads(seen[0].content)
    assert payload["think"] is False
    assert payload["options"] == {"temperature": 0.2, "num_ctx": 8192}


async def test_missing_model_raises_model_not_found_with_the_fix() -> None:
    provider = make_provider(
        lambda request: httpx.Response(404, json={"error": "model 'nope' not found"})
    )

    with pytest.raises(ModelNotFoundError, match="ollama pull nope"):
        async for _ in provider.chat_stream("nope", QUESTION):
            pass


async def test_server_error_keeps_the_detail_from_ollama() -> None:
    provider = make_provider(lambda request: httpx.Response(500, json={"error": "out of memory"}))

    with pytest.raises(LLMProviderError, match="out of memory"):
        async for _ in provider.chat_stream("qwen3:8b", QUESTION):
            pass


async def test_connection_refused_raises_provider_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = make_provider(handler)

    with pytest.raises(ProviderUnavailableError):
        async for _ in provider.chat_stream("qwen3:8b", QUESTION):
            pass
    with pytest.raises(ProviderUnavailableError):
        await provider.list_models()


async def test_timeout_is_reported_as_a_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    provider = make_provider(handler)

    with pytest.raises(LLMProviderError, match="timeout"):
        async for _ in provider.chat_stream("qwen3:8b", QUESTION):
            pass


async def test_error_in_the_middle_of_the_stream_is_raised_after_partial_content() -> None:
    body = ndjson(
        {"message": {"role": "assistant", "content": "Olá"}, "done": False},
        {"error": "CUDA out of memory"},
    )
    provider = make_provider(lambda request: httpx.Response(200, content=body))
    received: list[str] = []

    with pytest.raises(LLMProviderError, match="CUDA out of memory"):
        async for chunk in provider.chat_stream("qwen3:8b", QUESTION):
            received.append(chunk.content)

    assert received == ["Olá"]


async def test_malformed_line_raises_instead_of_passing_garbage_on() -> None:
    provider = make_provider(lambda request: httpx.Response(200, content=b"<html>proxy</html>\n"))

    with pytest.raises(LLMProviderError, match="Unexpected response"):
        async for _ in provider.chat_stream("qwen3:8b", QUESTION):
            pass


async def test_list_models_maps_name_size_and_details() -> None:
    tags = {
        "models": [
            {
                "name": "qwen3:8b",
                "size": 5_200_000_000,
                "details": {"parameter_size": "8.2B", "quantization_level": "Q4_K_M"},
            },
            {"name": "bge-m3", "size": 1_200_000_000},
        ]
    }
    provider = make_provider(lambda request: httpx.Response(200, json=tags))

    models = await provider.list_models()

    assert [model.name for model in models] == ["qwen3:8b", "bge-m3"]
    assert models[0].size_bytes == 5_200_000_000
    assert models[0].quantization == "Q4_K_M"
    assert models[1].quantization is None


async def test_embed_sends_all_texts_and_returns_one_vector_each() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2], [0.3, 0.4]]})

    provider = make_provider(handler)

    vectors = await provider.embed("bge-m3", ["a", "b"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert seen[0].url.path == "/api/embed"
    assert json.loads(seen[0].content) == {"model": "bge-m3", "input": ["a", "b"]}


async def test_embed_with_no_texts_makes_no_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no request expected")

    provider = make_provider(handler)

    assert await provider.embed("bge-m3", []) == []


async def test_embed_rejects_a_response_with_the_wrong_number_of_vectors() -> None:
    provider = make_provider(lambda request: httpx.Response(200, json={"embeddings": [[0.1]]}))

    with pytest.raises(LLMProviderError, match="1 embeddings for 2 texts"):
        await provider.embed("bge-m3", ["a", "b"])
