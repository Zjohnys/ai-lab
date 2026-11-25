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

const PROMPTS = [
  { id: 'v1_basic', description: 'Instrução mínima.' },
  { id: 'v2_definitions', description: 'Com definições.' },
]

export const DATASETS = [
  {
    name: 'support_triage',
    description: 'Casos de desenvolvimento.',
    labels: ['rede', 'hardware'],
    cases: 15,
    prompts: PROMPTS,
  },
  {
    name: 'support_triage_holdout',
    description: 'Casos de validação.',
    labels: ['rede', 'hardware'],
    cases: 10,
    prompts: PROMPTS,
  },
]

/** A finished eval run: two cases, one right and one wrong. */
export function evalRun(model: string, promptId: string, dataset = 'support_triage') {
  return {
    dataset,
    prompt_id: promptId,
    model,
    started_at: '2026-11-25T12:00:00+00:00',
    summary: {
      total: 2,
      correct: 1,
      accuracy: 0.5,
      strict_json_rate: 1,
      json_found_rate: 1,
      valid_label_rate: 1,
      errors: 0,
      mean_latency_seconds: 0.35,
      max_latency_seconds: 0.4,
      mean_tokens_per_second: 31.4,
      per_label: { rede: { total: 1, correct: 1 }, hardware: { total: 1, correct: 0 } },
    },
    results: [
      {
        case_id: 'rede-01',
        expected: 'rede',
        predicted: 'rede',
        correct: true,
        strict_json: true,
        json_found: true,
        label_valid: true,
        raw_output: '{"category": "rede"}',
        error: null,
        latency_seconds: 0.3,
        output_tokens: 8,
        tokens_per_second: 31,
      },
      {
        case_id: 'hardware-03',
        expected: 'hardware',
        predicted: 'software',
        correct: false,
        strict_json: true,
        json_found: true,
        label_valid: true,
        raw_output: '{"category": "software"}',
        error: null,
        latency_seconds: 0.4,
        output_tokens: 8,
        tokens_per_second: 31.8,
      },
    ],
  }
}

export const MODELS = {
  models: [
    { name: 'qwen3:8b', size_bytes: 5225388164, parameter_size: '8.2B', quantization: 'Q4_K_M' },
    { name: 'qwen3:4b', size_bytes: 2600000000, parameter_size: '4.0B', quantization: 'Q4_K_M' },
  ],
  default_chat_model: 'qwen3:8b',
}
