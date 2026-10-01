import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { apiError, json, mockApi, renderRoute } from '../test/utils'

type Reply = (messages: { role: string; content: string }[]) => Response

/** Documents page plus a fake /api/chat; ``reply`` decides each answer. */
function chatBackend(reply: Reply = () => json({ reply: 'Cevap' })) {
  return mockApi({
    'GET /api/documents': () => json([]),
    'POST /api/chat': async (request) => {
      const body = (await request.json()) as { messages: { role: string; content: string }[] }
      return reply(body.messages)
    },
  })
}

async function openChat() {
  renderRoute('/')
  await userEvent.click(await screen.findByRole('button', { name: /Sor/ }))
  return screen.getByRole('complementary', { name: 'Yapay zekâya sor' })
}

describe('ChatPanel', () => {
  it('answers a question and formats the reply', async () => {
    const requests = chatBackend(() =>
      json({ reply: '**der Termin**: randevu\n- Çoğulu: die Termine\n- Ich habe einen Termin.' }),
    )
    const panel = await openChat()

    await userEvent.type(within(panel).getByLabelText('Sorun'), 'Termin der mi?')
    await userEvent.click(within(panel).getByRole('button', { name: 'Gönder' }))

    expect(await within(panel).findByText('der Termin')).toContainHTML('der Termin')
    expect(within(panel).getByText('der Termin').tagName).toBe('STRONG')
    expect(within(panel).getAllByRole('listitem')).toHaveLength(2)
    expect(within(panel).getByText('Termin der mi?')).toBeInTheDocument()
    const sent = requests.find((request) => request.url.endsWith('/api/chat'))!
    expect(await sent.json()).toEqual({ messages: [{ role: 'user', content: 'Termin der mi?' }] })
    expect(within(panel).getByLabelText('Sorun')).toHaveValue('')
  })

  it('sends the conversation so far with every question, and Enter sends', async () => {
    const seen: number[] = []
    chatBackend((messages) => {
      seen.push(messages.length)
      return json({ reply: `Cevap ${seen.length}` })
    })
    const panel = await openChat()
    const input = within(panel).getByLabelText('Sorun')

    await userEvent.type(input, 'Birinci{Enter}')
    await within(panel).findByText('Cevap 1')
    await userEvent.type(input, 'İkinci{Enter}')
    await within(panel).findByText('Cevap 2')

    expect(seen).toEqual([1, 3])
  })

  it('starts with suggestions that can be asked with one click', async () => {
    chatBackend((messages) => json({ reply: `Sorduğun: ${messages[0].content}` }))
    const panel = await openChat()

    await userEvent.click(within(panel).getByRole('button', { name: /Termin/ }))

    expect(await within(panel).findByText(/Sorduğun: „Termin“/)).toBeInTheDocument()
    expect(within(panel).queryByRole('button', { name: /weil/ })).not.toBeInTheDocument()
  })

  it('points to the settings when no AI is set up', async () => {
    mockApi({
      'GET /api/documents': () => json([]),
      'GET /api/ai-settings': () =>
        json({
          configured: false,
          provider: null,
          model: null,
          base_url: null,
          api_key_hint: null,
          updated_at: null,
        }),
    })
    const panel = await openChat()

    const notice = await within(panel).findByRole('status')
    expect(notice).toHaveTextContent('yapay zekâ sağlayıcını ve API anahtarını gir')
    expect(within(notice).getByRole('link', { name: 'Ayarlar' })).toHaveAttribute(
      'href',
      '/settings',
    )
    expect(within(panel).queryByRole('button', { name: /Termin/ })).not.toBeInTheDocument()
  })

  it('keeps the question after an AI failure so it can be retried', async () => {
    let fail = true
    chatBackend(() => {
      if (fail) {
        fail = false
        return apiError('ai_provider_error', 502)
      }
      return json({ reply: 'Şimdi oldu' })
    })
    const panel = await openChat()

    await userEvent.type(within(panel).getByLabelText('Sorun'), 'Hallo{Enter}')

    expect(await within(panel).findByRole('alert')).toHaveTextContent('ulaşılamadı')
    expect(within(panel).getByText('Hallo')).toBeInTheDocument()

    await userEvent.click(within(panel).getByRole('button', { name: 'Tekrar dene' }))

    expect(await within(panel).findByText('Şimdi oldu')).toBeInTheDocument()
    expect(within(panel).queryByRole('alert')).not.toBeInTheDocument()
  })

  it('keeps the conversation when the panel is closed and clears it on request', async () => {
    chatBackend()
    const panel = await openChat()
    await userEvent.type(within(panel).getByLabelText('Sorun'), 'Soru{Enter}')
    await within(panel).findByText('Cevap')

    await userEvent.click(within(panel).getByRole('button', { name: 'Sohbeti kapat' }))
    await userEvent.click(screen.getByRole('button', { name: /Sor/ }))
    const reopened = screen.getByRole('complementary', { name: 'Yapay zekâya sor' })
    expect(within(reopened).getByText('Cevap')).toBeInTheDocument()

    await userEvent.click(within(reopened).getByRole('button', { name: 'Yeni sohbet' }))

    expect(within(reopened).queryByText('Cevap')).not.toBeInTheDocument()
    expect(within(reopened).getAllByRole('button', { name: /\?$/ }).length).toBeGreaterThan(0)
  })
})
