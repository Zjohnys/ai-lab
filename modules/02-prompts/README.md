# Module 2 - Measured prompt engineering

> In progress. This file holds the measurements so far; the lesson, the comparison screen and the final write-up come in later batches.

## Setup

- **Task**: classify an IT support message into one of five categories (`acesso`, `hardware`, `rede`, `software`, `seguranca`) and answer with `{"category": "..."}`.
- **Dev set** (`support_triage`, 15 cases): written together with the prompts. The tie-break rules in v2 and v3 were written knowing the answers to its hard cases.
- **Holdout set** (`support_triage_holdout`, 10 cases): written after the prompts. The prompts were not changed after seeing these results.
- **Prompts**: `v1_basic` (categories and format only), `v2_definitions` (role, definitions, tie-break rules, strict format), `v3_few_shot` (v2 plus five examples not taken from either set).
- **Options**: temperature 0, seed 42. One run per configuration, measured on 2026-11-23 on an RTX 3050 8 GB with Ollama 0.40.16.

Run it:

```powershell
cd backend
uv run python -m app.features.evals.cli --model qwen3:8b --dataset support_triage --dataset support_triage_holdout
uv run python -m app.features.evals.cli --model qwen3:4b --dataset support_triage --dataset support_triage_holdout --think --max-tokens 2048
```

Raw results, one file per run: [`results/`](results/).

## Results

### qwen3:8b, thinking off (64-token limit)

| Prompt | Dev (15) | Holdout (10) | Strict JSON | Mean latency (holdout) |
| --- | --- | --- | --- | --- |
| v1_basic | 12 | 8 | 100% | 0.35 s |
| v2_definitions | 15 | 8 | 100% | 0.35 s |
| v3_few_shot | 15 | 9 | 100% | 0.37 s |

5.8 GB of memory, 100% on the GPU, about 31 tokens/s.

### qwen3:4b, thinking on (2,048-token limit)

| Prompt | Dev (15) | Holdout (10) | Strict JSON (holdout) | Mean latency (holdout) |
| --- | --- | --- | --- | --- |
| v1_basic | 14 | 9 | 100% | 15.9 s |
| v2_definitions | 15 | 8 | 90% | 10.6 s |
| v3_few_shot | 15 | 9 | 100% | 10.8 s |

3.6 GB of memory, 100% on the GPU, about 61 tokens/s.

### qwen3:8b, thinking on, v2 only (2,048-token limit)

| Prompt | Dev (15) | Holdout (10) | Mean latency (holdout) |
| --- | --- | --- | --- |
| v2_definitions | 15 | **10** | 7.8 s |

## What the numbers show

- **The dev set overstated the prompts.** v2 went from 15/15 on the cases it was written for to 8/10 on new cases with `qwen3:8b`. The 15/15 measured how well the rules matched cases their author already knew.
- **v1 to v2 helped only on the dev set.** On the holdout both score 8/10 with `qwen3:8b`. The few-shot examples in v3 added one case.
- **Both 8b errors on the holdout are the same two cases for v1 and v2**: the two-factor code going to an old phone (labelled `seguranca`, expected `acesso`) and the printer missing from the network (labelled `hardware`, expected `rede`).
- **Thinking fixed them, at a cost.** `qwen3:8b` with thinking got 10/10 on the holdout, at 7.8 s per message instead of 0.35 s: 22 times slower.
- **The 4b model is faster per token but slower per answer.** It generates about twice as many tokens per second as the 8b, but it must think, so each answer takes 5 to 16 s.

## What failed

- **First qwen3:4b run: 0 of 25 on every prompt.** The `qwen3:4b` tag pulled from Ollama is a thinking-only variant (`ollama show` lists thinking level `true` only). With `think: false`, Ollama put the reasoning inside the answer text, and the 64-token limit cut it before any JSON. Those runs are kept in `results/` without the `__think` suffix. They measure a configuration mistake, not the model.
- **Running out of tokens while thinking.** Two `qwen3:4b` answers spent all 2,048 tokens reasoning and returned an empty answer, which counts as wrong.

## Limitations

- 15 and 10 cases. One case is 10 percentage points on the holdout: differences of one or two cases are noise.
- One run per configuration. With temperature 0 and a fixed seed, reruns should be close, but this was not checked.
- The same person wrote the prompts, both datasets and their gold labels. Someone else might label the ambiguous cases differently.
- `qwen3:8b` speed was about 31 tokens/s in this session against 36 to 39 in Module 1. Not investigated.
- Latency includes the model load on the first case of each run.
