import { describe, expect, it } from 'vitest'
import { streamOf } from '../test/sse-helpers'
import { readSse, type SseMessage } from './sse'

async function collect(chunks: (string | Uint8Array)[]): Promise<SseMessage[]> {
  const messages: SseMessage[] = []
  for await (const message of readSse(streamOf(chunks))) messages.push(message)
  return messages
}

describe('readSse', () => {
  it('parses several events that arrive in one chunk', async () => {
    const messages = await collect(['event: token\ndata: {"a":1}\n\nevent: done\ndata: {"b":2}\n\n'])

    expect(messages).toEqual([
      { event: 'token', data: '{"a":1}' },
      { event: 'done', data: '{"b":2}' },
    ])
  })

  it('joins an event that was cut between network chunks', async () => {
    const messages = await collect(['event: tok', 'en\ndata: {"content":', '"Olá"}\n', '\n'])

    expect(messages).toEqual([{ event: 'token', data: '{"content":"Olá"}' }])
  })

  it('keeps an accented character whose bytes were split between chunks', async () => {
    const bytes = new TextEncoder().encode('event: token\ndata: é\n\n')
    const cut = bytes.indexOf(0xc3) + 1 // "é" is 0xC3 0xA9 in UTF-8: cut between the two bytes

    const messages = await collect([bytes.slice(0, cut), bytes.slice(cut)])

    expect(messages).toEqual([{ event: 'token', data: 'é' }])
  })

  it('ignores comments and blocks without data, and joins multi-line data', async () => {
    const messages = await collect([': keep-alive\n\nevent: note\n\ndata: line 1\ndata: line 2\n\n'])

    expect(messages).toEqual([{ event: 'message', data: 'line 1\nline 2' }])
  })

  it('drops an incomplete event left at the end of the stream', async () => {
    const messages = await collect(['event: token\ndata: {"a":1}\n\nevent: token\ndata: {"a":'])

    expect(messages).toEqual([{ event: 'token', data: '{"a":1}' }])
  })
})
