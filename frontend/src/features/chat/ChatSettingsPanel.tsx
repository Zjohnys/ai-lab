import type { ModelInfo } from '../../lib/api'
import type { ChatSettings } from './useChat'

const CONTEXT_SIZES = [2048, 4096, 8192]

interface Props {
  settings: ChatSettings
  models: ModelInfo[]
  modelsError: string | null
  disabled: boolean
  onChange: (settings: ChatSettings) => void
}

function describe(model: ModelInfo): string {
  const sizeGb = (model.size_bytes / 1024 ** 3).toLocaleString('pt-BR', { maximumFractionDigits: 1 })
  const details = [model.parameter_size, model.quantization, `${sizeGb} GB`].filter(Boolean)
  return `${model.name} (${details.join(', ')})`
}

export function ChatSettingsPanel({ settings, models, modelsError, disabled, onChange }: Props) {
  const labelClass = 'flex flex-col gap-1 text-sm font-medium text-slate-700'
  const fieldClass = 'rounded-md border border-slate-300 px-2 py-1 font-normal disabled:opacity-60'

  return (
    <fieldset disabled={disabled} className="flex flex-col gap-4">
      <legend className="mb-2 text-base font-semibold">Parâmetros</legend>

      <label className={labelClass}>
        Modelo
        <select
          className={fieldClass}
          value={settings.model}
          onChange={(event) => onChange({ ...settings, model: event.target.value })}
        >
          {models.length === 0 && <option value="">Padrão do servidor</option>}
          {models.map((model) => (
            <option key={model.name} value={model.name}>
              {describe(model)}
            </option>
          ))}
        </select>
        {modelsError && (
          <span role="alert" className="font-normal text-red-700">
            {modelsError}
          </span>
        )}
      </label>

      <label className={labelClass}>
        System prompt
        <textarea
          className={fieldClass}
          rows={4}
          placeholder="Ex.: Você é um analista de suporte. Responda em no máximo 3 linhas."
          value={settings.systemPrompt}
          onChange={(event) => onChange({ ...settings, systemPrompt: event.target.value })}
        />
        <span className="font-normal text-slate-500">
          Instrução fixa, enviada antes de toda a conversa.
        </span>
      </label>

      <label className={labelClass}>
        Temperatura: {settings.temperature.toLocaleString('pt-BR', { minimumFractionDigits: 1 })}
        <input
          type="range"
          min={0}
          max={2}
          step={0.1}
          value={settings.temperature}
          onChange={(event) => onChange({ ...settings, temperature: Number(event.target.value) })}
        />
        <span className="font-normal text-slate-500">
          0 repete a resposta mais provável; valores altos variam mais e erram mais.
        </span>
      </label>

      <label className={labelClass}>
        Janela de contexto (tokens)
        <select
          className={fieldClass}
          value={settings.numCtx}
          onChange={(event) => onChange({ ...settings, numCtx: Number(event.target.value) })}
        >
          {CONTEXT_SIZES.map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
        <span className="font-normal text-slate-500">
          Mudar o tamanho recarrega o modelo. Acima de 8192 não cabe em 8 GB de VRAM.
        </span>
      </label>

      <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
        <input
          type="checkbox"
          checked={settings.think}
          onChange={(event) => onChange({ ...settings, think: event.target.checked })}
        />
        Thinking (raciocínio antes da resposta)
      </label>
    </fieldset>
  )
}
