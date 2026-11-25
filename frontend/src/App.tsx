import { useEffect, useState } from 'react'
import { ChatPage } from './features/chat/ChatPage'
import { EvalLabPage } from './features/evals/EvalLabPage'
import { fetchHealth } from './lib/api'

type Tab = 'chat' | 'evals'

const TABS: { id: Tab; label: string }[] = [
  { id: 'chat', label: 'Chat' },
  { id: 'evals', label: 'Laboratório de prompts' },
]

type BackendState =
  | { kind: 'loading' }
  | { kind: 'online'; version: string }
  | { kind: 'offline' }

function App() {
  const [backend, setBackend] = useState<BackendState>({ kind: 'loading' })
  const [tab, setTab] = useState<Tab>('chat')

  useEffect(() => {
    let cancelled = false
    fetchHealth()
      .then((health) => {
        if (!cancelled) setBackend({ kind: 'online', version: health.version })
      })
      .catch(() => {
        if (!cancelled) setBackend({ kind: 'offline' })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-4 py-6">
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">AI Lab</h1>
          <nav aria-label="Seções" className="mt-2 flex gap-2">
            {TABS.map((item) => (
              <button
                key={item.id}
                type="button"
                aria-current={tab === item.id ? 'page' : undefined}
                onClick={() => setTab(item.id)}
                className={
                  tab === item.id
                    ? 'rounded-md bg-slate-900 px-3 py-1 text-sm text-white'
                    : 'rounded-md px-3 py-1 text-sm text-slate-600 hover:bg-slate-100'
                }
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>
        <p role="status" className="text-sm">
          {backend.kind === 'loading' && 'Verificando o backend...'}
          {backend.kind === 'online' && `Backend online (v${backend.version})`}
          {backend.kind === 'offline' &&
            'Backend offline. Inicie com: uv run uvicorn app.main:app --reload'}
        </p>
      </header>
      {/* Both pages stay mounted, so switching tabs keeps the conversation and a running eval. */}
      <main>
        <div hidden={tab !== 'chat'}>
          <ChatPage />
        </div>
        <div hidden={tab !== 'evals'}>
          <EvalLabPage />
        </div>
      </main>
    </div>
  )
}

export default App
