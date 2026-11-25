import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { DATASETS, jsonResponse, MODELS } from './test/sse-helpers'

/** App renders both pages, which ask for the model list and the eval datasets. */
function mockFetch(health: () => Promise<Response>) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url === '/api/health') return health()
      if (url === '/api/evals/datasets') return Promise.resolve(jsonResponse(DATASETS))
      return Promise.resolve(jsonResponse(MODELS))
    }),
  )
}

const healthy = () => Promise.resolve(jsonResponse({ status: 'ok', version: '0.1.0' }))

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('shows the backend version when the health check succeeds', async () => {
    mockFetch(healthy)

    render(<App />)

    expect(await screen.findByText('Backend online (v0.1.0)')).toBeInTheDocument()
  })

  it('shows an offline message when the request fails', async () => {
    mockFetch(() => Promise.reject(new Error('network down')))

    render(<App />)

    expect(await screen.findByText(/Backend offline/)).toBeInTheDocument()
  })

  it('shows an offline message when the backend answers with an error status', async () => {
    mockFetch(() => Promise.resolve(jsonResponse({ detail: 'boom' }, 500)))

    render(<App />)

    expect(await screen.findByText(/Backend offline/)).toBeInTheDocument()
  })

  it('opens on the chat page', async () => {
    mockFetch(healthy)

    render(<App />)

    expect(await screen.findByRole('option', { name: /qwen3:8b/ })).toBeInTheDocument()
    expect(screen.getByLabelText('Mensagem')).toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Dataset' })).not.toBeInTheDocument()
  })

  it('switches to the prompt lab and keeps the chat draft when coming back', async () => {
    mockFetch(healthy)
    render(<App />)
    await screen.findByRole('option', { name: /qwen3:8b/ })
    fireEvent.change(screen.getByLabelText('Mensagem'), { target: { value: 'rascunho' } })

    fireEvent.click(screen.getByRole('button', { name: 'Laboratório de prompts' }))

    expect(await screen.findByRole('combobox', { name: 'Dataset' })).toBeInTheDocument()
    // The chat page is hidden, not unmounted.
    expect(screen.getByLabelText('Mensagem')).not.toBeVisible()

    fireEvent.click(screen.getByRole('button', { name: 'Chat' }))

    expect(screen.getByLabelText('Mensagem')).toBeVisible()
    expect(screen.getByLabelText('Mensagem')).toHaveValue('rascunho')
  })
})
