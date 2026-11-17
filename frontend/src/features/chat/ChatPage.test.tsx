import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { jsonResponse, MODELS, sseEvent, sseResponse, STATS } from '../../test/sse-helpers'
import { ChatPage } from './ChatPage'

type ChatHandler = (init: RequestInit) => Response | Promise<Response>

/** Routes fetch by URL: /api/models answers the model list, /api/chat uses the given handler. */
function mockBackend(chat: ChatHandler, models: Response = jsonResponse(MODELS)) {
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    if (url === '/api/models') return Promise.resolve(models)
    if (url === '/api/chat') return Promise.resolve(chat(init ?? {}))
    return Promise.reject(new Error(`unexpected request to ${url}`))
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function chatBodies(fetchMock: ReturnType<typeof mockBackend>): Record<string, unknown>[] {
  return fetchMock.mock.calls
    .filter(([url]) => url === '/api/chat')
    .map(([, init]) => JSON.parse(init?.body as string) as Record<string, unknown>)
}

async function ask(question: string) {
  // Wait for the model list so the default model is already selected.
  await screen.findByRole('option', { name: /qwen3:8b/ })
  fireEvent.change(screen.getByLabelText('Mensagem'), { target: { value: question } })
  fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))
}

function answer(...pieces: string[]): Response {
  return sseResponse([
    ...pieces.map((content) => sseEvent('token', { content, thinking: '' })),
    sseEvent('done', STATS),
  ])
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ChatPage', () => {
  it('shows the question, the streamed answer and the measured stats', async () => {
    mockBackend(() => answer('Um token ', 'é um pedaço ', 'de texto.'))
    render(<ChatPage />)

    await ask('O que é um token?')

    expect(await screen.findByText('Um token é um pedaço de texto.')).toBeInTheDocument()
    expect(screen.getByText('O que é um token?')).toBeInTheDocument()
    const stats = screen.getByTestId('stats')
    expect(stats).toHaveTextContent('36,1 tokens/s')
    expect(stats).toHaveTextContent('80 tokens gerados')
    expect(stats).toHaveTextContent('contexto: 110 de 8192 tokens')
    expect(stats).toHaveTextContent('carga do modelo: 8,2 s')
    expect(screen.getByLabelText('Mensagem')).toHaveValue('')
  })

  it('sends the selected model, the system prompt and the chosen options', async () => {
    const fetchMock = mockBackend(() => answer('ok'))
    render(<ChatPage />)
    await screen.findByRole('option', { name: /qwen3:8b/ })

    fireEvent.change(screen.getByLabelText(/^Modelo/), { target: { value: 'qwen3:4b' } })
    fireEvent.change(screen.getByLabelText(/^System prompt/), {
      target: { value: 'Responda em uma frase.' },
    })
    fireEvent.change(screen.getByLabelText(/^Temperatura/), { target: { value: '1.2' } })
    fireEvent.change(screen.getByLabelText(/^Janela de contexto/), { target: { value: '4096' } })
    fireEvent.click(screen.getByLabelText(/^Thinking/))
    await ask('Oi')
    await screen.findByText('ok')

    expect(chatBodies(fetchMock)[0]).toEqual({
      model: 'qwen3:4b',
      messages: [
        { role: 'system', content: 'Responda em uma frase.' },
        { role: 'user', content: 'Oi' },
      ],
      options: { temperature: 1.2, num_ctx: 4096, think: true },
    })
  })

  it('resends the earlier turns with the second question', async () => {
    const fetchMock = mockBackend(() => answer('Olá!'))
    render(<ChatPage />)

    await ask('Oi')
    await screen.findByText('Olá!')
    await ask('Tudo bem?')
    await waitFor(() => expect(chatBodies(fetchMock)).toHaveLength(2))

    expect(chatBodies(fetchMock)[1].messages).toEqual([
      { role: 'user', content: 'Oi' },
      { role: 'assistant', content: 'Olá!' },
      { role: 'user', content: 'Tudo bem?' },
    ])
  })

  it('shows the backend message when the model is not installed', async () => {
    const detail = "Model 'qwen3:8b' is not installed. Run: ollama pull qwen3:8b"
    mockBackend(() => jsonResponse({ detail }, 404))
    render(<ChatPage />)

    await ask('Oi')

    expect(await screen.findByRole('alert')).toHaveTextContent(detail)
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeInTheDocument()
  })

  it('keeps the partial answer and shows the error when generation fails midway', async () => {
    mockBackend(() =>
      sseResponse([
        sseEvent('token', { content: 'Um token ', thinking: '' }),
        sseEvent('error', { message: 'CUDA out of memory' }),
      ]),
    )
    render(<ChatPage />)

    await ask('O que é um token?')

    expect(await screen.findByRole('alert')).toHaveTextContent('CUDA out of memory')
    expect(screen.getByText('Um token')).toBeInTheDocument()
  })

  it('explains what to check when the backend cannot be reached', async () => {
    mockBackend(() => Promise.reject(new TypeError('Failed to fetch')))
    render(<ChatPage />)

    await ask('Oi')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível falar com o backend. Ele está rodando?',
    )
  })

  it('stops the generation when the user clicks Parar', async () => {
    let signal: AbortSignal | undefined
    mockBackend((init) => {
      signal = init.signal ?? undefined
      // A stream that sends one token and then stays open until the request is aborted.
      const body = new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(
            new TextEncoder().encode(sseEvent('token', { content: 'Era uma vez', thinking: '' })),
          )
          signal?.addEventListener('abort', () =>
            controller.error(new DOMException('Aborted', 'AbortError')),
          )
        },
      })
      return new Response(body, { status: 200 })
    })
    render(<ChatPage />)

    await ask('Conte uma história longa.')
    await screen.findByText('Era uma vez')
    fireEvent.click(screen.getByRole('button', { name: 'Parar' }))

    expect(await screen.findByText('Geração interrompida.')).toBeInTheDocument()
    expect(signal?.aborted).toBe(true)
    expect(screen.getByText('Era uma vez')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeInTheDocument()
  })

  it('shows the thinking text separately from the answer', async () => {
    mockBackend(() =>
      sseResponse([
        sseEvent('token', { content: '', thinking: '2 + 2 = 4' }),
        sseEvent('token', { content: 'Quatro.', thinking: '' }),
        sseEvent('done', STATS),
      ]),
    )
    render(<ChatPage />)

    await ask('Quanto é 2 + 2?')

    expect(await screen.findByText('Quatro.')).toBeInTheDocument()
    expect(screen.getByText('Raciocínio do modelo')).toBeInTheDocument()
    expect(screen.getByText('2 + 2 = 4')).toBeInTheDocument()
  })

  it('still works with the server default when the model list fails to load', async () => {
    const fetchMock = mockBackend(
      () => answer('ok'),
      jsonResponse({ detail: 'Could not connect to Ollama. Is it running?' }, 503),
    )
    render(<ChatPage />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not connect to Ollama')
    fireEvent.change(screen.getByLabelText('Mensagem'), { target: { value: 'Oi' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))
    await screen.findByText('ok')

    expect(chatBodies(fetchMock)[0]).not.toHaveProperty('model')
  })

  it('does not send an empty message', async () => {
    const fetchMock = mockBackend(() => answer('ok'))
    render(<ChatPage />)
    await screen.findByRole('option', { name: /qwen3:8b/ })

    fireEvent.change(screen.getByLabelText('Mensagem'), { target: { value: '   ' } })

    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()
    expect(chatBodies(fetchMock)).toHaveLength(0)
  })
})
