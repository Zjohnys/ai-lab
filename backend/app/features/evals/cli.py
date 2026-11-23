"""Run the support triage evaluation against local models.

From the backend folder:

    uv run python -m app.features.evals.cli --model qwen3:8b
    uv run python -m app.features.evals.cli --model qwen3:8b --model qwen3:4b \
        --dataset support_triage --dataset support_triage_holdout

Every run is saved as JSON; a summary table is printed at the end.
"""

import argparse
import asyncio
import re
from pathlib import Path

import httpx

from app.core.config import REPO_ROOT, get_settings
from app.features.evals.runner import DEFAULT_EVAL_OPTIONS, run_eval
from app.features.evals.schemas import (
    EvalRun,
    ModelMemory,
    available_datasets,
    load_dataset,
    prompts_for,
)
from app.llm.ollama import OllamaProvider

DEFAULT_OUTPUT = REPO_ROOT / "modules" / "02-prompts" / "results"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--model", action="append", help="Model to test (repeatable).")
    parser.add_argument("--prompt", action="append", help="Prompt id to test (default: all).")
    parser.add_argument(
        "--dataset", action="append", help="Dataset name (repeatable, default: support_triage)."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Results folder.")
    return parser.parse_args()


def slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()


def model_memory(base_url: str, model: str) -> ModelMemory | None:
    """Ollama-specific: /api/ps reports the loaded model's size and how much is on the GPU."""
    try:
        data = httpx.get(f"{base_url}/api/ps", timeout=10).json()
    except (httpx.HTTPError, ValueError):
        return None
    for entry in data.get("models", []):
        if entry.get("name") == model and entry.get("size"):
            size, vram = entry["size"], entry.get("size_vram", 0)
            return ModelMemory(
                size_gb=round(size / 1024**3, 2),
                vram_gb=round(vram / 1024**3, 2),
                gpu_percent=round(100 * vram / size, 1),
            )
    return None


def print_table(runs: list[EvalRun]) -> None:
    header = (
        f"{'dataset':<24} {'model':<10} {'prompt':<15} {'acc':>7} {'strict':>6} "
        f"{'latency':>8} {'tok/s':>6} {'vram':>7}"
    )
    print("\n" + header + "\n" + "-" * len(header))
    for run in runs:
        s = run.summary
        vram = f"{run.memory.vram_gb:.1f} GB" if run.memory else "-"
        print(
            f"{run.dataset:<24} {run.model:<10} {run.prompt_id:<15} {s.correct:>3}/{s.total:<3} "
            f"{s.strict_json_rate:>6.0%} {s.mean_latency_seconds:>7.2f}s "
            f"{s.mean_tokens_per_second:>6.1f} {vram:>7}"
        )


async def main() -> None:
    args = parse_args()
    settings = get_settings()
    found = available_datasets()
    names = args.dataset or ["support_triage"]
    unknown_datasets = set(names) - set(found)
    if unknown_datasets:
        raise SystemExit(f"Unknown datasets: {sorted(unknown_datasets)}. Found: {sorted(found)}")
    models = args.model or [settings.chat_model]

    args.output.mkdir(parents=True, exist_ok=True)
    provider = OllamaProvider(settings.ollama_base_url, timeout_seconds=600)
    runs: list[EvalRun] = []
    try:
        # Model in the outer loop: each model is loaded once, not once per dataset.
        for model in models:
            for name in names:
                dataset = load_dataset(found[name])
                prompts = prompts_for(dataset)
                if args.prompt:
                    prompts = [prompt for prompt in prompts if prompt.id in args.prompt]
                for prompt in prompts:
                    print(f"Running {model} / {dataset.name} / {prompt.id}...")
                    run = await run_eval(provider, model, dataset, prompt, DEFAULT_EVAL_OPTIONS)
                    run.memory = model_memory(settings.ollama_base_url, model)
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
