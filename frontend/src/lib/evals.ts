import { requestJson } from './api'

export interface PromptSummary {
  id: string
  description: string
}

export interface DatasetSummary {
  name: string
  description: string
  labels: string[]
  cases: number
  prompts: PromptSummary[]
}

export interface EvalRequest {
  dataset: string
  prompt_id: string
  model: string
  think: boolean
  max_tokens: number
}

export interface CaseResult {
  case_id: string
  expected: string
  predicted: string | null
  correct: boolean
  strict_json: boolean
  json_found: boolean
  label_valid: boolean
  raw_output: string
  error: string | null
  latency_seconds: number
  output_tokens: number
  tokens_per_second: number
}

export interface EvalSummary {
  total: number
  correct: number
  accuracy: number
  strict_json_rate: number
  json_found_rate: number
  valid_label_rate: number
  errors: number
  mean_latency_seconds: number
  max_latency_seconds: number
  mean_tokens_per_second: number
  per_label: Record<string, { total: number; correct: number }>
}

export interface EvalRun {
  dataset: string
  prompt_id: string
  model: string
  started_at: string
  summary: EvalSummary
  results: CaseResult[]
}

/** Without thinking the answer is one short JSON object; with it, reasoning comes first. */
export const MAX_TOKENS_NO_THINKING = 64
export const MAX_TOKENS_THINKING = 2048

export function fetchDatasets(): Promise<DatasetSummary[]> {
  return requestJson<DatasetSummary[]>('/api/evals/datasets')
}

export function runEval(request: EvalRequest, signal?: AbortSignal): Promise<EvalRun> {
  return requestJson<EvalRun>('/api/evals/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })
}
