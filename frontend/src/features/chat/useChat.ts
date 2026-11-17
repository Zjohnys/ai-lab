import { useEffect, useRef, useState } from 'react'
import { ApiError, streamChat, type ChatMessage, type GenerationStats } from '../../lib/api'

export interface ChatSettings {
  model: string
  systemPrompt: string
  temperature: number
  numCtx: number
  think: boolean
}

export type MessageStatus = 'streaming' | 'done' | 'stopped' | 'error'

export interface UiMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  thinking: string
  status: MessageStatus
  /** Context size used for this answer, to show how much of the window was filled. */
  numCtx: number
  stats?: GenerationStats
  error?: string
}

/**
 * Builds what is actually sent to the model: the system prompt, every earlier
 * message that has text, and the new question. The model has no memory; the
 * whole conversation is sent again on every turn.
 */
export function buildHistory(
  systemPrompt: string,
  previous: readonly UiMessage[],
  question: string,
): ChatMessage[] {
  const history: ChatMessage[] = []
  if (systemPrompt.trim()) {
    history.push({ role: 'system', content: systemPrompt.trim() })
  }
  for (const message of previous) {
    if (message.content.trim()) {
      history.push({ role: message.role, content: message.content })
    }
  }
  history.push({ role: 'user', content: question })
  return history
}

export function useChat(settings: ChatSettings) {
  const [messages, setMessages] = useState<UiMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const nextId = useRef(1)

  // Leaving the page cancels a generation in progress.
  useEffect(() => () => abortRef.current?.abort(), [])

  function patch(id: number, change: (message: UiMessage) => UiMessage) {
    setMessages((current) => current.map((message) => (message.id === id ? change(message) : message)))
  }

  async function send(text: string) {
    const question = text.trim()
    if (!question || isStreaming) return

    const history = buildHistory(settings.systemPrompt, messages, question)
    const base = { thinking: '', numCtx: settings.numCtx }
    const userMessage: UiMessage = {
      ...base,
      id: nextId.current++,
      role: 'user',
      content: question,
      status: 'done',
    }
    const answerId = nextId.current++
    const answer: UiMessage = {
      ...base,
      id: answerId,
      role: 'assistant',
      content: '',
      status: 'streaming',
    }
    setMessages((current) => [...current, userMessage, answer])
    setIsStreaming(true)

    const controller = new AbortController()
    abortRef.current = controller
    try {
      const request = {
        model: settings.model || undefined,
        messages: history,
        options: {
          temperature: settings.temperature,
          num_ctx: settings.numCtx,
          think: settings.think,
        },
      }
      for await (const event of streamChat(request, controller.signal)) {
        if (event.type === 'token') {
          patch(answerId, (message) => ({
            ...message,
            content: message.content + event.content,
            thinking: message.thinking + event.thinking,
          }))
        } else if (event.type === 'done') {
          patch(answerId, (message) => ({ ...message, status: 'done', stats: event.stats }))
        } else {
          patch(answerId, (message) => ({ ...message, status: 'error', error: event.message }))
        }
      }
      // The stream closed without a final event: the connection dropped midway.
      patch(answerId, (message) =>
        message.status === 'streaming'
          ? { ...message, status: 'error', error: 'A conexão terminou antes do fim da resposta.' }
          : message,
      )
    } catch (error) {
      if (controller.signal.aborted) {
        patch(answerId, (message) => ({ ...message, status: 'stopped' }))
      } else {
        const detail =
          error instanceof ApiError
            ? error.message
            : 'Não foi possível falar com o backend. Ele está rodando?'
        patch(answerId, (message) => ({ ...message, status: 'error', error: detail }))
      }
    } finally {
      abortRef.current = null
      setIsStreaming(false)
    }
  }

  function stop() {
    abortRef.current?.abort()
  }

  function clear() {
    stop()
    setMessages([])
  }

  return { messages, isStreaming, send, stop, clear }
}
