import { afterEach, describe, expect, it, vi } from 'vitest'
import { jsonResponse, sseEvent, sseResponse, STATS } from '../test/sse-helpers'
import { ApiError, streamChat, type ChatEvent } from './api'

const REQUEST = { messages: [{ role: 'user' as const, content: 'Oi' }] }

async function collect(): Promise<ChatEvent[]> {
  const events: ChatEvent[] = []
  for await (const event of streamChat(REQUEST)) events.push(event)
  return events
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('streamChat', () => {
  it('posts the request as JSON and yields typed events', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      sseResponse([
        sseEvent('token', { content: 'Olá', thinking: '' }),
        sseEvent('token', { content: '!', thinking: '' }),
        sseEvent('done', STATS),
      ]),
    )
    vi.stubGlobal('fetch', fetchMock)

    const events = await collect()

    expect(events).toEqual([
      { type: 'token', content: 'Olá', thinking: '' },
      { type: 'token', content: '!', thinking: '' },
      { type: 'done', stats: STATS },
    ])
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/chat')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual(REQUEST)
  })

  it('throws ApiError with the backend detail when the request is refused', async () => {
    const detail = "Model 'x' is not installed. Run: ollama pull x"
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail }, 404)))

    const failure = await collect().catch((error: unknown) => error)

    expect(failure).toBeInstanceOf(ApiError)
    expect((failure as ApiError).status).toBe(404)
    expect((failure as ApiError).message).toBe(detail)
  })

  it('uses a generic message when the error body is not the expected JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>', { status: 502 })))

    const failure = await collect().catch((error: unknown) => error)

    expect((failure as ApiError).message).toBe('O backend respondeu com erro 502.')
  })

  it('yields an error event sent in the middle of the stream', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        sseResponse([
          sseEvent('token', { content: 'Um', thinking: '' }),
          sseEvent('error', { message: 'CUDA out of memory' }),
        ]),
      ),
    )

    expect(await collect()).toEqual([
      { type: 'token', content: 'Um', thinking: '' },
      { type: 'error', message: 'CUDA out of memory' },
    ])
  })

  it('skips unknown events, malformed JSON and incomplete stats', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        sseResponse([
          sseEvent('ping', {}),
          'event: token\ndata: not json\n\n',
          sseEvent('done', { output_tokens: 3 }),
          sseEvent('token', { content: 'ok', thinking: '' }),
        ]),
      ),
    )

    expect(await collect()).toEqual([{ type: 'token', content: 'ok', thinking: '' }])
  })
})
