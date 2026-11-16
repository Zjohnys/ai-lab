# Module 0 - Professional environment with AI

## Problem

Before building anything with local models, the environment has to answer three questions reliably: which models fit on this machine, how fast do they run, and can every change be tested without a model. This module sets that up.

## What was built

- **Repository conventions**: `CLAUDE.md` with project rules for the AI assistant, `.gitignore`, `.gitattributes`, `.editorconfig`, `.env.example`.
- **Backend skeleton**: FastAPI with `GET /api/health`, settings from `.env`, pytest and Ruff.
- **Frontend skeleton**: React + TypeScript + Tailwind page that reports backend health, with Vitest.
- **Editor setup**: `.vscode/` with settings, tasks, debugger launch configurations and recommended extensions; `backend/requests.http` for the REST Client extension.
- **Hardware diagnosis**: `scripts/hw-diagnose.ps1`.
- **CI**: GitHub Actions running lint, tests and build for both sides, with no model involved.
- **Lesson material** (Portuguese): [`lesson.md`](lesson.md) and [`exercises.md`](exercises.md).

## Architecture

```
Browser (Vite dev server, :5173)
   |  /api/*  (dev proxy)
   v
FastAPI (:8000)
   |  HTTP (from Module 1 on, through the LLMProvider interface)
   v
Ollama (:11434) -> qwen3:8b on the GPU
```

In this module the backend does not call Ollama yet; the model was measured directly through the Ollama API.

## How to run

```powershell
powershell -ExecutionPolicy Bypass -File scripts/hw-diagnose.ps1
ollama pull qwen3:8b
cd backend; uv run uvicorn app.main:app --reload
```

In a second terminal:

```powershell
cd frontend; npm install; npm run dev
```

In VS Code, `Ctrl+Shift+B` starts both servers and `F5` starts the backend under the debugger.

Tests:

```powershell
cd backend; uv run pytest
cd frontend; npm test
```

## Measured results

Model `qwen3:8b` (Q4_K_M, 5.2 GB on disk) on Ollama 0.40.16, RTX 3050 8 GB, `num_ctx=8192`, `temperature=0.2`.
Prompt (Portuguese): "Explique em 3 frases o que é um token em um modelo de linguagem."
Single run per row, measured on 2026-11-16 through `POST /api/generate` with `stream=false`.

| Run | Load time | Output tokens | Generation speed | Total time |
| --- | --- | --- | --- | --- |
| Cold (model not loaded), thinking off | 44.4 s | 91 | 5.9 tokens/s | 93.5 s |
| Warm, thinking off | 0.0 s | 77 | 36.3 tokens/s | 2.2 s |
| Warm, thinking on | 0.0 s | 282 | 35.7 tokens/s | 20.3 s |

Memory while loaded: 6.2 GB reported by `ollama ps`, 100% on GPU; `nvidia-smi` showed 7.5 of 8 GB VRAM in use (desktop included); 0.8 GB of system RAM free.

## What worked

- An 8B model at Q4_K_M runs entirely on an 8 GB GPU with an 8192-token context, at about 36 tokens/s once loaded.
- Tests and CI are independent of the model: 4 backend tests and 3 frontend tests run in seconds.

## What failed or surprised

- **Ollama model folder**: the desktop app ignored the `OLLAMA_MODELS` environment variable and used its own setting, pointing at the system drive. The measurement was taken with `ollama serve` started directly; the app setting has to be changed by hand.
- **Cold start**: the first request took 93.5 s in total, and generated at only 5.9 tokens/s even after loading.
- **Thinking mode**: 3.7 times more output tokens for the same question and 9 times the total time.
- **PowerShell 5.1 quoting**: a multi-line `gh pr create --body` with nested quotes was split into several arguments; `--body-file` solved it.

## Limitations

- One run per row; no variance measured.
- The slow cold generation was not investigated; the machine had under 1.5 GB of free RAM at the time.
- In the thinking run, generation accounts for 7.9 s of the 20.3 s total; the rest was not investigated.
- VRAM headroom is about 0.7 GB: a larger context or a second loaded model will not fit.
- pytest prints a Starlette deprecation warning about `httpx` in the test client; not addressed yet.
