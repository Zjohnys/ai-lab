import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { ApiError, fetchModels, type ModelInfo } from '../../lib/api'
import { ChatSettingsPanel } from './ChatSettingsPanel'
import { MessageBubble } from './MessageBubble'
import { useChat, type ChatSettings } from './useChat'

const DEFAULT_SETTINGS: ChatSettings = {
  model: '',
  systemPrompt: '',
  temperature: 0.2,
  numCtx: 8192,
  think: false,
}

export function ChatPage() {
  const [settings, setSettings] = useState<ChatSettings>(DEFAULT_SETTINGS)
  const [models, setModels] = useState<ModelInfo[]>([])
  const [modelsError, setModelsError] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const { messages, isStreaming, send, stop, clear } = useChat(settings)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false
    fetchModels()
      .then((response) => {
        if (cancelled) return
        setModels(response.models)
        setSettings((current) => ({ ...current, model: response.default_chat_model }))
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setModelsError(
          error instanceof ApiError ? error.message : 'Não foi possível listar os modelos.',
        )
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Keep the newest text in view while the answer grows.
  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: 'end' })
  }, [messages])

  function submit(event?: FormEvent) {
    event?.preventDefault()
    if (!draft.trim() || isStreaming) return
    void send(draft)
    setDraft('')
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-[18rem_1fr]">
      <aside>
        <ChatSettingsPanel
          settings={settings}
          models={models}
          modelsError={modelsError}
          disabled={isStreaming}
          onChange={setSettings}
        />
      </aside>

      <section aria-label="Conversa" className="flex min-h-[60vh] flex-col gap-4">
        {messages.length === 0 ? (
          <p className="text-slate-500">
            Faça uma pergunta. Depois mude a temperatura ou o system prompt e pergunte de novo para
            comparar.
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </ul>
        )}
        <div ref={endRef} />

        <form onSubmit={submit} className="mt-auto flex flex-col gap-2">
          <textarea
            aria-label="Mensagem"
            className="rounded-md border border-slate-300 px-3 py-2"
            rows={3}
            placeholder="Escreva sua mensagem. Enter envia, Shift+Enter quebra a linha."
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
          />
          <div className="flex gap-2">
            {isStreaming ? (
              <button
                type="button"
                onClick={stop}
                className="rounded-md bg-red-700 px-4 py-2 font-medium text-white"
              >
                Parar
              </button>
            ) : (
              <button
                type="submit"
                disabled={!draft.trim()}
                className="rounded-md bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-40"
              >
                Enviar
              </button>
            )}
            <button
              type="button"
              onClick={clear}
              disabled={messages.length === 0}
              className="rounded-md border border-slate-300 px-4 py-2 disabled:opacity-40"
            >
              Limpar conversa
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
