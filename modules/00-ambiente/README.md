# Module 0 - Professional environment with AI

> In progress. This file currently holds only the first measurement; the full README is written when the module closes.

## First measurement

Model `qwen3:8b` (Q4_K_M, 5.2 GB on disk) on Ollama 0.40.16, RTX 3050 8 GB, `num_ctx=8192`, `temperature=0.2`.
Prompt (Portuguese): "Explique em 3 frases o que é um token em um modelo de linguagem."
Single run per row, measured on 2026-11-16 through `POST /api/generate` with `stream=false`.

| Run | Load time | Output tokens | Generation speed | Total time |
| --- | --- | --- | --- | --- |
| Cold (model not loaded), thinking off | 44.4 s | 91 | 5.9 tokens/s | 93.5 s |
| Warm, thinking off | 0.0 s | 77 | 36.3 tokens/s | 2.2 s |
| Warm, thinking on | 0.0 s | 282 | 35.7 tokens/s | 20.3 s |

Memory while loaded: 6.2 GB reported by `ollama ps`, 100% on GPU; `nvidia-smi` showed 7.5 of 8 GB VRAM in use (desktop included); 0.8 GB of system RAM free.

## What this shows

- The first request pays for loading the model: 44 s here. Later requests start immediately while the model stays loaded (5 minutes by default).
- Thinking mode produced 3.7 times more tokens for the same question and took 9 times longer in total.
- The model fits entirely on the GPU with an 8192-token context, but with about 0.7 GB of VRAM to spare. A larger context or a second loaded model will not fit.

## Limitations

- One run per row; no variance measured.
- The cold run was slow even after loading (5.9 tokens/s). The cause was not investigated; the machine had under 1.5 GB of free RAM at the time.
- In the thinking run, generation accounts for 7.9 s of the 20.3 s total. The remaining time was not investigated.
