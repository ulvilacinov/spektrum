import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { apiError, json, mockApi, renderRoute } from '../test/utils'
import { chapterProgress, document, progress, session, sessionItem } from '../test/factories'

const CHAPTERS = [
  chapterProgress(),
  chapterProgress({
    chapter_id: 22,
    chapter_number: 2,
    title: 'Kapitel 2',
    total: 54,
    new: 44,
    learning: 7,
    weak: 3,
    can_start_new_batch: false,
    can_review: true,
  }),
  chapterProgress({
    chapter_id: 23,
    chapter_number: 3,
    title: 'Kapitel 3',
    total: 52,
    new: 0,
    mastered: 52,
    mastery_ratio: 1,
    can_start_new_batch: false,
  }),
]

function backend(extra = {}) {
  return mockApi({
    'GET /api/documents/1': () => json(document()),
    'GET /api/progress': () => json(progress(CHAPTERS)),
    ...extra,
  })
}

describe('DocumentPage', () => {
  it('shows every chapter with its progress', async () => {
    backend()

    renderRoute('/documents/1')

    expect(await screen.findByRole('heading', { name: 'spektrum_b1.pdf' })).toBeInTheDocument()
    const [first, second, third] = screen.getAllByRole('listitem')
    expect(within(first).getByText('64 kelime · %0 öğrenildi')).toBeInTheDocument()
    expect(within(second).getByText('Öğreniliyor: 7')).toBeInTheDocument()
    expect(within(second).getByText('Zayıf: 3')).toBeInTheDocument()
    expect(within(third).getByText(/Bölüm tamamlandı/)).toBeInTheDocument()
  })

  it('enables only the actions the chapter allows', async () => {
    backend()
    renderRoute('/documents/1')

    const [first, second, third] = await screen.findAllByRole('listitem')
    expect(within(first).getByRole('button', { name: 'Yeni 10 kelime öğren' })).toBeEnabled()
    expect(within(first).getByRole('button', { name: 'Tekrar et (0)' })).toBeDisabled()
    expect(within(second).getByRole('button', { name: 'Yeni 10 kelime öğren' })).toBeDisabled()
    expect(within(second).getByRole('button', { name: 'Tekrar et (10)' })).toBeEnabled()
    expect(within(second).getByText(/önce öğrendiğin kelimeleri tekrar et/)).toBeInTheDocument()
    expect(
      within(third)
        .getAllByRole('button')
        .every((button) => button.hasAttribute('disabled')),
    ).toBe(true)
  })

  it('starts a new batch with the chosen size and opens the learning screen', async () => {
    const requests = backend({
      'POST /api/learning-sessions': () => json(session({ batch_size: 5 }), 201),
      'GET /api/learning-sessions/7': () => json(session({ batch_size: 5 })),
      'GET /api/learning-sessions/7/items': () => json([sessionItem(1), sessionItem(2)]),
    })
    renderRoute('/documents/1')

    await userEvent.selectOptions(await screen.findByLabelText(/kaç kelime/), '5')
    const [first] = screen.getAllByRole('listitem')
    await userEvent.click(within(first).getByRole('button', { name: 'Yeni 5 kelime öğren' }))

    expect(await screen.findByRole('heading', { name: 'Kapitel 1: 2 kelime' })).toBeInTheDocument()
    const start = requests.find((request) => request.method === 'POST')!
    expect(await start.json()).toEqual({ chapter_id: 21, batch_size: 5, mode: 'new' })
  })

  it('starts a review session', async () => {
    const requests = backend({
      'POST /api/learning-sessions': () => json(session({ mode: 'review' }), 201),
      'GET /api/learning-sessions/7': () => json(session({ mode: 'review' })),
      'GET /api/learning-sessions/7/items': () => json([sessionItem(1)]),
    })
    renderRoute('/documents/1')

    const second = (await screen.findAllByRole('listitem'))[1]
    await userEvent.click(within(second).getByRole('button', { name: 'Tekrar et (10)' }))

    expect(await screen.findByText('Tekrar')).toBeInTheDocument()
    const start = requests.find((request) => request.method === 'POST')!
    expect(await start.json()).toMatchObject({ chapter_id: 22, mode: 'review' })
  })

  it('shows why a batch could not start', async () => {
    backend({ 'POST /api/learning-sessions': () => apiError('batch_locked', 409) })
    renderRoute('/documents/1')

    const [first] = await screen.findAllByRole('listitem')
    await userEvent.click(within(first).getByRole('button', { name: 'Yeni 10 kelime öğren' }))

    expect(await within(first).findByRole('alert')).toHaveTextContent('tekrar et')
  })

  it('tells when the document has not been analyzed yet', async () => {
    mockApi({
      'GET /api/documents/1': () => json(document({ status: 'uploaded' })),
      'GET /api/progress': () => json(progress([])),
    })

    renderRoute('/documents/1')

    expect(await screen.findByText(/analiz etmen gerekiyor/)).toBeInTheDocument()
  })

  it('handles an unknown document', async () => {
    mockApi({
      'GET /api/documents/9': () => apiError('not_found', 404),
      'GET /api/progress': () => apiError('not_found', 404),
    })

    renderRoute('/documents/9')

    expect(await screen.findByRole('alert')).toHaveTextContent('bulunamadı')
  })

  it('shows the not-found page for a malformed id', async () => {
    renderRoute('/documents/abc')

    expect(await screen.findByRole('heading', { name: 'Sayfa bulunamadı' })).toBeInTheDocument()
  })
})
