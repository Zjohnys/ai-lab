# Post para LinkedIn - Módulo 1

Módulo 1 do AI Lab: um chat com modelo local em streaming, e quatro experimentos medidos em uma RTX 3050 de 8 GB com o qwen3:8b.

O resultado que mais me ensinou: quando o prompt não cabe na janela de contexto, o Ollama corta o início do texto em silêncio. Sem erro, sem aviso. Coloquei um código no começo de um texto longo e perguntei por ele: o modelo respondeu com confiança, e errado. O mesmo código no fim do texto foi encontrado em todas as tentativas.

Os outros números:

- Temperatura 0: 5 respostas iguais em 5. Temperatura 1,5: 4 respostas diferentes em 5.
- Thinking ligado: acertou 6 de 6 perguntas de raciocínio, contra 4 de 6 desligado. Custou 19 vezes mais tokens e 18 vezes mais tempo.
- Janela de 8 mil tokens: modelo inteiro na GPU, 38 tokens/s. Janela de 16 mil: 17% do modelo vai para a CPU e a velocidade cai para 20 tokens/s.

O que construí:

- Uma camada LLMProvider que isola o modelo do resto do app. 78 testes rodam sem GPU, em segundos, no CI.
- Streaming de ponta a ponta: Ollama, FastAPI com Server-Sent Events e React, com botão de parar que cancela a geração na GPU.

Lição prática: quem monta prompts longos (histórico de chat, RAG) precisa contar tokens por conta própria. O modelo não avisa quando perdeu informação.

Limitação honesta: uma execução por configuração e só seis perguntas de raciocínio. Os números mostram ordem de grandeza, não médias.

Próximo módulo: avaliação de prompts com casos de teste e gabarito.

Repositório: https://github.com/Zjohnys/ai-lab

#AIEngineering #LLM #Ollama #OpenSource #Python #React
