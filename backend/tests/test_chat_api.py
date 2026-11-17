"""Chat API tests. The provider is replaced by FakeProvider: no Ollama, no model."""

import json
from collections.abc import AsyncGenerator, Iterator, Sequence

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.llm import (
    ChatChunk,
    ChatMessage,
    GenerationOptions,
    LLMProvider,
    LLMProviderError,
    ModelNotFoundError,
    ProviderUnavailableError,
)
from app.llm.deps import get_provider
from app.llm.fake import FakeProvider
from app.main import app

USER_MESSAGE = {"role": "user", "content": "O que é um token?"}


class BreaksMidStreamProvider(FakeProvider):
    """Yields one piece of the answer and then fails, like a GPU running out of memory."""

    async def chat_stream(
        self,
        model: str,
        messages: Sequence[ChatMessage],
        options: GenerationOptions | None = None,
    ) -> AsyncGenerator[ChatChunk]:
        yield ChatChunk(content="Um token ")
        raise LLMProviderError("CUDA out of memory")


@pytest.fixture
def use_provider() -> Iterator[None]:
    """Clean up dependency overrides after each test so tests cannot leak into each other."""
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    yield
    app.dependency_overrides.clear()


def client_with(provider: LLMProvider) -> TestClient:
    app.dependency_overrides[get_provider] = lambda: provider
    return TestClient(app)


def parse_sse(body: str) -> list[tuple[str, dict[str, object]]]:
    events: list[tuple[str, dict[str, object]]] = []
    for block in body.strip().split("\n\n"):
        name_line, data_line = block.split("\n")
        events.append(
            (name_line.removeprefix("event: "), json.loads(data_line.removeprefix("data: ")))
        )
    return events


pytestmark = pytest.mark.usefixtures("use_provider")


def test_chat_streams_tokens_and_ends_with_stats() -> None:
    client = client_with(FakeProvider(reply="Um token é um pedaço de texto."))

    response = client.post("/api/chat", json={"messages": [USER_MESSAGE]})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    tokens = [data["content"] for name, data in events if name == "token"]
    assert "".join(str(token) for token in tokens) == "Um token é um pedaço de texto."
    assert [name for name, _ in events][-1] == "done"
    assert [name for name, _ in events].count("done") == 1
    stats = events[-1][1]
    assert stats["output_tokens"] == 7
    assert stats["tokens_per_second"] == pytest.approx(50.0)


def test_chat_uses_server_defaults_when_model_and_options_are_omitted() -> None:
    provider = FakeProvider()
    client = client_with(provider)

    client.post("/api/chat", json={"messages": [USER_MESSAGE]})

    call = provider.calls[0]
    assert call.model == "qwen3:8b"
    assert call.options.temperature == 0.2
    assert call.options.num_ctx == 8192
    assert call.options.think is False


def test_chat_passes_explicit_model_options_and_history() -> None:
    provider = FakeProvider()
    client = client_with(provider)
    messages = [
        {"role": "system", "content": "Responda em uma frase."},
        {"role": "user", "content": "Oi"},
        {"role": "assistant", "content": "Olá!"},
        USER_MESSAGE,
    ]

    client.post(
        "/api/chat",
        json={
            "model": "qwen3:4b",
            "messages": messages,
            "options": {"temperature": 1.0, "num_ctx": 2048, "think": True},
        },
    )

    call = provider.calls[0]
    assert call.model == "qwen3:4b"
    assert [message.role for message in call.messages] == ["system", "user", "assistant", "user"]
    assert call.options.temperature == 1.0
    assert call.options.num_ctx == 2048
    assert call.options.think is True


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (ModelNotFoundError("Model 'x' is not installed. Run: ollama pull x"), 404),
        (ProviderUnavailableError("Could not connect to Ollama. Is it running?"), 503),
        (LLMProviderError("Ollama answered with status 500: boom"), 502),
    ],
)
def test_chat_failure_before_the_first_token_becomes_an_http_error(
    error: LLMProviderError, expected_status: int
) -> None:
    client = client_with(FakeProvider(fail_with=error))

    response = client.post("/api/chat", json={"messages": [USER_MESSAGE]})

    assert response.status_code == expected_status
    assert response.json() == {"detail": str(error)}


def test_chat_failure_after_the_first_token_becomes_an_error_event() -> None:
    client = client_with(BreaksMidStreamProvider())

    response = client.post("/api/chat", json={"messages": [USER_MESSAGE]})

    assert response.status_code == 200
    assert parse_sse(response.text) == [
        ("token", {"content": "Um token ", "thinking": ""}),
        ("error", {"message": "CUDA out of memory"}),
    ]


def test_chat_with_an_empty_answer_sends_only_the_done_event() -> None:
    client = client_with(FakeProvider(reply=""))

    response = client.post("/api/chat", json={"messages": [USER_MESSAGE]})

    assert [name for name, _ in parse_sse(response.text)] == ["done"]


@pytest.mark.parametrize(
    "payload",
    [
        {"messages": []},
        {"messages": [{"role": "assistant", "content": "Olá"}]},
        {"messages": [{"role": "robot", "content": "Oi"}]},
        {"messages": [USER_MESSAGE], "options": {"temperature": 9}},
        {"messages": [USER_MESSAGE], "model": ""},
        {},
    ],
)
def test_chat_rejects_invalid_requests_without_calling_the_provider(
    payload: dict[str, object],
) -> None:
    provider = FakeProvider()
    client = client_with(provider)

    response = client.post("/api/chat", json=payload)

    assert response.status_code == 422
    assert provider.calls == []


def test_models_lists_installed_models_and_the_default() -> None:
    client = client_with(FakeProvider(models=["qwen3:8b", "bge-m3"]))

    response = client.get("/api/models")

    assert response.status_code == 200
    body = response.json()
    assert [model["name"] for model in body["models"]] == ["qwen3:8b", "bge-m3"]
    assert body["default_chat_model"] == "qwen3:8b"


def test_models_returns_503_when_the_provider_is_down() -> None:
    client = client_with(FakeProvider(fail_with=ProviderUnavailableError("down")))

    response = client.get("/api/models")

    assert response.status_code == 503
