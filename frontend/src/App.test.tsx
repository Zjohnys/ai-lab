import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { jsonResponse, MODELS } from './test/sse-helpers'

/** App also renders the chat page, which asks for the model list. */
function mockFetch(health: () => Promise<Response>) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => (url === '/api/health' ? health() : Promise.resolve(jsonResponse(MODELS)))),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('shows the backend version when the health check succeeds', async () => {
    mockFetch(() => Promise.resolve(jsonResponse({ status: 'ok', version: '0.1.0' })))

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

  it('renders the chat page', async () => {
    mockFetch(() => Promise.resolve(jsonResponse({ status: 'ok', version: '0.1.0' })))

    render(<App />)

    expect(await screen.findByRole('option', { name: /qwen3:8b/ })).toBeInTheDocument()
    expect(screen.getByLabelText('Mensagem')).toBeInTheDocument()
  })
})
