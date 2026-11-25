import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../../lib/api'
import {
  MAX_TOKENS_NO_THINKING,
  MAX_TOKENS_THINKING,
  runEval,
  type EvalRun,
} from '../../lib/evals'

export interface EvalJob {
  dataset: string
  promptId: string
  model: string
  think: boolean
}

export type JobStatus = 'pending' | 'running' | 'done' | 'error' | 'cancelled'

export interface JobState extends EvalJob {
  key: string
  status: JobStatus
  run?: EvalRun
  error?: string
}

export function jobKey(job: EvalJob): string {
  return `${job.dataset}|${job.model}|${job.think ? 'think' : 'nothink'}|${job.promptId}`
}

/**
 * Runs evaluation jobs one after another. The GPU holds one model at a time,
 * so parallel requests would only make the backend swap models back and forth.
 */
export function useEvalQueue() {
  const [jobs, setJobs] = useState<JobState[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => () => abortRef.current?.abort(), [])

  function update(key: string, change: Partial<JobState>) {
    setJobs((current) => current.map((job) => (job.key === key ? { ...job, ...change } : job)))
  }

  async function start(toRun: EvalJob[]) {
    if (isRunning || toRun.length === 0) return
    const queue: JobState[] = toRun.map((job) => ({ ...job, key: jobKey(job), status: 'pending' }))
    setJobs(queue)
    setIsRunning(true)
    const controller = new AbortController()
    abortRef.current = controller

    try {
      for (const job of queue) {
        if (controller.signal.aborted) {
          update(job.key, { status: 'cancelled' })
          continue
        }
        update(job.key, { status: 'running' })
        try {
          const run = await runEval(
            {
              dataset: job.dataset,
              prompt_id: job.promptId,
              model: job.model,
              think: job.think,
              max_tokens: job.think ? MAX_TOKENS_THINKING : MAX_TOKENS_NO_THINKING,
            },
            controller.signal,
          )
          update(job.key, { status: 'done', run })
        } catch (error) {
          if (controller.signal.aborted) {
            update(job.key, { status: 'cancelled' })
          } else {
            const message =
              error instanceof ApiError
                ? error.message
                : 'Não foi possível falar com o backend. Ele está rodando?'
            update(job.key, { status: 'error', error: message })
          }
        }
      }
    } finally {
      abortRef.current = null
      setIsRunning(false)
    }
  }

  function cancel() {
    abortRef.current?.abort()
  }

  return { jobs, isRunning, start, cancel }
}
