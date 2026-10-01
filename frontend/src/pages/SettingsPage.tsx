import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'

import {
  useAISettings,
  useDeleteAISettings,
  useListModels,
  useSaveAISettings,
  useTestAI,
  type AIProviderKind,
  type AISettings,
} from '../api/aiSettings'
import { errorMessage } from '../api/client'
import { COMPATIBLE_EXAMPLES, PROVIDERS, PROVIDER_ORDER } from '../lib/providers'

// The dropdown entry that switches to typing a model name.
const TYPE_MODEL = '__type_model__'

export function SettingsPage() {
  const settings = useAISettings()

  if (settings.isError) {
    return (
      <p className="error" role="alert">
        {errorMessage(settings.error)}
      </p>
    )
  }
  if (!settings.data) return <p className="muted">Yükleniyor…</p>
  // Keyed so the form starts again from the saved values after saving or deleting.
  return (
    <AISettingsForm
      key={`${settings.data.provider}-${settings.data.updated_at}`}
      saved={settings.data}
    />
  )
}

function AISettingsForm({ saved }: { saved: AISettings }) {
  const [provider, setProvider] = useState<AIProviderKind>(saved.provider ?? 'gemini')
  const [model, setModel] = useState(saved.model ?? PROVIDERS.gemini.suggestedModels[0] ?? '')
  const [baseUrl, setBaseUrl] = useState(saved.base_url ?? '')
  const [apiKey, setApiKey] = useState('')
  const [models, setModels] = useState<string[] | null>(null)
  // Typing a model name instead of picking one from the list.
  const [typing, setTyping] = useState(false)
  const save = useSaveAISettings()
  const remove = useDeleteAISettings()
  const listModels = useListModels()
  const test = useTestAI()

  // The saved key can be reused only for the same provider (and URL).
  const savedKeyUsable =
    saved.configured &&
    saved.provider === provider &&
    (provider !== 'openai_compatible' ||
      (saved.base_url ?? '') === baseUrl.trim().replace(/\/+$/, ''))
  const hasKey = apiKey.trim() !== '' || savedKeyUsable
  const draft = {
    provider,
    model: model.trim(),
    base_url: provider === 'openai_compatible' ? baseUrl.trim() : null,
    api_key: apiKey.trim() || null,
  }
  const info = PROVIDERS[provider]
  const listed = models ?? info.suggestedModels
  // The current model stays choosable even when the provider did not list it.
  const unlisted = model.trim() !== '' && !listed.includes(model)
  const choices = unlisted && listed.length > 0 ? [model, ...listed] : listed
  const showSelect = choices.length > 0 && !typing

  function chooseProvider(next: AIProviderKind) {
    setProvider(next)
    setModels(null)
    setTyping(false)
    listModels.reset()
    test.reset()
    setModel(
      next === saved.provider ? (saved.model ?? '') : (PROVIDERS[next].suggestedModels[0] ?? ''),
    )
  }

  function fetchModels() {
    listModels.mutate(draft, {
      onSuccess: (found) => {
        setModels(found)
        setTyping(found.length === 0)
        if (!model.trim() && found.length > 0) setModel(found[0])
      },
    })
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    save.mutate(draft)
  }

  function forget() {
    if (
      window.confirm(
        'API anahtarın silinsin mi? Yapay zekâ özellikleri yeni bir anahtar girene kadar kapanır.',
      )
    )
      remove.mutate()
  }

  const error = save.error ?? remove.error

  return (
    <div className="stack">
      <Link to="/">← Belgelerim</Link>
      <form className="card settings" onSubmit={submit} aria-labelledby="settings-title">
        <h2 id="settings-title">⚙️ Yapay zekâ ayarları</h2>
        <p className="muted">
          PDF analizi, açık uçlu cevapların değerlendirilmesi ve sohbet senin seçtiğin yapay
          zekâyla, senin API anahtarınla çalışır. Anahtar sunucuda şifreli saklanır ve bir daha
          gösterilmez; kullanım ücreti sağlayıcıdaki hesabına yansır.
        </p>
        <p className={saved.configured ? 'success' : 'error'} role="status">
          {saved.configured
            ? `Şu an: ${PROVIDERS[saved.provider!].label} · ${saved.model} · anahtar ••••${saved.api_key_hint}`
            : 'Henüz ayarlanmadı: yapay zekâ özellikleri kapalı.'}
        </p>

        <label className="login__field">
          Sağlayıcı
          <select
            value={provider}
            onChange={(event) => chooseProvider(event.target.value as AIProviderKind)}
          >
            {PROVIDER_ORDER.map((kind) => (
              <option key={kind} value={kind}>
                {PROVIDERS[kind].label}
              </option>
            ))}
          </select>
        </label>

        {provider === 'openai_compatible' && (
          <label className="login__field">
            Servis adresi (base URL)
            <input
              type="url"
              value={baseUrl}
              onChange={(event) => setBaseUrl(event.target.value)}
              placeholder="https://api.deepseek.com"
              list="compatible-urls"
              autoComplete="off"
              spellCheck={false}
              required
            />
            <datalist id="compatible-urls">
              {COMPATIBLE_EXAMPLES.map((url) => (
                <option key={url} value={url} />
              ))}
            </datalist>
          </label>
        )}

        <div className="login__field">
          <label htmlFor="ai-key">API anahtarı</label>
          <input
            id="ai-key"
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder={
              savedKeyUsable
                ? `Kayıtlı: ••••${saved.api_key_hint} (değiştirmek için yenisini gir)`
                : 'Anahtarını buraya yapıştır'
            }
            autoComplete="off"
            spellCheck={false}
            aria-describedby={info.keyUrl ? 'ai-key-hint' : undefined}
          />
          {info.keyUrl && (
            <span id="ai-key-hint" className="settings__hint">
              Anahtar oluştur:{' '}
              <a href={info.keyUrl} target="_blank" rel="noreferrer">
                {new URL(info.keyUrl).host}
              </a>
            </span>
          )}
        </div>

        <div className="login__field">
          <label htmlFor="ai-model">Model</label>
          <div className="settings__model">
            {showSelect ? (
              <select
                id="ai-model"
                value={model}
                onChange={(event) =>
                  event.target.value === TYPE_MODEL ? setTyping(true) : setModel(event.target.value)
                }
              >
                {choices.map((name) => (
                  <option key={name} value={name}>
                    {name === model && unlisted ? `${name} (listede yok)` : name}
                  </option>
                ))}
                <option value={TYPE_MODEL}>Başka bir model yaz…</option>
              </select>
            ) : (
              <input
                id="ai-model"
                type="text"
                value={model}
                onChange={(event) => setModel(event.target.value)}
                placeholder="Model adını yaz ya da modelleri getir"
                autoComplete="off"
                spellCheck={false}
              />
            )}
            {typing && choices.length > 0 && (
              <button type="button" className="secondary" onClick={() => setTyping(false)}>
                Listeden seç
              </button>
            )}
            <button
              type="button"
              className="secondary"
              onClick={fetchModels}
              disabled={!hasKey || listModels.isPending}
            >
              {listModels.isPending ? 'Getiriliyor…' : 'Modelleri getir'}
            </button>
          </div>
          {models && (
            <span className="settings__hint">
              {models.length > 0 ? `${models.length} model bulundu.` : 'Hiç model bulunamadı.'}
            </span>
          )}
          {listModels.isError && (
            <p className="error" role="alert">
              {errorMessage(listModels.error)}
            </p>
          )}
        </div>

        <div className="chapter__actions">
          <button type="submit" disabled={!model.trim() || !hasKey || save.isPending}>
            {save.isPending ? 'Kaydediliyor…' : 'Kaydet'}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => test.mutate(draft)}
            disabled={!model.trim() || !hasKey || test.isPending}
          >
            {test.isPending ? 'Deneniyor…' : 'Bağlantıyı test et'}
          </button>
          {saved.configured && (
            <button
              type="button"
              className="secondary"
              onClick={forget}
              disabled={remove.isPending}
            >
              Anahtarı sil
            </button>
          )}
        </div>

        {test.isSuccess && (
          <p className="success" role="status">
            Bağlantı çalışıyor. Modelin cevabı: „{test.data}“
          </p>
        )}
        {test.isError && (
          <p className="error" role="alert">
            {errorMessage(test.error)}
          </p>
        )}
        {save.isSuccess && (
          <p className="success" role="status">
            Kaydedildi.
          </p>
        )}
        {error && (
          <p className="error" role="alert">
            {errorMessage(error)}
          </p>
        )}
      </form>
    </div>
  )
}
