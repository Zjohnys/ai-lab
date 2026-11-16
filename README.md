# AI Lab

[![CI](https://github.com/Zjohnys/ai-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/Zjohnys/ai-lab/actions/workflows/ci.yml)

A personal AI engineering school that runs entirely on local, open-source models. No cloud APIs, no API keys, no usage cost.

Each module teaches one topic and ends with a working project, tests, and measured results.

> Status: Module 0 (environment) complete. First measurement: `qwen3:8b` at 36 tokens/s on an RTX 3050 8 GB. The backend and frontend are minimal skeletons.

## Why local only

- Every number in this repository (accuracy, latency, tokens per second) is reproducible on a consumer GPU.
- Small models fail more often than large hosted ones. Each module README records what worked and what did not.

## Reference hardware

| Component | Value |
| --- | --- |
| CPU | AMD Ryzen 7 5700X (8 cores, 16 threads) |
| RAM | 16 GB DDR4 |
| GPU | NVIDIA RTX 3050, 8 GB VRAM |
| OS | Windows 11 |

## Default models

| Role | Model | Approx. size |
| --- | --- | --- |
| Chat | `qwen3:8b` (Q4_K_M) | 5.2 GB |
| Code | `qwen2.5-coder:7b` (Q4_K_M) | 4.7 GB |
| Embeddings | `bge-m3` | 1.2 GB |

## Stack

- Backend: Python 3.13, FastAPI, Pydantic, SQLite + sqlite-vec, pytest
- Frontend: React, TypeScript, Vite, Tailwind, Vitest
- Inference: Ollama, behind an `LLMProvider` interface

## Modules

| # | Topic | Portfolio project |
| --- | --- | --- |
| [0](modules/00-ambiente/README.md) | Professional environment with AI | |
| 1 | Local LLM fundamentals | |
| 2 | Measured prompt engineering | Model benchmark (start) |
| 3 | Reusable prompts and commands | |
| 4 | Structured output | Local code reviewer |
| 5 | Embeddings and local RAG | ITIL helpdesk (triage + RAG) |
| 6 | Agents and tool use | Argus local agent |
| 7 | MCP | Codebase explainer |
| 8 | Local production | |
| 9 | Advanced: quantization, LoRA, in-browser AI | Model benchmark (final) |

Study order: 0, 1, 2, 4, 5, 6, 7, 8, 3, 9. Evaluation, structured output, RAG and agents come first; reusable commands and the advanced topics close the track.

## Setup

Requirements: [Ollama](https://ollama.com), [uv](https://docs.astral.sh/uv/), Node.js 22+.

```powershell
Copy-Item .env.example .env
ollama pull qwen3:8b
```

Backend (http://localhost:8000, API docs at `/docs`):

```powershell
cd backend
uv run uvicorn app.main:app --reload
```

Frontend (http://localhost:5173), in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

## Tests

```powershell
cd backend; uv run pytest
cd frontend; npm test
```

Tests never call a real model. Tests that need Ollama are marked `live` and are skipped by default.
