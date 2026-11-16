import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('shows the backend version when the health check succeeds', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: 'ok', version: '0.1.0' }),
      }),
    )

    render(<App />)

    expect(await screen.findByText('Backend online (v0.1.0)')).toBeInTheDocument()
  })

  it('shows an offline message when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))

    render(<App />)

    expect(await screen.findByText(/Backend offline/)).toBeInTheDocument()
  })

  it('shows an offline message when the backend answers with an error status', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))

    render(<App />)

    expect(await screen.findByText(/Backend offline/)).toBeInTheDocument()
  })
})
