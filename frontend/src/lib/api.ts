import { readSse, type SseMessage } from './sse'

export interface HealthResponse {
  status: string
  version: string
}

export interface ModelInfo {
  name: string
  size_bytes: number
  parameter_size: string | null
  quantization: string | null
}

export interface ModelsResponse {
  models: ModelInfo[]
  default_chat_model: string
}

export type Role = 'system' | 'user' | 'assistant'

export interface ChatMessage {
  role: Role
  content: string
}

export interface GenerationOptions {
  temperature: number
  num_ctx: number
  think: boolean
  max_tokens?: number
}

export interface GenerationStats {
  prompt_tokens: number
  output_tokens: number
  load_seconds: number
  prompt_eval_seconds: number
  generation_seconds: number
  total_seconds: number
  tokens_per_second: number
}

export interface ChatRequest {
  model?: string
  messages: ChatMessage[]
  options?: GenerationOptions
}

export type ChatEvent =
  | { type: 'token'; content: string; thinking: string }
  | { type: 'done'; stats: GenerationStats }
  | { type: 'error'; message: string }

/** The backend answered with an HTTP error status. `message` is safe to show to the user. */
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch('/api/health')
  if (!response.ok) {
    throw new ApiError(response.status, await errorDetail(response))
  }
  return (await response.json()) as HealthResponse
}

export async function fetchModels(): Promise<ModelsResponse> {
  const response = await fetch('/api/models')
  if (!response.ok) {
    throw new ApiError(response.status, await errorDetail(response))
  }
  return (await response.json()) as ModelsResponse
}

/**
 * Sends a chat request and yields the answer as it is generated.
 * Throws ApiError when the backend refuses the request before streaming starts;
 * failures after that arrive as an event of type 'error'.
 */
export async function* streamChat(
  request: ChatRequest,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })
  if (!response.ok) {
    throw new ApiError(response.status, await errorDetail(response))
  }
  if (!response.body) {
    throw new ApiError(response.status, 'O backend respondeu sem conteúdo.')
  }

  for await (const message of readSse(response.body)) {
    const event = toChatEvent(message)
    if (event) yield event
  }
}

async function errorDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (isRecord(body) && typeof body.detail === 'string') return body.detail
  } catch {
    // Not JSON: fall through to the generic message.
  }
  return `O backend respondeu com erro ${response.status}.`
}

/** Checks the shape of each event at runtime: TypeScript types do not exist on the wire. */
function toChatEvent(message: SseMessage): ChatEvent | null {
  let data: unknown
  try {
    data = JSON.parse(message.data)
  } catch {
    return null
  }
  if (!isRecord(data)) return null

  if (message.event === 'token') {
    return {
      type: 'token',
      content: typeof data.content === 'string' ? data.content : '',
      thinking: typeof data.thinking === 'string' ? data.thinking : '',
    }
  }
  if (message.event === 'done' && isStats(data)) {
    return { type: 'done', stats: data }
  }
  if (message.event === 'error') {
    return {
      type: 'error',
      message: typeof data.message === 'string' ? data.message : 'Erro desconhecido.',
    }
  }
  return null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

const STATS_FIELDS = [
  'prompt_tokens',
  'output_tokens',
  'load_seconds',
  'prompt_eval_seconds',
  'generation_seconds',
  'total_seconds',
  'tokens_per_second',
] as const

function isStats(data: Record<string, unknown>): data is Record<string, unknown> & GenerationStats {
  return STATS_FIELDS.every((field) => typeof data[field] === 'number')
}
