import { useEffect, useState } from 'react'
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
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-4 px-4">
      <h1 className="text-4xl font-bold tracking-tight">AI Lab</h1>
      <p className="text-slate-600">
        Escola pessoal de engenharia de IA, rodando só com modelos locais.
      </p>
      <p role="status" className="text-sm">
        {backend.kind === 'loading' && 'Verificando o backend...'}
        {backend.kind === 'online' && `Backend online (v${backend.version})`}
        {backend.kind === 'offline' &&
          'Backend offline. Inicie com: uv run uvicorn app.main:app --reload'}
      </p>
    </main>
  )
}

export default App
