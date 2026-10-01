import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { TEST_AI_SETTINGS, apiError, json, mockApi, renderRoute } from '../test/utils'

const NOT_CONFIGURED = {
  configured: false,
  provider: null,
  model: null,
  base_url: null,
  api_key_hint: null,
  updated_at: null,
}

type Body = Record<string, unknown>

/** A settings backend that remembers what was saved. */
function settingsBackend(initial: object = NOT_CONFIGURED, extra = {}) {
  let saved: object = initial
  const requests = mockApi({
    'GET /api/ai-settings': () => json(saved),
    'PUT /api/ai-settings': async (request) => {
      const body = (await request.json()) as Body
      saved = {
        configured: true,
        provider: body.provider,
        model: body.model,
        base_url: body.base_url,
        api_key_hint: String(body.api_key ?? '1234').slice(-4),
        updated_at: '2026-09-29T12:00:00Z',
      }
      return json(saved)
    },
    'DELETE /api/ai-settings': () => {
      saved = NOT_CONFIGURED
      return new Response(null, { status: 204 })
    },
    'POST /api/ai-settings/models': () => json({ models: ['gpt-a', 'gpt-b'] }),
    'POST /api/ai-settings/test': () => json({ reply: 'OK' }),
    ...extra,
  })
  return requests
}

async function bodyOf(requests: Request[], method: string, path: string): Promise<Body> {
  const request = requests.filter((r) => r.method === method && r.url.endsWith(path)).at(-1)!
  return (await request.json()) as Body
}

describe('SettingsPage', () => {
  it('says the AI is off until a key is saved', async () => {
    settingsBackend()

    renderRoute('/settings')

    expect(await screen.findByText(/yapay zekâ özellikleri kapalı/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Kaydet' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Anahtarı sil' })).not.toBeInTheDocument()
  })

  it('saves provider, model and key, then shows only the end of the key', async () => {
    const requests = settingsBackend()
    renderRoute('/settings')

    await userEvent.selectOptions(await screen.findByLabelText('Sağlayıcı'), 'openai')
    await userEvent.type(screen.getByLabelText('API anahtarı'), 'sk-test-5678')
    await userEvent.type(screen.getByLabelText('Model'), 'gpt-a')
    await userEvent.click(screen.getByRole('button', { name: 'Kaydet' }))

    expect(await screen.findByText(/OpenAI \(GPT\) · gpt-a · anahtar ••••5678/)).toBeInTheDocument()
    expect(await bodyOf(requests, 'PUT', '/api/ai-settings')).toEqual({
      provider: 'openai',
      model: 'gpt-a',
      base_url: null,
      api_key: 'sk-test-5678',
    })
    expect(screen.getByLabelText('API anahtarı')).toHaveValue('')
    expect(screen.getByLabelText('API anahtarı')).toHaveAttribute(
      'placeholder',
      expect.stringContaining('••••5678'),
    )
  })

  it('fetches the models the key can use', async () => {
    const requests = settingsBackend()
    renderRoute('/settings')
    await userEvent.selectOptions(await screen.findByLabelText('Sağlayıcı'), 'openai')
    const fetch = screen.getByRole('button', { name: 'Modelleri getir' })
    expect(fetch).toBeDisabled() // no key yet

    await userEvent.type(screen.getByLabelText('API anahtarı'), 'sk-test-5678')
    await userEvent.click(fetch)

    expect(await screen.findByText('2 model bulundu.')).toBeInTheDocument()
    const select = screen.getByRole('combobox', { name: 'Model' })
    expect(select).toHaveValue('gpt-a') // first one chosen
    expect(
      within(select)
        .getAllByRole('option')
        .map((option) => option.textContent),
    ).toEqual(['gpt-a', 'gpt-b', 'Başka bir model yaz…'])
    expect(await bodyOf(requests, 'POST', '/api/ai-settings/models')).toMatchObject({
      provider: 'openai',
      api_key: 'sk-test-5678',
    })

    await userEvent.selectOptions(select, 'gpt-b')
    await userEvent.click(screen.getByRole('button', { name: 'Kaydet' }))

    await screen.findByText(/gpt-b · anahtar ••••5678/)
    expect(await bodyOf(requests, 'PUT', '/api/ai-settings')).toMatchObject({ model: 'gpt-b' })
  })

  it('lets you type a model that is not in the list, and go back to it', async () => {
    settingsBackend()
    renderRoute('/settings')
    await userEvent.selectOptions(await screen.findByLabelText('Sağlayıcı'), 'anthropic')

    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: 'Model' }),
      'Başka bir model yaz…',
    )
    const input = screen.getByRole('textbox', { name: 'Model' })
    await userEvent.clear(input)
    await userEvent.type(input, 'claude-new-model')
    await userEvent.click(screen.getByRole('button', { name: 'Listeden seç' }))

    const select = screen.getByRole('combobox', { name: 'Model' })
    expect(select).toHaveValue('claude-new-model')
    expect(
      within(select).getByRole('option', { name: 'claude-new-model (listede yok)' }),
    ).toBeInTheDocument()
    expect(within(select).getByRole('option', { name: 'claude-sonnet-5' })).toBeInTheDocument()
  })

  it('keeps a saved model that the provider does not list', async () => {
    settingsBackend(
      { ...TEST_AI_SETTINGS, model: 'gemini-old' },
      { 'POST /api/ai-settings/models': () => json({ models: ['gemini-3.8-flash', 'gemini-x'] }) },
    )
    renderRoute('/settings')

    await userEvent.click(await screen.findByRole('button', { name: 'Modelleri getir' }))

    await screen.findByText('2 model bulundu.')
    const select = screen.getByRole('combobox', { name: 'Model' })
    expect(select).toHaveValue('gemini-old')
    expect(
      within(select)
        .getAllByRole('option')
        .map((option) => option.textContent),
    ).toEqual(['gemini-old (listede yok)', 'gemini-3.8-flash', 'gemini-x', 'Başka bir model yaz…'])
  })

  it('tests the connection without saving', async () => {
    const requests = settingsBackend(TEST_AI_SETTINGS)
    renderRoute('/settings')

    await userEvent.click(await screen.findByRole('button', { name: 'Bağlantıyı test et' }))

    expect(await screen.findByText('Bağlantı çalışıyor. Modelin cevabı: „OK“')).toBeInTheDocument()
    // The saved key is used: none is sent.
    expect(await bodyOf(requests, 'POST', '/api/ai-settings/test')).toEqual({
      provider: 'gemini',
      model: 'gemini-3.8-flash',
      base_url: null,
      api_key: null,
    })
    expect(requests.some((request) => request.method === 'PUT')).toBe(false)
  })

  it('shows why the provider rejected the key', async () => {
    settingsBackend(TEST_AI_SETTINGS, {
      'POST /api/ai-settings/test': () => apiError('ai_invalid_key', 502),
    })
    renderRoute('/settings')

    await userEvent.click(await screen.findByRole('button', { name: 'Bağlantıyı test et' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('API anahtarını kabul etmedi')
  })

  it('asks for the base URL of an OpenAI-compatible service', async () => {
    const requests = settingsBackend()
    renderRoute('/settings')

    await userEvent.selectOptions(await screen.findByLabelText('Sağlayıcı'), 'openai_compatible')
    await userEvent.type(
      screen.getByLabelText('Servis adresi (base URL)'),
      'https://api.deepseek.com',
    )
    await userEvent.type(screen.getByLabelText('API anahtarı'), 'sk-ds-0000')
    await userEvent.type(screen.getByLabelText('Model'), 'deepseek-chat')
    await userEvent.click(screen.getByRole('button', { name: 'Kaydet' }))

    await screen.findByText(/deepseek-chat · anahtar ••••0000/)
    expect(await bodyOf(requests, 'PUT', '/api/ai-settings')).toMatchObject({
      provider: 'openai_compatible',
      base_url: 'https://api.deepseek.com',
    })
  })

  it('needs a new key when switching to another provider', async () => {
    settingsBackend(TEST_AI_SETTINGS)
    renderRoute('/settings')
    expect(await screen.findByRole('button', { name: 'Kaydet' })).toBeEnabled() // saved key

    await userEvent.selectOptions(screen.getByLabelText('Sağlayıcı'), 'anthropic')

    expect(screen.getByLabelText('Model')).toHaveValue('claude-sonnet-5')
    expect(screen.getByRole('button', { name: 'Kaydet' })).toBeDisabled()
    expect(screen.getByRole('link', { name: 'console.anthropic.com' })).toHaveAttribute(
      'href',
      'https://console.anthropic.com/settings/keys',
    )
  })

  it('deletes the key after confirmation', async () => {
    settingsBackend(TEST_AI_SETTINGS)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderRoute('/settings')

    await userEvent.click(await screen.findByRole('button', { name: 'Anahtarı sil' }))

    expect(await screen.findByText(/yapay zekâ özellikleri kapalı/)).toBeInTheDocument()
  })

  it('is reached from the header', async () => {
    settingsBackend(TEST_AI_SETTINGS, { 'GET /api/documents': () => json([]) })
    renderRoute('/')

    await userEvent.click(await screen.findByRole('link', { name: /Ayarlar/ }))

    const form = await screen.findByRole('form', { name: /Yapay zekâ ayarları/ })
    expect(within(form).getByText(/Google Gemini · gemini-3.8-flash/)).toBeInTheDocument()
  })
})
