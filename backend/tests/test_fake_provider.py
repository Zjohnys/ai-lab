import pytest

from app.llm import ChatMessage, GenerationOptions, ProviderUnavailableError
from app.llm.fake import FakeProvider

pytestmark = pytest.mark.anyio

QUESTION = [ChatMessage(role="user", content="O que é um token?")]


async def test_stream_pieces_join_back_into_the_reply() -> None:
    provider = FakeProvider(reply="Um token é um pedaço de texto.")

    chunks = [chunk async for chunk in provider.chat_stream("fake-model", QUESTION)]

    assert "".join(chunk.content for chunk in chunks) == "Um token é um pedaço de texto."


async def test_only_the_last_chunk_is_done_and_has_stats() -> None:
    provider = FakeProvider(reply="um dois três")

    chunks = [chunk async for chunk in provider.chat_stream("fake-model", QUESTION)]

    assert [chunk.done for chunk in chunks] == [False, False, False, True]
    assert all(chunk.stats is None for chunk in chunks[:-1])
    stats = chunks[-1].stats
    assert stats is not None
    assert stats.output_tokens == 3
    assert stats.tokens_per_second == pytest.approx(50.0)


async def test_records_each_call_for_assertions() -> None:
    provider = FakeProvider()
    options = GenerationOptions(temperature=0.9)

    async for _ in provider.chat_stream("fake-model", QUESTION, options):
        pass

    assert len(provider.calls) == 1
    assert provider.calls[0].model == "fake-model"
    assert provider.calls[0].messages == tuple(QUESTION)
    assert provider.calls[0].options.temperature == 0.9


async def test_empty_reply_still_ends_with_a_done_chunk() -> None:
    provider = FakeProvider(reply="")

    chunks = [chunk async for chunk in provider.chat_stream("fake-model", QUESTION)]

    assert len(chunks) == 1
    assert chunks[0].done is True


async def test_embeddings_are_deterministic_and_have_the_requested_size() -> None:
    provider = FakeProvider(embedding_dim=16)

    first = await provider.embed("fake-embed", ["reset de senha", "impressora offline"])
    second = await provider.embed("fake-embed", ["reset de senha"])

    assert [len(vector) for vector in first] == [16, 16]
    assert first[0] == second[0]
    assert first[0] != first[1]
    assert all(-1.0 <= value <= 1.0 for value in first[0])


async def test_lists_the_configured_models() -> None:
    provider = FakeProvider(models=["a", "b"])

    assert [model.name for model in await provider.list_models()] == ["a", "b"]


async def test_can_simulate_a_provider_failure() -> None:
    provider = FakeProvider(fail_with=ProviderUnavailableError("down"))

    with pytest.raises(ProviderUnavailableError):
        async for _ in provider.chat_stream("fake-model", QUESTION):
            pass
    with pytest.raises(ProviderUnavailableError):
        await provider.embed("fake-embed", ["x"])
