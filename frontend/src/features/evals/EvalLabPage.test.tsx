import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { DATASETS, evalRun, jsonResponse, MODELS } from '../../test/sse-helpers'
import { EvalLabPage } from './EvalLabPage'

type RunHandler = (body: Record<string, unknown>, init: RequestInit) => Response | Promise<Response>

function mockBackend(run: RunHandler) {
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    if (url === '/api/evals/datasets') return Promise.resolve(jsonResponse(DATASETS))
    if (url === '/api/models') return Promise.resolve(jsonResponse(MODELS))
    if (url === '/api/evals/run') {
      const body = JSON.parse(init?.body as string) as Record<string, unknown>
      return Promise.resolve(run(body, init ?? {}))
    }
    return Promise.reject(new Error(`unexpected request to ${url}`))
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function runBodies(fetchMock: ReturnType<typeof mockBackend>): Record<string, unknown>[] {
  return fetchMock.mock.calls
    .filter(([url]) => url === '/api/evals/run')
    .map(([, init]) => JSON.parse(init?.body as string) as Record<string, unknown>)
}

const answer: RunHandler = (body) =>
  jsonResponse(evalRun(body.model as string, body.prompt_id as string, body.dataset as string))

async function ready() {
  await screen.findByRole('checkbox', { name: 'qwen3:8b' })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('EvalLabPage', () => {
  it('starts with the first dataset, all its prompts and the default model selected', async () => {
    mockBackend(answer)
    render(<EvalLabPage />)
    await ready()

    expect(screen.getByRole('combobox', { name: 'Dataset' })).toHaveValue('support_triage')
    expect(screen.getByRole('checkbox', { name: /v1_basic/ })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: /v2_definitions/ })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'qwen3:8b' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'qwen3:4b' })).not.toBeChecked()
    expect(screen.getByRole('button', { name: 'Rodar 2 avaliações' })).toBeEnabled()
    expect(screen.getByText('30 chamadas ao modelo, uma por vez.')).toBeInTheDocument()
  })

  it('runs every model and prompt combination one at a time with the right options', async () => {
    const fetchMock = mockBackend(answer)
    render(<EvalLabPage />)
    await ready()

    fireEvent.change(screen.getByRole('combobox', { name: 'Dataset' }), {
      target: { value: 'support_triage_holdout' },
    })
    fireEvent.click(screen.getByRole('checkbox', { name: 'qwen3:4b' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Thinking em qwen3:4b' }))
    fireEvent.click(screen.getByRole('checkbox', { name: /v1_basic/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Rodar 2 avaliações' }))

    await waitFor(() => expect(runBodies(fetchMock)).toHaveLength(2))
    expect(runBodies(fetchMock)).toEqual([
      {
        dataset: 'support_triage_holdout',
        prompt_id: 'v2_definitions',
        model: 'qwen3:8b',
        think: false,
        max_tokens: 64,
      },
      {
        dataset: 'support_triage_holdout',
        prompt_id: 'v2_definitions',
        model: 'qwen3:4b',
        think: true,
        max_tokens: 2048,
      },
    ])
  })

  it('shows the summary of each run and the wrong cases on demand', async () => {
    mockBackend(answer)
    render(<EvalLabPage />)
    await ready()

    fireEvent.click(screen.getByRole('button', { name: 'Rodar 2 avaliações' }))

    const row = await screen.findByTestId('row-support_triage|qwen3:8b|nothink|v1_basic')
    await within(row).findByText('1/2 (50%)')
    expect(within(row).getByText('100%')).toBeInTheDocument()
    expect(within(row).getByText('0,35 s')).toBeInTheDocument()

    fireEvent.click(within(row).getByRole('button', { name: 'Ver erros' }))

    expect(screen.getByText('hardware-03')).toBeInTheDocument()
    expect(screen.getByText('{"category": "software"}')).toBeInTheDocument()
    expect(screen.queryByText('rede-01')).not.toBeInTheDocument()
  })

  it('shows a failed run and keeps going with the next one', async () => {
    const fetchMock = mockBackend((body) =>
      body.prompt_id === 'v1_basic'
        ? jsonResponse({ detail: "Model 'qwen3:8b' is not installed." }, 404)
        : answer(body, {}),
    )
    render(<EvalLabPage />)
    await ready()

    fireEvent.click(screen.getByRole('button', { name: 'Rodar 2 avaliações' }))

    expect(await screen.findByRole('alert')).toHaveTextContent("Model 'qwen3:8b' is not installed.")
    const second = await screen.findByTestId('row-support_triage|qwen3:8b|nothink|v2_definitions')
    await within(second).findByText('1/2 (50%)')
    expect(runBodies(fetchMock)).toHaveLength(2)
  })

  it('cancels the running evaluation and skips the ones still waiting', async () => {
    let signal: AbortSignal | undefined
    const fetchMock = mockBackend((_body, init) => {
      signal = init.signal ?? undefined
      return new Promise<Response>((_resolve, reject) => {
        signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
      })
    })
    render(<EvalLabPage />)
    await ready()

    fireEvent.click(screen.getByRole('button', { name: 'Rodar 2 avaliações' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Cancelar' }))

    await waitFor(() => expect(screen.getAllByText('Cancelado')).toHaveLength(2))
    expect(signal?.aborted).toBe(true)
    expect(runBodies(fetchMock)).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'Rodar 2 avaliações' })).toBeInTheDocument()
  })

  it('cannot run without a model or without a prompt', async () => {
    mockBackend(answer)
    render(<EvalLabPage />)
    await ready()

    fireEvent.click(screen.getByRole('checkbox', { name: 'qwen3:8b' }))

    expect(screen.getByRole('button', { name: 'Rodar 0 avaliações' })).toBeDisabled()

    fireEvent.click(screen.getByRole('checkbox', { name: 'qwen3:8b' }))
    fireEvent.click(screen.getByRole('checkbox', { name: /v1_basic/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /v2_definitions/ }))

    expect(screen.getByRole('button', { name: 'Rodar 0 avaliações' })).toBeDisabled()
  })

  it('explains when the datasets cannot be loaded', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(jsonResponse({ detail: 'Could not connect to Ollama.' }, 503))),
    )
    render(<EvalLabPage />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not connect to Ollama.')
  })
})
