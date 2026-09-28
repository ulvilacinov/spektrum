import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { QuizQuestion } from '../api/quiz'
import { answered, question, session, sessionItem } from '../test/factories'
import { apiError, json, mockApi, renderRoute } from '../test/utils'

const EXPECTED: Record<number, string> = { 1: 'Wort1', 2: 'Wort2' }

/**
 * A stateful fake backend for session 7 with two questions. ``answer`` decides the response
 * for each submission (default: correct iff it equals the expected answer).
 */
function quizBackend(
  questions: QuizQuestion[] = [question(1), question(2)],
  answer?: (id: number, text: string) => Response | undefined,
) {
  const state = [...questions]
  const requests = mockApi({
    'GET /api/learning-sessions/7': () => json(session({ item_count: state.length })),
    'POST /api/learning-sessions/7/quiz': () =>
      json({ learning_session_id: 7, question_count: state.length, questions: state }, 200),
    'POST /api/quiz/1/answer': (request) => submit(1, request),
    'POST /api/quiz/2/answer': (request) => submit(2, request),
    'POST /api/learning-sessions': () => json(session({ id: 8, mode: 'review' }), 201),
    'GET /api/learning-sessions/8': () => json(session({ id: 8, mode: 'review' })),
    'GET /api/learning-sessions/8/items': () => json([sessionItem(2)]),
    'GET /api/learning-sessions/7/items': () => json([sessionItem(1), sessionItem(2)]),
  })

  async function submit(id: number, request: Request) {
    const text = ((await request.json()) as { answer: string }).answer
    const custom = answer?.(id, text)
    if (custom) return custom
    const index = state.findIndex((item) => item.id === id)
    state[index] = answered(state[index], text, EXPECTED[id])
    const correct = state[index].is_correct
    return json({
      question: state[index],
      vocabulary_status: correct ? 'learning' : 'weak',
      learning_session: session({ item_count: state.length }),
    })
  }

  return requests
}

async function answerWith(text: string) {
  await userEvent.type(screen.getByLabelText(/Cevabın/), text)
  await userEvent.click(screen.getByRole('button', { name: 'Cevapla' }))
}

describe('QuizPage', () => {
  it('asks the first question with a plain German input', async () => {
    quizBackend()

    renderRoute('/sessions/7/quiz')

    expect(await screen.findByText('„kelime1“ Almanca nasıl söylenir?')).toBeInTheDocument()
    expect(screen.getByText('Türkçe → Almanca')).toBeInTheDocument()
    expect(screen.getByLabelText('İlerleme')).toHaveTextContent('Soru 1 / 2')
    const input = screen.getByLabelText('Cevabın (Almanca)')
    expect(input).toHaveAttribute('lang', 'de')
    expect(input).toHaveAttribute('spellcheck', 'false')
    expect(input).toHaveAttribute('autocomplete', 'off')
    expect(screen.getByRole('button', { name: 'Cevapla' })).toBeDisabled()
  })

  it('shows feedback after each answer and moves on when asked', async () => {
    const requests = quizBackend()
    renderRoute('/sessions/7/quiz')
    await screen.findByText('„kelime1“ Almanca nasıl söylenir?')

    await answerWith('  Wort1 ')

    expect(await screen.findByRole('heading', { name: 'Doğru!' })).toBeInTheDocument()
    expect(screen.getByText(/Kelime durumu: Öğreniliyor/)).toBeInTheDocument()
    const sent = requests.find((request) => request.url.endsWith('/api/quiz/1/answer'))!
    expect(await sent.json()).toEqual({ answer: 'Wort1' }) // trimmed

    await userEvent.click(screen.getByRole('button', { name: 'Sonraki soru' }))

    expect(screen.getByText('„kelime2“ Almanca nasıl söylenir?')).toBeInTheDocument()
    expect(screen.getByLabelText('İlerleme')).toHaveTextContent('Soru 2 / 2')
    expect(screen.getByLabelText(/Cevabın/)).toHaveValue('') // fresh input
  })

  it('explains a wrong answer', async () => {
    quizBackend(undefined, (id, text) =>
      json({
        question: answered(question(id), text, 'Lebensmittel einkaufen', {
          score: 0.5,
          corrected_answer: 'Lebensmittel einkaufen',
          ai_feedback: "'einkaufen' fiilini de eklemelisin.",
          error_type: 'vocabulary_usage',
        }),
        vocabulary_status: 'weak',
        learning_session: session(),
      }),
    )
    renderRoute('/sessions/7/quiz')
    await screen.findByText('„kelime1“ Almanca nasıl söylenir?')

    await answerWith('Lebensmittel')

    expect(await screen.findByRole('heading', { name: 'Yanlış' })).toBeInTheDocument()
    expect(screen.getByText('Lebensmittel')).toBeInTheDocument()
    expect(screen.getByText('Lebensmittel einkaufen')).toBeInTheDocument()
    expect(screen.getByText("'einkaufen' fiilini de eklemelisin.")).toBeInTheDocument()
    expect(
      screen.getByText(/Hata türü: Kelime kullanımı · Puan: 50\/100 · Kelime durumu: Zayıf/),
    ).toBeInTheDocument()
  })

  it('keeps the question open when the evaluation fails, so it can be retried', async () => {
    let fail = true
    quizBackend(undefined, () => {
      if (!fail) return undefined
      fail = false
      return apiError('ai_provider_error', 502)
    })
    renderRoute('/sessions/7/quiz')
    await screen.findByText('„kelime1“ Almanca nasıl söylenir?')

    await answerWith('Wort1')

    expect(await screen.findByRole('alert')).toHaveTextContent('tekrar deneyebilirsin')
    expect(screen.getByLabelText(/Cevabın/)).toHaveValue('Wort1')

    await userEvent.click(screen.getByRole('button', { name: 'Cevapla' }))

    expect(await screen.findByRole('heading', { name: 'Doğru!' })).toBeInTheDocument()
  })

  it('continues where the learner left off', async () => {
    quizBackend([answered(question(1), 'Wort1', 'Wort1'), question(2)])

    renderRoute('/sessions/7/quiz')

    expect(await screen.findByText('„kelime2“ Almanca nasıl söylenir?')).toBeInTheDocument()
    expect(screen.getByLabelText('İlerleme')).toHaveTextContent('Soru 2 / 2')
  })

  it('summarises the quiz and offers to review the weak words', async () => {
    const requests = quizBackend()
    renderRoute('/sessions/7/quiz')
    await screen.findByText('„kelime1“ Almanca nasıl söylenir?')

    await answerWith('Wort1')
    await userEvent.click(await screen.findByRole('button', { name: 'Sonraki soru' }))
    await answerWith('falsch')
    await userEvent.click(await screen.findByRole('button', { name: 'Sonuçları gör' }))

    expect(screen.getByRole('heading', { name: 'Quiz tamamlandı' })).toBeInTheDocument()
    expect(screen.getByText('1 / 2 doğru')).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(2)

    await userEvent.click(screen.getByRole('button', { name: 'Zayıf kelimeleri tekrar et' }))

    expect(await screen.findByText('Tekrar')).toBeInTheDocument() // the new review session
    const start = requests.find((request) => request.url.endsWith('/api/learning-sessions'))!
    expect(await start.json()).toEqual({ chapter_id: 21, batch_size: 1, mode: 'review' })
  })

  it('shows a streak of correct answers', async () => {
    quizBackend()
    renderRoute('/sessions/7/quiz')
    await screen.findByText('„kelime1“ Almanca nasıl söylenir?')

    await answerWith('Wort1')
    await userEvent.click(await screen.findByRole('button', { name: 'Sonraki soru' }))
    expect(screen.queryByText(/doğru üst üste/)).not.toBeInTheDocument()
    await answerWith('Wort2')

    expect(await screen.findByText('🔥 2 doğru üst üste')).toBeInTheDocument()
  })

  it('does not offer a review after a perfect quiz', async () => {
    quizBackend([answered(question(1), 'Wort1', 'Wort1'), answered(question(2), 'Wort2', 'Wort2')])

    renderRoute('/sessions/7/quiz')

    expect(await screen.findByText('2 / 2 doğru')).toBeInTheDocument()
    expect(screen.getByText('Harika! Hepsini bildin.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /tekrar et/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Bölümlere dön' })).toHaveAttribute(
      'href',
      '/documents/1',
    )
  })

  it('uses a Turkish input for German→Turkish questions', async () => {
    quizBackend([question(1, { question_type: 'german_to_turkish', question: '„Wort1“?' })])

    renderRoute('/sessions/7/quiz')

    expect(await screen.findByLabelText('Cevabın (Türkçe)')).toHaveAttribute('lang', 'tr')
  })

  it('is reached from the learning screen', async () => {
    quizBackend()
    renderRoute('/sessions/7')

    await userEvent.click(await screen.findByRole('link', { name: 'Quiz’e başla' }))

    expect(await screen.findByText('„kelime1“ Almanca nasıl söylenir?')).toBeInTheDocument()
  })
})
