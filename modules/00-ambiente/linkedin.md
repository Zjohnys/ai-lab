# Post para LinkedIn - Módulo 0

Comecei um projeto de estudo público: o AI Lab, uma trilha de engenharia de IA que roda 100% com modelos locais e open source. Sem API paga e sem chave de API.

A regra que me impus: todo resultado precisa de um número medido.

O primeiro, em uma RTX 3050 de 8 GB com o qwen3:8b via Ollama:

- 36 tokens/s com o modelo já carregado
- 44 s para carregar o modelo na primeira chamada
- modelo inteiro na GPU com contexto de 8192 tokens, sobrando menos de 1 GB de VRAM
- o modo "thinking" gerou 3,7 vezes mais tokens e levou 9 vezes mais tempo para a mesma pergunta

O que aprendi montando o ambiente:

- Hardware modesto roda um modelo de 8B com folga de velocidade, mas a memória é contada em megabytes.
- Testes e CI não podem depender do modelo. O pipeline roda em segundos porque nenhuma etapa chama IA.
- Trabalhar com IA no editor é mais revisar do que digitar: lotes pequenos, diff lido linha a linha.

Stack: FastAPI, React, TypeScript, Ollama, GitHub Actions.

Próximo módulo: fundamentos de LLM local, com chat em streaming e medição de tokens por segundo dentro do app.

Repositório: https://github.com/Zjohnys/ai-lab

#AIEngineering #LLM #Ollama #OpenSource #Python
