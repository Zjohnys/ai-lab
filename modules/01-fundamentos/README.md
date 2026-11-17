# Module 1 - Local LLM fundamentals

## Problem

Tokens, context window, temperature, quantization, thinking and streaming are usually explained in the abstract. This module builds a working chat on a local model and measures each of them on real hardware, so every claim in the [lesson](lesson.md) has a number behind it.

## What was built

- **`LLMProvider` layer** (`backend/app/llm/`): one interface for every model call, with `OllamaProvider` (streaming chat, embeddings, model list) and `FakeProvider` (deterministic, for tests and CI). Every Ollama response is validated with Pydantic.
- **Chat API** (`backend/app/features/chat/`): `POST /api/chat` streams Server-Sent Events (`token`, `done`, `error`); `GET /api/models` lists installed models.
- **Chat page** (`frontend/src/features/chat/`): streamed answers, stop button, model selector, system prompt, temperature, context size and thinking, with tokens/s, context used and load time under each answer.
- **Experiments** ([`experiments.py`](experiments.py)): four measurements against the real model, results in [`results/experiments.json`](results/experiments.json).
- **Lesson material** (Portuguese): [`lesson.md`](lesson.md) and [`exercises.md`](exercises.md).

## Architecture

```
Browser: ChatPage -> useChat -> streamChat -> readSse
   |  POST /api/chat  (Server-Sent Events back)
   v
FastAPI: chat router -> LLMProvider (injected; FakeProvider in tests)
   |  POST /api/chat  (NDJSON back)
   v
Ollama -> qwen3:8b on the GPU
```

Errors before the first token become HTTP status codes (`404` model not installed, `503` Ollama not running, `502` other). Errors after it become an `error` event, because the `200` status has already been sent.

## How to run

```powershell
cd backend; uv run uvicorn app.main:app --reload
```

```powershell
cd frontend; npm run dev
```

Open http://localhost:5173. In VS Code, `Ctrl+Shift+B` starts both.

Experiments (several minutes of GPU time; Ollama must be running):

```powershell
uv run --directory backend python ../modules/01-fundamentos/experiments.py
```

Tests:

```powershell
cd backend; uv run pytest          # 50 tests, no model
cd backend; uv run pytest -m live  # 3 tests against the real model
cd frontend; npm test              # 28 tests
```

## Measured results

Model `qwen3:8b` (Q4_K_M) on Ollama 0.40.16, RTX 3050 8 GB, measured on 2026-11-16. Each configuration was run once unless stated; there is no variance estimate.

### 1. Temperature: how often the answer changes

Prompt: suggest a name for a coffee shop inside a datacenter, answer with the name only. Five runs per temperature.

| Temperature | Distinct answers out of 5 |
| --- | --- |
| 0.0 | 1 |
| 0.7 | 3 |
| 1.5 | 4 |

At 0.0 all five runs returned the same name.

### 2. Thinking on vs off

Six short reasoning questions (arithmetic, dates, a sequence, letter counting), temperature 0, each with one expected answer.

| Thinking | Correct | Output tokens (total) | Time (total) |
| --- | --- | --- | --- |
| Off | 4 of 6 | 121 | 4.4 s |
| On | 6 of 6 | 2,346 | 79.2 s |

With thinking off, the model got two arithmetic questions wrong (360 instead of 300, 39 instead of 29). In a third question it ignored "answer with the number only" and wrote a worked explanation; the grader scored it correct because the last number was right (see Limitations). With thinking on it answered all six, at 19 times the tokens and 18 times the time.

### 3. Prompt larger than the context window

A made-up code placed either at the start or at the end of a filler text, with `num_ctx=2048`, then the question "what is the code?".

| Filler sentences | Prompt tokens reported | Code at the start | Code at the end |
| --- | --- | --- | --- |
| 20 | 444 | found | found |
| 80 | 1,644 | found | found |
| 200 | 1,026 | **lost** (answered "200") | found |
| 400 | 1,026 | **lost** (answered "400") | found |

When the prompt did not fit, Ollama kept only the last 1,026 tokens and returned no error. The model then answered with a number from the filler. Information at the end of the prompt survived; information at the start was silently dropped.

### 4. Context window size: speed and memory

Same prompt, second run of each size (model already loaded).

| `num_ctx` | Model size in memory | On GPU | Tokens/s | GPU memory in use |
| --- | --- | --- | --- | --- |
| 2,048 | 4.92 GB | 100% | 39.2 | 6,150 MB |
| 4,096 | 5.20 GB | 100% | 37.7 | 6,426 MB |
| 8,192 | 5.77 GB | 100% | 38.2 | 6,763 MB |
| 16,384 | 7.30 GB | 82.6% | 20.4 | 7,031 MB |

Up to 8,192 the model fits entirely on the GPU and speed barely changes. At 16,384 it no longer fits: 17% of it moves to the CPU and generation drops to about half the speed. Changing `num_ctx` reloaded the model, costing 6.2 to 7.5 s.

## What worked

- Streaming end to end, at about 36 to 39 tokens/s, with stop, errors and stats visible in the UI.
- The provider abstraction: 78 tests (50 backend, 28 frontend) run without a model, in seconds, in CI.
- Every behaviour described in the lesson was reproduced with a number on this machine.

## What failed or surprised

- **Silent truncation**: an oversized prompt lost its beginning with no error or warning, and the model answered confidently with wrong information. Anything that builds long prompts (chat history, RAG in Module 5) must count tokens itself.
- **Truncation size**: Ollama kept 1,026 tokens, about half of the 2,048-token window, not the full window. The reason was not investigated.
- **Arithmetic without thinking**: 2 of 6 simple word problems wrong. Thinking fixed them at a large cost in time.
- **Format instructions**: one answer ignored "answer with the number only".

## Limitations

- One run per configuration (five for temperature). No variance, no confidence intervals.
- Six reasoning questions are far too few to compare thinking modes in general; this only shows the size of the cost.
- The reasoning grader takes the last number in the answer. For the answer that ignored the format instruction, only its first 120 characters were saved, so the grading of that question was not checked by hand.
- In the context size experiment, the 2,048 run reported 0.0 s of load time although the model was reloaded with a smaller context. Not investigated.
- GPU memory figures include the Windows desktop (about 1.4 GB when idle).
- The chat does not trim history when it approaches the window; this experiment shows why it should.
