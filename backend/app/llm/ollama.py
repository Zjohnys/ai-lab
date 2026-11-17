from collections.abc import AsyncGenerator, Sequence

import httpx
from pydantic import BaseModel, ValidationError

from app.llm.provider import (
    LLMProvider,
    LLMProviderError,
    ModelNotFoundError,
    ProviderUnavailableError,
)
from app.llm.types import ChatChunk, ChatMessage, GenerationOptions, GenerationStats, ModelInfo

_NANOSECONDS = 1_000_000_000


# --- Wire format: what Ollama sends back. Validated before anything else uses it. ---


class _ChatLineMessage(BaseModel):
    content: str = ""
    thinking: str | None = None


class _ChatLine(BaseModel):
    """One NDJSON line of a streamed /api/chat response. Durations are in nanoseconds."""

    message: _ChatLineMessage | None = None
    done: bool = False
    error: str | None = None
    total_duration: int = 0
    load_duration: int = 0
    prompt_eval_count: int = 0
    prompt_eval_duration: int = 0
    eval_count: int = 0
    eval_duration: int = 0

    def to_stats(self) -> GenerationStats:
        return GenerationStats(
            prompt_tokens=self.prompt_eval_count,
            output_tokens=self.eval_count,
            load_seconds=self.load_duration / _NANOSECONDS,
            prompt_eval_seconds=self.prompt_eval_duration / _NANOSECONDS,
            generation_seconds=self.eval_duration / _NANOSECONDS,
            total_seconds=self.total_duration / _NANOSECONDS,
        )


class _TagDetails(BaseModel):
    parameter_size: str | None = None
    quantization_level: str | None = None


class _Tag(BaseModel):
    name: str
    size: int = 0
    details: _TagDetails = _TagDetails()


class _TagsResponse(BaseModel):
    models: list[_Tag] = []


class _EmbedResponse(BaseModel):
    embeddings: list[list[float]]


class _ErrorBody(BaseModel):
    error: str = ""


class OllamaProvider(LLMProvider):
    """LLMProvider backed by a local Ollama server."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout_seconds: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        # `client` exists so tests can inject one with a mock transport.
        # The read timeout is the longest allowed silence between two chunks,
        # and it has to cover the model being loaded on the first request.
        self._client = client or httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout_seconds, connect=5.0),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def chat_stream(
        self,
        model: str,
        messages: Sequence[ChatMessage],
        options: GenerationOptions | None = None,
    ) -> AsyncGenerator[ChatChunk]:
        opts = options or GenerationOptions()
        payload = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "stream": True,
            "think": opts.think,
            "options": _to_ollama_options(opts),
        }
        try:
            async with self._client.stream("POST", "/api/chat", json=payload) as response:
                if response.status_code != httpx.codes.OK:
                    body = await response.aread()
                    raise _error_from_response(response.status_code, body, model)
                async for raw_line in response.aiter_lines():
                    if not raw_line.strip():
                        continue
                    line = _parse(_ChatLine, raw_line)
                    if line.error:
                        raise LLMProviderError(f"Ollama failed during generation: {line.error}")
                    message = line.message or _ChatLineMessage()
                    yield ChatChunk(
                        content=message.content,
                        thinking=message.thinking or "",
                        done=line.done,
                        stats=line.to_stats() if line.done else None,
                    )
        except httpx.HTTPError as exc:
            raise _error_from_transport(exc) from exc

    async def embed(self, model: str, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        body = await self._request("POST", "/api/embed", model, {"model": model, "input": [*texts]})
        embeddings = _parse(_EmbedResponse, body).embeddings
        if len(embeddings) != len(texts):
            raise LLMProviderError(
                f"Ollama returned {len(embeddings)} embeddings for {len(texts)} texts."
            )
        return embeddings

    async def list_models(self) -> list[ModelInfo]:
        body = await self._request("GET", "/api/tags", model=None, payload=None)
        return [
            ModelInfo(
                name=tag.name,
                size_bytes=tag.size,
                parameter_size=tag.details.parameter_size,
                quantization=tag.details.quantization_level,
            )
            for tag in _parse(_TagsResponse, body).models
        ]

    async def _request(
        self, method: str, url: str, model: str | None, payload: dict[str, object] | None
    ) -> str:
        try:
            response = await self._client.request(method, url, json=payload)
        except httpx.HTTPError as exc:
            raise _error_from_transport(exc) from exc
        if response.status_code != httpx.codes.OK:
            raise _error_from_response(response.status_code, response.content, model)
        return response.text


def _to_ollama_options(options: GenerationOptions) -> dict[str, float | int]:
    """Translate provider-neutral names to Ollama's (max_tokens is num_predict there)."""
    result: dict[str, float | int] = {
        "temperature": options.temperature,
        "num_ctx": options.num_ctx,
    }
    if options.max_tokens is not None:
        result["num_predict"] = options.max_tokens
    if options.seed is not None:
        result["seed"] = options.seed
    return result


def _parse[T: BaseModel](schema: type[T], raw: str) -> T:
    try:
        return schema.model_validate_json(raw)
    except ValidationError as exc:
        raise LLMProviderError(f"Unexpected response from Ollama: {raw[:200]!r}") from exc


def _error_from_response(status_code: int, body: bytes, model: str | None) -> LLMProviderError:
    try:
        detail = _ErrorBody.model_validate_json(body).error
    except ValidationError:
        detail = body.decode("utf-8", errors="replace")[:200]
    if status_code == httpx.codes.NOT_FOUND and model is not None:
        return ModelNotFoundError(f"Model '{model}' is not installed. Run: ollama pull {model}")
    return LLMProviderError(f"Ollama answered with status {status_code}: {detail}")


def _error_from_transport(exc: httpx.HTTPError) -> LLMProviderError:
    if isinstance(exc, httpx.ConnectError):
        return ProviderUnavailableError("Could not connect to Ollama. Is it running?")
    if isinstance(exc, httpx.TimeoutException):
        return LLMProviderError("Ollama took too long to answer (timeout).")
    return LLMProviderError(f"Network error while talking to Ollama: {exc}")
