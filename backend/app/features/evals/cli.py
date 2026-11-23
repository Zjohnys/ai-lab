"""Run the support triage evaluation against local models.

From the backend folder:

    uv run python -m app.features.evals.cli --model qwen3:8b
    uv run python -m app.features.evals.cli --model qwen3:8b --model qwen3:4b --prompt v3_few_shot

Every run is saved as JSON; a summary table is printed at the end.
"""

import argparse
import asyncio
import re
from pathlib import Path

from app.core.config import REPO_ROOT, get_settings
from app.features.evals.runner import DEFAULT_EVAL_OPTIONS, run_eval
from app.features.evals.schemas import DATA_DIR, EvalRun, load_dataset, load_prompts
from app.llm.ollama import OllamaProvider

DEFAULT_OUTPUT = REPO_ROOT / "modules" / "02-prompts" / "results"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", action="append", help="Model to test (repeatable).")
    parser.add_argument("--prompt", action="append", help="Prompt id to test (default: all).")
    parser.add_argument("--dataset", default="support_triage", help="Dataset name in data/.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Results folder.")
    return parser.parse_args()


def slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()


def print_table(runs: list[EvalRun]) -> None:
    header = (
        f"{'model':<14} {'prompt':<16} {'accuracy':>8} {'strict':>7} {'json':>6} "
        f"{'latency':>8} {'tok/s':>6}"
    )
    print("\n" + header + "\n" + "-" * len(header))
    for run in runs:
        s = run.summary
        print(
            f"{run.model:<14} {run.prompt_id:<16} {s.correct:>3}/{s.total:<4} "
            f"{s.strict_json_rate:>7.0%} {s.json_found_rate:>6.0%} "
            f"{s.mean_latency_seconds:>7.2f}s {s.mean_tokens_per_second:>6.1f}"
        )


async def main() -> None:
    args = parse_args()
    settings = get_settings()
    dataset = load_dataset(DATA_DIR / f"{args.dataset}.json")
    prompts = load_prompts(DATA_DIR / f"{args.dataset}_prompts.toml")
    if args.prompt:
        unknown = set(args.prompt) - {prompt.id for prompt in prompts}
        if unknown:
            raise SystemExit(f"Unknown prompt ids: {sorted(unknown)}")
        prompts = [prompt for prompt in prompts if prompt.id in args.prompt]
    models = args.model or [settings.chat_model]

    args.output.mkdir(parents=True, exist_ok=True)
    provider = OllamaProvider(settings.ollama_base_url, timeout_seconds=600)
    runs: list[EvalRun] = []
    try:
        for model in models:
            for prompt in prompts:
                print(f"Running {model} / {prompt.id} on {len(dataset.cases)} cases...")
                run = await run_eval(provider, model, dataset, prompt, DEFAULT_EVAL_OPTIONS)
                runs.append(run)
                path = args.output / f"{dataset.name}__{slug(model)}__{prompt.id}.json"
                path.write_text(
                    run.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n"
                )
                for result in run.results:
                    if not result.correct:
                        print(
                            f"   wrong: {result.case_id} expected={result.expected} "
                            f"got={result.predicted} raw={result.raw_output[:80]!r}"
                        )
    finally:
        await provider.aclose()
    print_table(runs)


if __name__ == "__main__":
    asyncio.run(main())
