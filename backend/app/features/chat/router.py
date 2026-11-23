import json
from collections.abc import AsyncGenerator, Iterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.features.chat.schemas import ChatRequest, ModelsResponse
from app.llm.deps import ProviderDep, SettingsDep
from app.llm.http_errors import to_http_error
from app.llm.provider import LLMProviderError
from app.llm.types import ChatChunk, GenerationOptions, GenerationStats

router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/models")
async def list_models(provider: ProviderDep, settings: SettingsDep) -> ModelsResponse:
    try:
        models = await provider.list_models()
    except LLMProviderError as exc:
        raise to_http_error(exc) from exc
    return ModelsResponse(models=models, default_chat_model=settings.chat_model)


@router.post(
    "/chat",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": "Server-Sent Events: `token` events, then one `done` or `error`.",
        },
        404: {"description": "The model is not installed."},
        502: {"description": "The provider failed before producing any output."},
        503: {"description": "The provider is not running."},
    },
)
async def chat(
    request: ChatRequest, provider: ProviderDep, settings: SettingsDep
) -> StreamingResponse:
    model = request.model or settings.chat_model
    options = request.options or GenerationOptions(
        temperature=settings.temperature, num_ctx=settings.num_ctx
    )
    stream = provider.chat_stream(model, request.messages, options)

    # Wait for the first chunk before answering. Once a streaming response starts,
    # the status code is already sent as 200 and can no longer say "404" or "503".
    try:
        first = await anext(stream)
    except StopAsyncIteration:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "The model returned an empty stream."
        ) from None
    except LLMProviderError as exc:
        raise to_http_error(exc) from exc

    return StreamingResponse(
        _event_stream(first, stream),
        media_type="text/event-stream",
        # Ask proxies not to cache or buffer, otherwise tokens arrive all at once.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _event_stream(first: ChatChunk, stream: AsyncGenerator[ChatChunk]) -> AsyncGenerator[str]:
    try:
        for event in _chunk_events(first):
            yield event
        async for chunk in stream:
            for event in _chunk_events(chunk):
                yield event
    except LLMProviderError as exc:
        # Too late for an HTTP error status: report the failure inside the stream.
        yield _sse("error", {"message": str(exc)})
    finally:
        # Runs when the answer ends and also when the browser disconnects.
        # Closing the generator closes the connection to Ollama, which stops generating.
        await stream.aclose()


def _chunk_events(chunk: ChatChunk) -> Iterator[str]:
    if chunk.content or chunk.thinking:
        yield _sse("token", {"content": chunk.content, "thinking": chunk.thinking})
    if chunk.done:
        yield _sse("done", (chunk.stats or GenerationStats()).model_dump())


def _sse(event: str, data: dict[str, object]) -> str:
    """Format one Server-Sent Event. json.dumps never emits a raw newline, so one data line."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
