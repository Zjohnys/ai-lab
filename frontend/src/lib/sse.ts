export interface SseMessage {
  event: string
  data: string
}

/**
 * Reads Server-Sent Events from a fetch response body.
 *
 * The browser's EventSource only supports GET, and /api/chat is a POST,
 * so the stream is parsed by hand. Events are separated by a blank line.
 * Our backend always uses "\n" line endings.
 */
export async function* readSse(body: ReadableStream<Uint8Array>): AsyncGenerator<SseMessage> {
  const reader = body.getReader()
  // One decoder for the whole stream: with { stream: true } it keeps the bytes of a
  // character that was cut between two network chunks (common with "é", "ã", "ç").
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let boundary = buffer.indexOf('\n\n')
      while (boundary !== -1) {
        const message = parseBlock(buffer.slice(0, boundary))
        buffer = buffer.slice(boundary + 2)
        if (message) yield message
        boundary = buffer.indexOf('\n\n')
      }
    }
  } finally {
    // Runs on normal end, on error and when the consumer stops early.
    await reader.cancel().catch(() => undefined)
  }
}

function parseBlock(block: string): SseMessage | null {
  let event = 'message'
  const dataLines: string[] = []

  for (const line of block.split('\n')) {
    if (line.startsWith(':')) continue // comment / keep-alive
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''))
  }

  if (dataLines.length === 0) return null
  return { event, data: dataLines.join('\n') }
}
