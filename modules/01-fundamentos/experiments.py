"""Module 1 experiments: measure how a small local model behaves.

Runs against a real Ollama server through the project's own OllamaProvider.
From the repository root:

    uv run --directory backend python ../modules/01-fundamentos/experiments.py

Results are printed and saved to modules/01-fundamentos/results/experiments.json.
"""

import asyncio
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))

import httpx  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.llm import ChatMessage, GenerationOptions, GenerationStats, LLMProviderError  # noqa: E402
from app.llm.ollama import OllamaProvider  # noqa: E402

SETTINGS = get_settings()
MODEL = SETTINGS.chat_model
RESULTS_PATH = HERE / "results" / "experiments.json"


class Run:
    """The outcome of one generation: text, stats and wall-clock time, or an error."""

    def __init__(self) -> None:
        self.text = ""
        self.thinking = ""
        self.stats: GenerationStats | None = None
        self.wall_seconds = 0.0
        self.error: str | None = None


async def generate(
    provider: OllamaProvider, prompt: str, options: GenerationOptions, system: str | None = None
) -> Run:
    messages = [ChatMessage(role="system", content=system)] if system else []
    messages.append(ChatMessage(role="user", content=prompt))
    run = Run()
    started = time.perf_counter()
    try:
        async for chunk in provider.chat_stream(MODEL, messages, options):
            run.text += chunk.content
            run.thinking += chunk.thinking
            if chunk.done:
                run.stats = chunk.stats
    except LLMProviderError as exc:
        run.error = str(exc)
    run.wall_seconds = time.perf_counter() - started
    run.text = run.text.strip()
    return run


def gpu_memory_used_mb() -> int | None:
    try:
        output = subprocess.run(  # noqa: S603 - fixed command, no user input
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        ).stdout
        return int(output.strip().splitlines()[0])
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def loaded_model_memory() -> dict[str, float]:
    """What Ollama reports for the loaded model: total size and how much of it is on the GPU."""
    data = httpx.get(f"{SETTINGS.ollama_base_url}/api/ps", timeout=10).json()
    for model in data.get("models", []):
        if model.get("name") == MODEL:
            size, vram = model.get("size", 0), model.get("size_vram", 0)
            return {
                "size_gb": round(size / 1024**3, 2),
                "vram_gb": round(vram / 1024**3, 2),
                "gpu_percent": round(100 * vram / size, 1) if size else 0.0,
            }
    return {}


# --- Experiment 1: temperature -------------------------------------------------------------

TEMPERATURE_PROMPT = (
    "Sugira um nome criativo para uma cafeteria dentro de um datacenter. "
    "Responda apenas com o nome, sem explicação."
)


async def temperature_experiment(provider: OllamaProvider) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for temperature in (0.0, 0.7, 1.5):
        answers: list[str] = []
        for _ in range(5):
            options = GenerationOptions(temperature=temperature, max_tokens=24)
            run = await generate(provider, TEMPERATURE_PROMPT, options)
            answers.append(run.error or run.text)
        counts = Counter(answers)
        rows.append(
            {
                "temperature": temperature,
                "runs": len(answers),
                "distinct_answers": len(counts),
                "answers": answers,
            }
        )
        print(f"  temperature={temperature}: {len(counts)} distinct of {len(answers)} -> {answers}")
    return rows


# --- Experiment 2: thinking on vs off ------------------------------------------------------

# (question, expected answer). Numbers are compared with the last number in the reply.
REASONING_QUESTIONS: list[tuple[str, str]] = [
    (
        "Um servidor processa 120 chamados por hora. Quantos chamados ele processa em "
        "2 horas e 30 minutos? Responda apenas com o número.",
        "300",
    ),
    (
        "Tenho 3 caixas com 12 cabos de rede em cada uma. Entreguei 7 cabos. "
        "Quantos cabos restam? Responda apenas com o número.",
        "29",
    ),
    (
        "Se hoje é quarta-feira, que dia da semana será daqui a 10 dias? "
        "Responda apenas com o dia da semana.",
        "sábado",
    ),
    (
        "Um backup de 48 GB é copiado a 4 GB por minuto. Outro backup de 30 GB é copiado a "
        "5 GB por minuto. Quantos minutos a mais o primeiro leva? Responda apenas com o número.",
        "6",
    ),
    (
        "Qual é o próximo número da sequência 2, 6, 12, 20, 30? Responda apenas com o número.",
        "42",
    ),
    (
        "Quantas vezes a letra 'r' aparece na palavra 'servidor'? Responda apenas com o número.",
        "2",
    ),
]


def is_correct(answer: str, expected: str) -> bool:
    if expected.isdigit():
        numbers = re.findall(r"\d+", answer)
        return bool(numbers) and numbers[-1] == expected
    return expected in answer.lower()


async def thinking_experiment(provider: OllamaProvider) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for think in (False, True):
        correct = 0
        output_tokens = 0
        seconds = 0.0
        details: list[dict[str, object]] = []
        for question, expected in REASONING_QUESTIONS:
            run = await generate(
                provider, question, GenerationOptions(temperature=0.0, think=think, max_tokens=2048)
            )
            ok = run.error is None and is_correct(run.text, expected)
            correct += ok
            output_tokens += run.stats.output_tokens if run.stats else 0
            seconds += run.wall_seconds
            details.append(
                {"expected": expected, "answer": run.error or run.text[:120], "correct": ok}
            )
        rows.append(
            {
                "think": think,
                "correct": correct,
                "questions": len(REASONING_QUESTIONS),
                "output_tokens": output_tokens,
                "seconds": round(seconds, 1),
                "details": details,
            }
        )
        print(
            f"  think={think}: {correct}/{len(REASONING_QUESTIONS)} correct, "
            f"{output_tokens} tokens, {seconds:.1f}s"
        )
        for detail in details:
            print(f"     expected={detail['expected']!r} answer={detail['answer']!r}")
    return rows


# --- Experiment 3: prompt larger than the context window -----------------------------------

# A made-up marker the model can only know from the prompt. Not a credential.
MARKER = "AZUL-7731"
FACT = f"Anotação importante: o código secreto do projeto é {MARKER}."
QUESTION = "Qual é o código secreto do projeto? Responda apenas com o código."
OVERFLOW_NUM_CTX = 2048


def filler(sentences: int) -> str:
    return " ".join(
        f"Registro {i}: o servidor de arquivos foi verificado e está operando normalmente."
        for i in range(1, sentences + 1)
    )


async def overflow_experiment(provider: OllamaProvider) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    options = GenerationOptions(temperature=0.0, num_ctx=OVERFLOW_NUM_CTX, max_tokens=40)
    for sentences in (20, 80, 200, 400):
        for position in ("start", "end"):
            body = filler(sentences)
            document = f"{FACT}\n\n{body}" if position == "start" else f"{body}\n\n{FACT}"
            run = await generate(provider, f"{document}\n\n{QUESTION}", options)
            row = {
                "filler_sentences": sentences,
                "prompt_characters": len(document) + len(QUESTION),
                "fact_position": position,
                "num_ctx": OVERFLOW_NUM_CTX,
                "prompt_tokens_reported": run.stats.prompt_tokens if run.stats else None,
                "found_secret": run.error is None and MARKER in run.text,
                "answer": run.error or run.text[:120],
            }
            rows.append(row)
            print(
                f"  sentences={sentences} fact_at={position}: "
                f"prompt_tokens={row['prompt_tokens_reported']} "
                f"found={row['found_secret']} answer={row['answer']!r}"
            )
    return rows


# --- Experiment 4: context window size, speed and memory -----------------------------------

SPEED_PROMPT = "Explique em um parágrafo o que é um firewall."


async def context_size_experiment(provider: OllamaProvider) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    # 8192 is last so the model is left loaded with the project default.
    for num_ctx in (2048, 4096, 16384, 8192):
        options = GenerationOptions(temperature=0.0, num_ctx=num_ctx, max_tokens=120)
        first = await generate(provider, SPEED_PROMPT, options)  # reloads the model
        second = await generate(provider, SPEED_PROMPT, options)  # model already loaded
        row: dict[str, object] = {
            "num_ctx": num_ctx,
            "load_seconds": round(first.stats.load_seconds, 1) if first.stats else None,
            "tokens_per_second": round(second.stats.tokens_per_second, 1) if second.stats else None,
            "gpu_memory_used_mb": gpu_memory_used_mb(),
            "error": first.error or second.error,
            **loaded_model_memory(),
        }
        rows.append(row)
        print(f"  {row}")
    return rows


async def main() -> None:
    provider = OllamaProvider(SETTINGS.ollama_base_url, timeout_seconds=600)
    results: dict[str, object] = {
        "model": MODEL,
        "date": time.strftime("%Y-%m-%d"),
        "gpu_memory_used_mb_before": gpu_memory_used_mb(),
    }
    try:
        print(f"Model: {MODEL}\n\n1. Temperature")
        results["temperature"] = await temperature_experiment(provider)
        print("\n2. Thinking on vs off")
        results["thinking"] = await thinking_experiment(provider)
        print("\n3. Prompt larger than the context window")
        results["overflow"] = await overflow_experiment(provider)
        print("\n4. Context window size")
        results["context_size"] = await context_size_experiment(provider)
    finally:
        await provider.aclose()

    RESULTS_PATH.parent.mkdir(exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"\nSaved to {RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
