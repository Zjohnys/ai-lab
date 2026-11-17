import type { GenerationStats } from '../../lib/api'
import type { UiMessage } from './useChat'

function formatNumber(value: number, digits = 1): string {
  return value.toLocaleString('pt-BR', { maximumFractionDigits: digits })
}

function StatsLine({ stats, numCtx }: { stats: GenerationStats; numCtx: number }) {
  const used = stats.prompt_tokens + stats.output_tokens
  return (
    <p className="mt-2 text-xs text-slate-500" data-testid="stats">
      <strong>{formatNumber(stats.tokens_per_second)} tokens/s</strong>
      {' · '}
      {stats.output_tokens} tokens gerados
      {' · '}
      contexto: {used} de {numCtx} tokens
      {' · '}
      carga do modelo: {formatNumber(stats.load_seconds)} s{' · '}
      total: {formatNumber(stats.total_seconds)} s
    </p>
  )
}

export function MessageBubble({ message }: { message: UiMessage }) {
  const isUser = message.role === 'user'
  const waiting = message.status === 'streaming' && !message.content && !message.thinking

  return (
    <li className={isUser ? 'flex justify-end' : 'flex justify-start'}>
      <div
        className={
          isUser
            ? 'max-w-[85%] rounded-2xl bg-slate-900 px-4 py-2 text-white'
            : 'max-w-[85%] rounded-2xl bg-slate-100 px-4 py-2 text-slate-900'
        }
      >
        <p className="sr-only">{isUser ? 'Você' : 'Modelo'}</p>

        {message.thinking && (
          <details className="mb-2 text-sm text-slate-500">
            <summary className="cursor-pointer">Raciocínio do modelo</summary>
            <p className="mt-1 whitespace-pre-wrap">{message.thinking}</p>
          </details>
        )}

        {waiting ? (
          <p className="text-slate-500">Aguardando o modelo (a primeira resposta carrega o modelo)...</p>
        ) : (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        )}

        {message.status === 'stopped' && (
          <p className="mt-2 text-xs text-amber-700">Geração interrompida.</p>
        )}
        {message.status === 'error' && (
          <p role="alert" className="mt-2 text-sm text-red-700">
            {message.error}
          </p>
        )}
        {message.stats && <StatsLine stats={message.stats} numCtx={message.numCtx} />}
      </div>
    </li>
  )
}
