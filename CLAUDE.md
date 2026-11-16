# AI Lab

Escola pessoal de engenharia de IA. Monorepo: backend FastAPI, frontend React, módulos de estudo.

## Regra central
- Nenhuma API de IA em nuvem. Toda inferência passa por `LLMProvider` (`backend/app/llm`).
- Implementação padrão: Ollama local. Nunca adicionar SDK de provedor pago nem chave de API.

## Stack
- Backend: Python 3.13, uv, FastAPI, Pydantic v2, SQLite + sqlite-vec, pytest, Ruff.
- Frontend: React, TypeScript strict, Vite, Tailwind, Vitest.
- Modelos: `qwen3:8b` (chat), `qwen2.5-coder:7b` (code), `bge-m3` (embeddings).
- Hardware alvo: RTX 3050 8 GB VRAM, 16 GB RAM. Um modelo carregado por vez; `num_ctx` até 8192.

## Comandos
- Backend: `cd backend; uv run uvicorn app.main:app --reload`
- Testes backend: `cd backend; uv run pytest`
- Lint backend: `cd backend; uv run ruff check .`
- Frontend: `cd frontend; npm run dev`
- Testes frontend: `cd frontend; npm test`
- Lint frontend: `cd frontend; npm run lint` (oxlint, padrão do template Vite atual)
- O frontend chama `/api/*`; o Vite faz proxy para `http://localhost:8000`.

## Como trabalhar
- Planejar antes de codar. Lotes de no máximo 3 itens; parar e esperar aprovação.
- Explicar o porquê de cada decisão e o trade-off. Ensinar o nome do atalho, comando ou técnica usada.
- Responder em português; código, identificadores, commits e comandos em inglês.
- READMEs em inglês; interface do app em português.
- Não escrever código de exercício marcado como "solo".

## Ritmo e ordem
- Ritmo: cerca de 2 horas por semana. Uma sessão = um lote = um pull request mesclado.
- Exercício solo de até 30 minutos; não bloqueia o lote seguinte.
- Downloads, instalações e benchmarks longos rodam fora do tempo de sessão.
- Ordem de execução dos módulos: 0, 1, 2, 4, 5, 6, 7, 8, 3, 9. A numeração das pastas não muda.
- Primeiro projeto de portfólio (benchmark de modelos) é publicado em repositório próprio ao fim do Módulo 2.

## Código
- Testes nunca chamam modelo real: usar `FakeProvider`. Testes com modelo ficam em `@pytest.mark.live`, fora do CI.
- Toda saída de LLM é validada com Pydantic antes de ser usada.
- Configuração só via `.env` (lido em `app/core/config.py`); manter `.env.example` atualizado.
- Type hints em todo Python; sem `any` no TypeScript.
- Shell é PowerShell no Windows: usar `;` e não `&&` nos exemplos.

## Git
- Commits pequenos, Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- Nunca commitar direto na `main` depois do commit inicial: branch + pull request.
- Nunca commitar `.env`, modelos, bancos `.db` ou `node_modules`.

## Definição de pronto (por módulo)
- Testes passando, README com problema, arquitetura, como rodar, resultados medidos e limitações.
- Pelo menos um número medido (acurácia, latência ou tokens/s).
- Texto de post para LinkedIn em `modules/NN-nome/linkedin.md`.
