# Módulo 1 - Checklist e exercícios

Para marcar um item, edite este arquivo e troque `[ ]` por `[x]`.

## Checklist

### No chat do app
- [ ] Fiz a mesma pergunta três vezes com temperatura 0 e três vezes com 1,5 e comparei
- [ ] Escrevi um system prompt e vi o modelo segui-lo (ou não)
- [ ] Disse meu nome, limpei a conversa e confirmei que o modelo esqueceu
- [ ] Liguei o thinking e comparei tokens gerados e tempo total com a mesma pergunta sem ele
- [ ] Usei o botão Parar no meio de uma resposta longa
- [ ] Mudei a janela de contexto e observei o tempo de carga na resposta seguinte

### No código
- [ ] Li `backend/app/llm/provider.py` e sei dizer os três métodos da interface
- [ ] Achei em `ollama.py` onde os nanossegundos viram segundos
- [ ] Rodei `uv run pytest -m live -s` e vi os tokens/s impressos
- [ ] Rodei `experiments.py` e comparei meus números com os do README

## Exercício solo (até 30 minutos)

Faça sem pedir para a IA escrever o código. Ela só entra na etapa 5.

**Tempo até o primeiro token.** Hoje a tela mostra tokens/s e tempo total, mas não quanto tempo a pessoa esperou até o texto começar a aparecer.

1. Crie a branch `feat/time-to-first-token`.
2. Em `frontend/src/features/chat/useChat.ts`, guarde o instante em que a pergunta foi enviada e o instante em que chegou o primeiro evento `token` com texto.
3. Mostre a diferença, em segundos, na linha de estatísticas de `MessageBubble.tsx`.
4. Adicione um teste em `ChatPage.test.tsx` que confirma que o valor aparece. Dica: `vi.useFakeTimers()` ou `vi.spyOn(performance, 'now')` controlam o relógio no teste.
5. Peça ao Claude Code para revisar o seu diff, sem alterar arquivos. Decida o que aceitar.
6. Abra o pull request, confira o CI e faça o merge.

Pergunta para pensar enquanto faz: por que medir isso no navegador e não no backend?

## Perguntas para responder com suas palavras

1. Uma resposta levou 12 segundos e a tela mostra 36 tokens/s com 70 tokens gerados. Para onde foi o resto do tempo?
2. Por que a segunda pergunta de uma conversa envia mais tokens que a primeira, mesmo sendo mais curta?
3. Você precisa classificar chamados de suporte em categorias fixas. Que temperatura usaria, e por quê?
4. O que o experimento de estouro de contexto mostrou sobre um fato colocado no início de um texto longo? O que isso muda na forma de montar um prompt?
5. O thinking valeu o custo nas perguntas do experimento? Em que tipo de tarefa você o ligaria?
6. Por que um modelo de 8B em Q4 cabe na sua GPU e o mesmo modelo em Q8 não?
