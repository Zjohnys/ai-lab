import { useEffect, useState, type FormEvent } from 'react'
import { ApiError, fetchModels, type ModelInfo } from '../../lib/api'
import { fetchDatasets, type DatasetSummary } from '../../lib/evals'
import { ResultsTable } from './ResultsTable'
import { useEvalQueue, type EvalJob } from './useEvalQueue'

interface ModelChoice {
  selected: boolean
  think: boolean
}

function errorText(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

export function EvalLabPage() {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([])
  const [models, setModels] = useState<ModelInfo[]>([])
  const [datasetName, setDatasetName] = useState('')
  const [promptIds, setPromptIds] = useState<string[]>([])
  const [choices, setChoices] = useState<Record<string, ModelChoice>>({})
  const [loadError, setLoadError] = useState<string | null>(null)
  const { jobs, isRunning, start, cancel } = useEvalQueue()

  useEffect(() => {
    let cancelled = false
    Promise.all([fetchDatasets(), fetchModels()])
      .then(([datasetList, modelList]) => {
        if (cancelled) return
        setDatasets(datasetList)
        setModels(modelList.models)
        const first = datasetList[0]
        if (first) {
          setDatasetName(first.name)
          setPromptIds(first.prompts.map((prompt) => prompt.id))
        }
        setChoices(
          Object.fromEntries(
            modelList.models.map((model) => [
              model.name,
              { selected: model.name === modelList.default_chat_model, think: false },
            ]),
          ),
        )
      })
      .catch((error: unknown) => {
        if (!cancelled) setLoadError(errorText(error, 'Não foi possível carregar os dados.'))
      })
    return () => {
      cancelled = true
    }
  }, [])

  const dataset = datasets.find((item) => item.name === datasetName)
  const selectedModels = models.filter((model) => choices[model.name]?.selected)
  const jobsToRun: EvalJob[] = selectedModels.flatMap((model) =>
    promptIds.map((promptId) => ({
      dataset: datasetName,
      promptId,
      model: model.name,
      think: choices[model.name]?.think ?? false,
    })),
  )

  function chooseDataset(name: string) {
    setDatasetName(name)
    const next = datasets.find((item) => item.name === name)
    setPromptIds(next ? next.prompts.map((prompt) => prompt.id) : [])
  }

  function togglePrompt(id: string) {
    setPromptIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    )
  }

  function updateChoice(name: string, change: Partial<ModelChoice>) {
    setChoices((current) => {
      const previous = current[name] ?? { selected: false, think: false }
      return { ...current, [name]: { ...previous, ...change } }
    })
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    void start(jobsToRun)
  }

  if (loadError) {
    return (
      <p role="alert" className="text-red-700">
        {loadError}
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={submit} className="grid gap-6 md:grid-cols-3">
        <fieldset disabled={isRunning} className="flex flex-col gap-2">
          <legend className="mb-1 font-semibold">Dataset</legend>
          <select
            aria-label="Dataset"
            className="rounded-md border border-slate-300 px-2 py-1"
            value={datasetName}
            onChange={(event) => chooseDataset(event.target.value)}
          >
            {datasets.map((item) => (
              <option key={item.name} value={item.name}>
                {item.name} ({item.cases} casos)
              </option>
            ))}
          </select>
          {dataset && <p className="text-sm text-slate-500">{dataset.description}</p>}
        </fieldset>

        <fieldset disabled={isRunning} className="flex flex-col gap-2">
          <legend className="mb-1 font-semibold">Versões de prompt</legend>
          {dataset?.prompts.map((prompt) => (
            <label key={prompt.id} className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-1"
                checked={promptIds.includes(prompt.id)}
                onChange={() => togglePrompt(prompt.id)}
              />
              <span>
                <strong>{prompt.id}</strong>
                <span className="block text-slate-500">{prompt.description}</span>
              </span>
            </label>
          ))}
        </fieldset>

        <fieldset disabled={isRunning} className="flex flex-col gap-2">
          <legend className="mb-1 font-semibold">Modelos</legend>
          {models.map((model) => (
            <div key={model.name} className="flex flex-col text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={choices[model.name]?.selected ?? false}
                  onChange={(event) => updateChoice(model.name, { selected: event.target.checked })}
                />
                <strong>{model.name}</strong>
              </label>
              <label className="ml-6 flex items-center gap-2 text-slate-600">
                <input
                  type="checkbox"
                  aria-label={`Thinking em ${model.name}`}
                  checked={choices[model.name]?.think ?? false}
                  onChange={(event) => updateChoice(model.name, { think: event.target.checked })}
                />
                thinking
              </label>
            </div>
          ))}
          <p className="text-xs text-slate-500">
            Modelos só-thinking, como o qwen3:4b instalado, precisam do thinking ligado. Com ele
            cada caso leva segundos em vez de frações de segundo.
          </p>
        </fieldset>

        <div className="flex items-center gap-3 md:col-span-3">
          {isRunning ? (
            <button
              type="button"
              onClick={cancel}
              className="rounded-md bg-red-700 px-4 py-2 font-medium text-white"
            >
              Cancelar
            </button>
          ) : (
            <button
              type="submit"
              disabled={jobsToRun.length === 0}
              className="rounded-md bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-40"
            >
              Rodar {jobsToRun.length} {jobsToRun.length === 1 ? 'avaliação' : 'avaliações'}
            </button>
          )}
          <p className="text-sm text-slate-500">
            {dataset
              ? `${jobsToRun.length * dataset.cases} chamadas ao modelo, uma por vez.`
              : ''}
          </p>
        </div>
      </form>

      <ResultsTable jobs={jobs} />
    </div>
  )
}
