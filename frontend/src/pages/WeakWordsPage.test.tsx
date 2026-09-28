import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import {
  chapterProgress,
  document,
  progress,
  session,
  sessionItem,
  weakWord,
} from '../test/factories'
import { apiError, json, mockApi, renderRoute } from '../test/utils'

const CHAPTERS = [
  chapterProgress({ new: 54, learning: 8, weak: 2, can_start_new_batch: false, can_review: true }),
  chapterProgress({ chapter_id: 22, chapter_number: 2, title: 'Kapitel 2' }),
  chapterProgress({
    chapter_id: 23,
    chapter_number: 3,
    title: 'Kapitel 3',
    new: 63,
    weak: 1,
    can_start_new_batch: false,
    can_review: true,
  }),
]

// The backend orders by due date, not by chapter.
const WEAK = [
  weakWord(3, { chapter_id: 23 }),
  weakWord(
    1,
    {},
    {
      user_answer: 'Lebensmittel',
      expected_answer: 'Lebensmittel einkaufen',
      corrected_answer: 'Lebensmittel einkaufen',
      feedback: "'einkaufen' fiilini de eklemelisin.",
      error_type: 'vocabulary_usage',
    },
  ),
  weakWord(2, {}, null),
]

function backend(extra = {}) {
  return mockApi({
    'GET /api/documents/1': () => json(document()),
    'GET /api/progress': () => json(progress(CHAPTERS)),
    'GET /api/review/weak': () => json(WEAK),
    ...extra,
  })
}

describe('WeakWordsPage', () => {
  it('groups the weak words by chapter in reading order', async () => {
    const requests = backend()

    renderRoute('/documents/1/weak')

    const chapters = await screen.findAllByRole('heading', { level: 3, name: /Kapitel/ })
    expect(chapters.map((heading) => heading.textContent)).toEqual([
      'Kapitel 1 (2)',
      'Kapitel 3 (1)',
    ])
    const first = screen.getByRole('region', { name: 'Kapitel 1 (2)' })
    expect(within(first).getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByText('spektrum_b1.pdf · 3 zayıf kelime')).toBeInTheDocument()
    const weak = requests.find((request) => request.url.includes('/api/review/weak'))!
    expect(new URL(weak.url).searchParams.get('document_id')).toBe('1')
  })

  it('shows the latest mistake with its Turkish explanation', async () => {
    backend()

    renderRoute('/documents/1/weak')

    const card = (await screen.findByRole('heading', { name: 'Wort1' })).closest('li')!
    expect(within(card).getByText(/kelime1/, { selector: '.word__turkish' })).toBeInTheDocument()
    expect(within(card).getByText(/Son hata · Türkçe → Almanca/)).toBeInTheDocument()
    expect(within(card).getByText('Lebensmittel')).toBeInTheDocument()
    expect(within(card).getByText('Lebensmittel einkaufen')).toBeInTheDocument()
    expect(within(card).getByText("'einkaufen' fiilini de eklemelisin.")).toBeInTheDocument()
    expect(within(card).getByText('Hata türü: Kelime kullanımı')).toBeInTheDocument()
    expect(within(card).getByText('1 yanlış · 1 doğru')).toBeInTheDocument()

    const withoutMistake = screen.getByRole('heading', { name: 'Wort2' }).closest('li')!
    expect(within(withoutMistake).getByText(/kayıtlı bir hata yok/)).toBeInTheDocument()
  })

  it('starts a review of a chapter and opens the learning screen', async () => {
    const requests = backend({
      'POST /api/learning-sessions': () => json(session({ id: 8, mode: 'review' }), 201),
      'GET /api/learning-sessions/8': () => json(session({ id: 8, mode: 'review' })),
      'GET /api/learning-sessions/8/items': () => json([sessionItem(1), sessionItem(2)]),
    })
    renderRoute('/documents/1/weak')

    const first = await screen.findByRole('region', { name: 'Kapitel 1 (2)' })
    await userEvent.click(within(first).getByRole('button', { name: 'Bu bölümü tekrar et' }))

    expect(await screen.findByText('Tekrar')).toBeInTheDocument()
    const start = requests.find((request) => request.method === 'POST')!
    expect(await start.json()).toEqual({ chapter_id: 21, batch_size: 2, mode: 'review' })
  })

  it('shows why a review could not start', async () => {
    backend({ 'POST /api/learning-sessions': () => apiError('nothing_to_review', 409) })
    renderRoute('/documents/1/weak')

    const first = await screen.findByRole('region', { name: 'Kapitel 1 (2)' })
    await userEvent.click(within(first).getByRole('button', { name: 'Bu bölümü tekrar et' }))

    expect(await within(first).findByRole('alert')).toHaveTextContent('tekrar edilecek kelime yok')
  })

  it('congratulates when nothing is weak', async () => {
    mockApi({
      'GET /api/documents/1': () => json(document()),
      'GET /api/progress': () => json(progress([chapterProgress()])),
      'GET /api/review/weak': () => json([]),
    })

    renderRoute('/documents/1/weak')

    expect(await screen.findByText('Hiç zayıf kelimen yok. Harika!')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('handles an unknown document', async () => {
    mockApi({
      'GET /api/documents/9': () => apiError('not_found', 404),
      'GET /api/progress': () => apiError('not_found', 404),
      'GET /api/review/weak': () => apiError('not_found', 404),
    })

    renderRoute('/documents/9/weak')

    expect(await screen.findByRole('alert')).toHaveTextContent('bulunamadı')
  })

  it('is reached from the document page', async () => {
    backend()
    renderRoute('/documents/1')

    await userEvent.click(await screen.findByRole('link', { name: /Zayıf kelimelerim \(3\)/ }))

    expect(await screen.findByRole('heading', { name: 'Zayıf kelimeler' })).toBeInTheDocument()
  })
})
