# Módulo 0 - Checklist e exercícios

## Checklist

Marque só o que você fez com as próprias mãos.

### VS Code
- [ ] Abri um arquivo com `Ctrl+P` sem usar a árvore de pastas
- [ ] Usei `Ctrl+D` para editar três ocorrências ao mesmo tempo
- [ ] Renomeei uma variável com `F2`
- [ ] Rodei a task "dev: all" com `Ctrl+Shift+B` e abri `http://localhost:5173`
- [ ] Parei a execução em um breakpoint no endpoint `health` e inspecionei uma variável
- [ ] Enviei uma requisição pelo arquivo `backend/requests.http`

### Terminal e Git
- [ ] Rodei `scripts/hw-diagnose.ps1` e sei dizer quanta VRAM tenho disponível
- [ ] Criei uma branch, fiz um commit e abri um pull request sem ajuda
- [ ] Li um diff inteiro no painel Source Control antes de commitar

### IA
- [ ] Li o `CLAUDE.md` e sei explicar para que serve cada seção
- [ ] Pedi um plano à IA antes de pedir código
- [ ] Recusei ou corrigi pelo menos uma sugestão da IA, sabendo explicar o motivo

### Ollama
- [ ] Rodei `ollama run qwen3:8b --verbose` e anotei os tokens/s
- [ ] Vi `100% GPU` no `ollama ps`
- [ ] Configurei a pasta de modelos do app do Ollama para `F:\ollama\models`

## Exercício solo

Faça sem pedir para a IA escrever o código. Ela só entra na etapa 5.

1. Crie a branch `feat/version-endpoint`.
2. No backend, adicione `GET /api/version`, que devolve o nome do app e a versão do Python em execução. Use um modelo Pydantic para a resposta.
3. Escreva pelo menos dois testes em `backend/tests/test_version.py`.
4. Rode `uv run pytest` e `uv run ruff check .` até passarem.
5. Peça ao Claude Code para revisar o seu diff, sem alterar arquivos. Para cada sugestão, decida aceitar ou recusar e anote o motivo em uma linha.
6. Abra o pull request, confira o CI verde e faça o merge.

Dicas, só se travar: `sys.version_info` e `platform.python_version()` dão a versão do Python; `backend/tests/test_health.py` mostra o formato de um teste.

## Perguntas para responder com suas palavras

1. Por que a primeira resposta do modelo levou 44 segundos e a segunda, 2?
2. O que acontece se você pedir um contexto de 32 mil tokens neste hardware? Como confirmaria?
3. Por que o CI deste projeto nunca chama um modelo de verdade?
4. Qual a diferença entre `.env` e `.env.example`, e o que acontece se você commitar o primeiro?
