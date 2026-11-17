const encoder = new TextEncoder()

export function sseEvent(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`
}

export function streamOf(chunks: (string | Uint8Array)[]): ReadableStream<Uint8Array> {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(typeof chunk === 'string' ? encoder.encode(chunk) : chunk)
      }
      controller.close()
    },
  })
}

export function sseResponse(chunks: (string | Uint8Array)[]): Response {
  return new Response(streamOf(chunks), {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  })
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export const STATS = {
  prompt_tokens: 30,
  output_tokens: 80,
  load_seconds: 8.2,
  prompt_eval_seconds: 0.4,
  generation_seconds: 2.2,
  total_seconds: 10.8,
  tokens_per_second: 36.1,
}

export const MODELS = {
  models: [
    { name: 'qwen3:8b', size_bytes: 5225388164, parameter_size: '8.2B', quantization: 'Q4_K_M' },
    { name: 'qwen3:4b', size_bytes: 2600000000, parameter_size: '4.0B', quantization: 'Q4_K_M' },
  ],
  default_chat_model: 'qwen3:8b',
}
