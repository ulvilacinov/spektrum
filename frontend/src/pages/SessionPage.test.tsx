import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { apiError, json, mockApi, renderRoute } from '../test/utils'
import { session, sessionItem } from '../test/factories'

describe('SessionPage', () => {
  it('shows every word of the batch with meaning, grammar and example', async () => {
    mockApi({
      'GET /api/learning-sessions/7': () => json(session()),
      'GET /api/learning-sessions/7/items': () =>
        json([
          sessionItem(1),
          sessionItem(2, {
            german: 'die Veranstaltung',
            turkish: 'etkinlik',
            item_type: 'noun',
            article: 'die',
            base_verb: null,
            prateritum: null,
            perfekt: null,
            preposition: null,
            grammatical_case: null,
            example_german: null,
            example_turkish: null,
            source_page: null,
          }),
        ]),
    })

    renderRoute('/sessions/7')

    expect(await screen.findByRole('heading', { name: 'Kapitel 1: 2 kelime' })).toBeInTheDocument()
    expect(screen.getByText('Yeni kelimeler')).toBeInTheDocument()
    const [first, second] = screen.getAllByRole('listitem')
    expect(within(first).getByRole('heading', { name: 'im Stau stehen' })).toHaveAttribute(
      'lang',
      'de',
    )
    expect(within(first).getByText('Trafikte kalmak/beklemek')).toBeInTheDocument()
    expect(within(first).getByText('hat gestanden')).toBeInTheDocument()
    expect(within(first).getByText('in + Dativ')).toBeInTheDocument()
    expect(within(first).getByText('Morgens stehe ich oft im Stau.')).toBeInTheDocument()
    expect(within(first).getByText('PDF sayfa 1')).toBeInTheDocument()
    expect(within(first).getByText('Öğreniliyor')).toBeInTheDocument()
    // Optional fields are simply left out.
    expect(within(second).getByText('(isim)')).toBeInTheDocument()
    expect(within(second).queryByText('Perfekt')).not.toBeInTheDocument()
    expect(within(second).queryByText(/PDF sayfa/)).not.toBeInTheDocument()
  })

  it('links back to the chapters of the document', async () => {
    mockApi({
      'GET /api/learning-sessions/7': () => json(session({ document_id: 3 })),
      'GET /api/learning-sessions/7/items': () => json([sessionItem(1)]),
    })

    renderRoute('/sessions/7')

    expect(await screen.findByRole('link', { name: '← Bölümler' })).toHaveAttribute(
      'href',
      '/documents/3',
    )
  })

  it('handles a missing session', async () => {
    mockApi({
      'GET /api/learning-sessions/99': () => apiError('not_found', 404),
      'GET /api/learning-sessions/99/items': () => apiError('not_found', 404),
    })

    renderRoute('/sessions/99')

    expect(await screen.findByRole('alert')).toHaveTextContent('bulunamadı')
  })
})
