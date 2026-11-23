from collections.abc import AsyncGenerator, Sequence

import pytest

from app.features.evals.runner import DEFAULT_EVAL_OPTIONS, run_eval, summarize
from app.features.evals.schemas import CaseResult, EvalDataset, PromptVersion
from app.llm import (
    ChatChunk,
    ChatMessage,
    GenerationOptions,
    GenerationStats,
    LLMProviderError,
    ModelNotFoundError,
    ProviderUnavailableError,
)
from app.llm.fake import FakeProvider

pytestmark = pytest.mark.anyio

DATASET = EvalDataset.model_validate(
    {
        "name": "tiny",
        "labels": ["rede", "hardware"],
        "cases": [
            {"id": "r1", "message": "wifi caiu", "expected": "rede"},
            {"id": "r2", "message": "vpn não conecta", "expected": "rede"},
            {"id": "h1", "message": "teclado quebrou", "expected": "hardware"},
            {"id": "h2", "message": "monitor apagou", "expected": "hardware"},
        ],
    }
)
PROMPT = PromptVersion(id="p1", system="Categorias: {labels}", user_template="Mensagem: {message}")


class ScriptedProvider(FakeProvider):
    """Answers each message with a scripted reply, keyed by the ticket text."""

    def __init__(self, replies: dict[str, str], fail_on: str | None = None) -> None:
        super().__init__()
        self.replies = replies
        self.fail_on = fail_on
        self.seen: list[tuple[list[ChatMessage], GenerationOptions]] = []

    async def chat_stream(
        self,
        model: str,
        messages: Sequence[ChatMessage],
        options: GenerationOptions | None = None,
    ) -> AsyncGenerator[ChatChunk]:
        self.seen.append((list(messages), options or GenerationOptions()))
        ticket = messages[-1].content.removeprefix("Mensagem: ")
        if ticket == self.fail_on:
            raise LLMProviderError("CUDA out of memory")
        yield ChatChunk(content=self.replies[ticket])
        yield ChatChunk(done=True, stats=GenerationStats(output_tokens=8, generation_seconds=0.2))


REPLIES = {
    "wifi caiu": '{"category": "rede"}',
    "vpn não conecta": '```json\n{"category": "rede"}\n```',  # right, but not strict
    "teclado quebrou": '{"category": "rede"}',  # wrong
    "monitor apagou": "hardware",  # right word, no JSON
}


async def test_run_scores_every_case_and_summarizes() -> None:
    run = await run_eval(ScriptedProvider(REPLIES), "fake-model", DATASET, PROMPT)

    by_id = {result.case_id: result for result in run.results}
    assert [result.correct for result in run.results] == [True, True, False, False]
    assert by_id["r2"].strict_json is False and by_id["r2"].json_found is True
    assert by_id["h2"].predicted is None
    s = run.summary
    assert (s.total, s.correct, s.accuracy) == (4, 2, 0.5)
    assert s.strict_json_rate == 0.5
    assert s.json_found_rate == 0.75
    assert s.valid_label_rate == 0.75
    assert s.per_label["rede"].correct == 2
    assert s.per_label["hardware"].correct == 0
    assert s.mean_tokens_per_second == pytest.approx(40.0)
    assert run.model == "fake-model"
    assert run.prompt_id == "p1"


async def test_run_sends_the_rendered_prompt_with_deterministic_options() -> None:
    provider = ScriptedProvider(REPLIES)

    await run_eval(provider, "fake-model", DATASET, PROMPT)

    messages, options = provider.seen[0]
    assert [message.role for message in messages] == ["system", "user"]
    assert messages[0].content == "Categorias: rede, hardware"
    assert messages[1].content == "Mensagem: wifi caiu"
    assert options == DEFAULT_EVAL_OPTIONS
    assert options.temperature == 0.0
    assert options.think is False


async def test_a_failed_case_is_recorded_as_wrong_and_the_run_continues() -> None:
    provider = ScriptedProvider(REPLIES, fail_on="wifi caiu")

    run = await run_eval(provider, "fake-model", DATASET, PROMPT)

    first = run.results[0]
    assert first.correct is False
    assert first.error == "CUDA out of memory"
    assert run.summary.errors == 1
    assert len(run.results) == 4


@pytest.mark.parametrize(
    "error",
    [ProviderUnavailableError("Ollama is not running"), ModelNotFoundError("not installed")],
)
async def test_failures_that_would_repeat_on_every_case_stop_the_whole_run(
    error: LLMProviderError,
) -> None:
    provider = FakeProvider(fail_with=error)

    with pytest.raises(type(error)):
        await run_eval(provider, "fake-model", DATASET, PROMPT)
    assert len(provider.calls) == 1


def test_summary_of_no_results_is_all_zero() -> None:
    summary = summarize([], ["a"])

    assert summary.total == 0
    assert summary.accuracy == 0.0
    assert summary.mean_latency_seconds == 0.0


def test_summary_ignores_cases_without_speed_when_averaging_tokens_per_second() -> None:
    def result(tps: float) -> CaseResult:
        return CaseResult(
            case_id="x",
            expected="a",
            predicted="a",
            correct=True,
            strict_json=True,
            json_found=True,
            label_valid=True,
            raw_output="",
            latency_seconds=1.0,
            tokens_per_second=tps,
        )

    assert summarize([result(30.0), result(0.0)], ["a"]).mean_tokens_per_second == 30.0
