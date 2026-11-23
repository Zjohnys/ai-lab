import time
from datetime import UTC, datetime

from app.features.evals.schemas import (
    CaseResult,
    EvalCase,
    EvalDataset,
    EvalRun,
    EvalSummary,
    LabelScore,
    PromptVersion,
)
from app.features.evals.scoring import parse_output
from app.llm.provider import (
    LLMProvider,
    LLMProviderError,
    ModelNotFoundError,
    ProviderUnavailableError,
)
from app.llm.types import GenerationOptions

# Classification has one right answer: no randomness, no thinking, short output.
DEFAULT_EVAL_OPTIONS = GenerationOptions(temperature=0.0, think=False, max_tokens=64, seed=42)


async def run_case(
    provider: LLMProvider,
    model: str,
    prompt: PromptVersion,
    case: EvalCase,
    labels: list[str],
    options: GenerationOptions,
) -> CaseResult:
    text = ""
    output_tokens = 0
    tokens_per_second = 0.0
    error: str | None = None
    started = time.perf_counter()
    try:
        async for chunk in provider.chat_stream(
            model, prompt.render(case.message, labels), options
        ):
            text += chunk.content
            if chunk.done and chunk.stats:
                output_tokens = chunk.stats.output_tokens
                tokens_per_second = chunk.stats.tokens_per_second
    except (ProviderUnavailableError, ModelNotFoundError):
        raise  # Every other case would fail the same way: stop the run.
    except LLMProviderError as exc:
        error = str(exc)
    latency = time.perf_counter() - started

    parsed = parse_output(text, labels)
    return CaseResult(
        case_id=case.id,
        expected=case.expected,
        predicted=parsed.label,
        correct=error is None and parsed.label == case.expected,
        strict_json=parsed.strict_json,
        json_found=parsed.json_found,
        label_valid=parsed.label_valid,
        raw_output=text,
        error=error,
        latency_seconds=latency,
        output_tokens=output_tokens,
        tokens_per_second=tokens_per_second,
    )


def summarize(results: list[CaseResult], labels: list[str]) -> EvalSummary:
    total = len(results)

    def rate(count: int) -> float:
        return count / total if total else 0.0

    latencies = [result.latency_seconds for result in results]
    speeds = [result.tokens_per_second for result in results if result.tokens_per_second > 0]
    per_label = {
        label: LabelScore(
            total=sum(result.expected == label for result in results),
            correct=sum(result.expected == label and result.correct for result in results),
        )
        for label in labels
    }
    correct = sum(result.correct for result in results)
    return EvalSummary(
        total=total,
        correct=correct,
        accuracy=rate(correct),
        strict_json_rate=rate(sum(result.strict_json for result in results)),
        json_found_rate=rate(sum(result.json_found for result in results)),
        valid_label_rate=rate(sum(result.label_valid for result in results)),
        errors=sum(result.error is not None for result in results),
        mean_latency_seconds=sum(latencies) / total if total else 0.0,
        max_latency_seconds=max(latencies, default=0.0),
        mean_tokens_per_second=sum(speeds) / len(speeds) if speeds else 0.0,
        per_label=per_label,
    )


async def run_eval(
    provider: LLMProvider,
    model: str,
    dataset: EvalDataset,
    prompt: PromptVersion,
    options: GenerationOptions = DEFAULT_EVAL_OPTIONS,
) -> EvalRun:
    """Run every case in order, one at a time (one GPU, one model loaded)."""
    started_at = datetime.now(UTC).isoformat(timespec="seconds")
    results = [
        await run_case(provider, model, prompt, case, dataset.labels, options)
        for case in dataset.cases
    ]
    return EvalRun(
        dataset=dataset.name,
        prompt_id=prompt.id,
        model=model,
        options=options,
        started_at=started_at,
        summary=summarize(results, dataset.labels),
        results=results,
    )
