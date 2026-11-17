import { useEffect, useState } from 'react'
import { ChatPage } from './features/chat/ChatPage'
import { fetchHealth } from './lib/api'

type BackendState =
  | { kind: 'loading' }
  | { kind: 'online'; version: string }
  | { kind: 'offline' }

function App() {
  const [backend, setBackend] = useState<BackendState>({ kind: 'loading' })

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
          <p className="text-sm text-slate-600">Módulo 1: chat com modelo local</p>
        </div>
        <p role="status" className="text-sm">
          {backend.kind === 'loading' && 'Verificando o backend...'}
          {backend.kind === 'online' && `Backend online (v${backend.version})`}
          {backend.kind === 'offline' &&
            'Backend offline. Inicie com: uv run uvicorn app.main:app --reload'}
        </p>
      </header>
      <main>
        <ChatPage />
      </main>
    </div>
  )
}

export default App
