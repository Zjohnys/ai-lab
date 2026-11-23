# Módulo 1 - Fundamentos de LLM local

Objetivo: entender o que acontece entre a sua pergunta e a resposta do modelo, e saber medir cada parte. Os números citados aqui estão no [README](README.md) e foram medidos nesta máquina.

## 1. Tokens

O modelo não lê letras nem palavras: lê **tokens**, pedaços de texto que podem ser uma palavra, parte de uma palavra ou um símbolo. Tudo é contado em tokens: o tamanho da pergunta, o tamanho da resposta, o limite do contexto e a velocidade.

- Em português, uma palavra costuma virar mais de um token, porque os modelos foram treinados com mais texto em inglês.
- A resposta é gerada **um token por vez**. Cada token novo é escolhido olhando para tudo o que veio antes.
- Por isso a velocidade é medida em **tokens por segundo**, e por isso o streaming é natural: o texto já nasce em pedaços.

No app, cada resposta mostra `tokens gerados` e `tokens/s`. No código, eles vêm de `GenerationStats` em `backend/app/llm/types.py`.

## 2. Janela de contexto

A **janela de contexto** (`num_ctx`) é o máximo de tokens que o modelo enxerga de uma vez: system prompt, histórico, pergunta atual e a resposta em construção, tudo somado.

Três consequências práticas:

1. **O modelo não tem memória.** Quem lembra da conversa é o app, que reenvia o histórico inteiro a cada turno. Veja `buildHistory` em `frontend/src/features/chat/useChat.ts`.
2. **Conversa longa enche a janela.** A linha de estatísticas do chat mostra `contexto: X de Y tokens`.
3. **Quando estoura, alguma coisa é cortada, e nem sempre há aviso.** O experimento 3 do README mede o que acontece neste modelo.

Contexto maior custa memória de vídeo. O experimento 4 mede quanto.

## 3. Temperatura

A cada passo o modelo calcula a probabilidade de cada token possível. A **temperatura** controla como ele escolhe:

- **0**: sempre o mais provável. Mesma pergunta, mesma resposta (ou quase).
- **0,7**: alguma variação. É o padrão de muitas ferramentas de chat.
- **Acima de 1**: tokens improváveis ganham chance. Mais variedade e mais erro.

Regra prática: temperatura baixa para tarefas com resposta certa (classificar, extrair, gerar JSON) e mais alta para tarefas em que variedade é o objetivo (nomes, ideias). O padrão deste projeto é 0,2.

O parâmetro `seed` fixa o sorteio: com a mesma seed e a mesma temperatura, o resultado se repete. Útil para reproduzir um teste.

## 4. System prompt

O **system prompt** é uma mensagem com papel `system`, enviada antes da conversa, que define como o modelo deve se comportar: papel, tom, formato e restrições.

- Vale para a conversa inteira, sem precisar repetir.
- Ocupa tokens da janela em todos os turnos.
- Modelos pequenos seguem system prompts simples e diretos melhor do que longos e cheios de exceções.

O Módulo 3 trata de como escrever bons prompts; aqui basta saber onde ele entra.

## 5. Quantização

Os pesos de um modelo são números. Na forma original, cada um ocupa 16 bits. **Quantizar** é guardar cada peso com menos bits, o que reduz tamanho e uso de memória ao custo de alguma qualidade.

| Nome | Bits por peso (aprox.) | Uso |
| --- | --- | --- |
| F16 | 16 | Original; grande demais para GPU de consumidor |
| Q8_0 | 8 | Quase sem perda; o dobro do tamanho do Q4 |
| Q5_K_M | 5,7 | Meio-termo |
| Q4_K_M | 4,8 | Padrão do Ollama; melhor relação tamanho e qualidade |
| Q3, Q2 | 3 ou menos | Perda de qualidade visível |

O `qwen3:8b` deste projeto é Q4_K_M: 8,2 bilhões de parâmetros em 5,2 GB. Em Q8 teria perto de 9 GB e não caberia nos 8 GB de VRAM.

Regra prática para escolher: um modelo maior em Q4 costuma ser melhor que um modelo menor em Q8 do mesmo tamanho em disco. O Módulo 9 mede isso.

## 6. Thinking

Alguns modelos, como o `qwen3`, podem **raciocinar antes de responder**: geram um texto de rascunho (o "thinking") e só depois a resposta final.

- O rascunho também é feito de tokens, então custa tempo.
- Pode ajudar em problemas com vários passos e não ajuda em perguntas diretas.
- Neste projeto fica desligado por padrão e é ligado no painel de parâmetros.

O experimento 2 do README compara acerto, tokens e tempo com e sem thinking.

## 7. Streaming

Sem streaming, o app espera a resposta inteira e mostra tudo de uma vez. Com streaming, cada token aparece assim que é gerado. O tempo total é o mesmo; o que muda é o **tempo até o primeiro token**, que é o que a pessoa percebe como velocidade.

O caminho de um token neste projeto:

```
Ollama            linha JSON por pedaço (NDJSON)
  -> OllamaProvider   valida a linha e devolve um ChatChunk
  -> POST /api/chat   converte em evento SSE: token, done ou error
  -> readSse          junta os bytes e separa os eventos
  -> useChat          acrescenta o texto à mensagem na tela
```

Dois detalhes que valem para qualquer API de LLM com streaming:

- **O status HTTP sai antes do conteúdo.** Erro antes do primeiro token vira `404` ou `503`; erro depois vira um evento `error` dentro do stream.
- **Cancelar precisa chegar até o modelo.** O botão Parar aborta o `fetch`, o backend fecha o gerador e a conexão com o Ollama é encerrada.

## 8. As três fases de uma resposta

O tempo total de uma resposta se divide em:

| Fase | O que é | Campo |
| --- | --- | --- |
| Carga | Ler o modelo do disco para a VRAM. Só na primeira chamada ou ao mudar `num_ctx` | `load_seconds` |
| Leitura do prompt | Processar os tokens de entrada | `prompt_eval_seconds` |
| Geração | Produzir os tokens de saída | `generation_seconds` |

`tokens/s` é sempre `tokens gerados / tempo de geração`. Uma resposta pode demorar 10 segundos e ainda assim ter 36 tokens/s, se 8 desses segundos foram carga.

## 9. A camada `LLMProvider`

Todo o app fala com o modelo por uma única interface, em `backend/app/llm/`:

- **`LLMProvider`**: o contrato. `chat_stream`, `embed`, `list_models`.
- **`OllamaProvider`**: a implementação real.
- **`FakeProvider`**: respostas fixas, para testes e CI.

Isso permite testar endpoints, erros e telas sem GPU e em segundos. Os testes que precisam do modelo de verdade são marcados com `live` e ficam fora do CI.
