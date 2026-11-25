import { useState } from 'react'
import type { CaseResult } from '../../lib/evals'
import type { JobState } from './useEvalQueue'

function percent(value: number): string {
  return `${Math.round(value * 100)}%`
}

function seconds(value: number): string {
  return `${value.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} s`
}

const STATUS_TEXT: Record<JobState['status'], string> = {
  pending: 'Na fila',
  running: 'Rodando...',
  done: 'Concluído',
  error: 'Erro',
  cancelled: 'Cancelado',
}

function WrongCases({ results }: { results: CaseResult[] }) {
  const wrong = results.filter((result) => !result.correct)
  if (wrong.length === 0) {
    return <p className="text-sm text-emerald-700">Acertou todos os casos.</p>
  }
  return (
    <ul className="flex flex-col gap-2 text-sm">
      {wrong.map((result) => (
        <li key={result.case_id} className="rounded-md border border-slate-200 p-2">
          <p>
            <strong>{result.case_id}</strong>: esperado <code>{result.expected}</code>, obtido{' '}
            <code>{result.predicted ?? 'nada'}</code>
            {result.error && <span className="text-red-700"> ({result.error})</span>}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {result.output_tokens} tokens em {seconds(result.latency_seconds)}
            {!result.json_found && ' · nenhum JSON encontrado na resposta'}
          </p>
          <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs">
            {result.raw_output || '(resposta vazia)'}
          </pre>
        </li>
      ))}
    </ul>
  )
}

export function ResultsTable({ jobs }: { jobs: JobState[] }) {
  const [openKey, setOpenKey] = useState<string | null>(null)
  if (jobs.length === 0) return null

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Resultados da avaliação</caption>
        <thead className="border-b border-slate-300 text-xs uppercase text-slate-500">
          <tr>
            <th className="py-2 pr-3">Modelo</th>
            <th className="py-2 pr-3">Prompt</th>
            <th className="py-2 pr-3">Acerto</th>
            <th className="py-2 pr-3">Só JSON</th>
            <th className="py-2 pr-3">Latência média</th>
            <th className="py-2 pr-3">Tokens/s</th>
            <th className="py-2 pr-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => {
            const summary = job.run?.summary
            const isOpen = openKey === job.key
            return [
              <tr key={job.key} className="border-b border-slate-100" data-testid={`row-${job.key}`}>
                <td className="py-2 pr-3">
                  {job.model}
                  {job.think && <span className="ml-1 text-xs text-slate-500">(thinking)</span>}
                </td>
                <td className="py-2 pr-3">{job.promptId}</td>
                <td className="py-2 pr-3 font-semibold">
                  {summary ? `${summary.correct}/${summary.total} (${percent(summary.accuracy)})` : '-'}
                </td>
                <td className="py-2 pr-3">{summary ? percent(summary.strict_json_rate) : '-'}</td>
                <td className="py-2 pr-3">{summary ? seconds(summary.mean_latency_seconds) : '-'}</td>
                <td className="py-2 pr-3">
                  {summary
                    ? summary.mean_tokens_per_second.toLocaleString('pt-BR', {
                        maximumFractionDigits: 1,
                      })
                    : '-'}
                </td>
                <td className="py-2 pr-3">
                  {job.status === 'error' ? (
                    <span role="alert" className="text-red-700">
                      {job.error}
                    </span>
                  ) : job.run ? (
                    <button
                      type="button"
                      className="text-slate-900 underline"
                      aria-expanded={isOpen}
                      onClick={() => setOpenKey(isOpen ? null : job.key)}
                    >
                      {isOpen ? 'Ocultar erros' : 'Ver erros'}
                    </button>
                  ) : (
                    STATUS_TEXT[job.status]
                  )}
                </td>
              </tr>,
              isOpen && job.run ? (
                <tr key={`${job.key}-details`}>
                  <td colSpan={7} className="pb-4">
                    <WrongCases results={job.run.results} />
                  </td>
                </tr>
              ) : null,
            ]
          })}
        </tbody>
      </table>
    </div>
  )
}
