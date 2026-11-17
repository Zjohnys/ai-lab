import { describe, expect, it } from 'vitest'
import { buildHistory, type UiMessage } from './useChat'

function message(role: UiMessage['role'], content: string, id: number): UiMessage {
  return { id, role, content, thinking: '', status: 'done', numCtx: 8192 }
}

describe('buildHistory', () => {
  it('sends only the question when there is no system prompt and no history', () => {
    expect(buildHistory('', [], 'Oi')).toEqual([{ role: 'user', content: 'Oi' }])
  })

  it('puts the system prompt first and resends the whole conversation', () => {
    const previous = [message('user', 'Oi', 1), message('assistant', 'Olá!', 2)]

    expect(buildHistory('  Responda curto.  ', previous, 'Tudo bem?')).toEqual([
      { role: 'system', content: 'Responda curto.' },
      { role: 'user', content: 'Oi' },
      { role: 'assistant', content: 'Olá!' },
      { role: 'user', content: 'Tudo bem?' },
    ])
  })

  it('leaves out answers that failed before producing any text', () => {
    const previous = [message('user', 'Oi', 1), { ...message('assistant', '', 2), status: 'error' as const }]

    expect(buildHistory('', previous, 'De novo')).toEqual([
      { role: 'user', content: 'Oi' },
      { role: 'user', content: 'De novo' },
    ])
  })

  it('does not send the model reasoning back, only the answer text', () => {
    const previous = [{ ...message('assistant', 'Quatro.', 1), thinking: '2 + 2 = 4' }]

    expect(buildHistory('', previous, 'Certeza?')[0]).toEqual({
      role: 'assistant',
      content: 'Quatro.',
    })
  })
})
