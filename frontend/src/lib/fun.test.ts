import { describe, expect, it } from 'vitest'

import { answered, question, vocabulary } from '../test/factories'
import { articleOf, cheer, medal, streak } from './fun'

describe('streak', () => {
  it('counts correct answers back from the latest answered question', () => {
    const questions = [
      answered(question(1), 'x', 'Wort1'),
      answered(question(2), 'Wort2', 'Wort2'),
      answered(question(3), 'Wort3', 'Wort3'),
      question(4),
    ]
    expect(streak(questions)).toBe(2)
  })

  it('is zero after a wrong answer or before any answer', () => {
    expect(streak([answered(question(1), 'x', 'Wort1')])).toBe(0)
    expect(streak([question(1)])).toBe(0)
  })
})

describe('medal', () => {
  it('grows with the score', () => {
    expect(medal(1).emoji).toBe('🏆')
    expect(medal(0.8).emoji).toBe('🥇')
    expect(medal(0.5).emoji).toBe('🥈')
    expect(medal(0.2).emoji).toBe('💪')
  })
})

describe('cheer', () => {
  it('is stable for a question', () => {
    expect(cheer(3, true)).toBe(cheer(3, true))
    expect(cheer(3, true)).not.toBe(cheer(3, false))
  })
})

describe('articleOf', () => {
  it('reads the article field or the first word', () => {
    expect(articleOf(vocabulary({ article: 'die', german: 'die Getränke' }))).toBe('die')
    expect(articleOf(vocabulary({ article: null, german: 'Der Stau' }))).toBe('der')
    expect(articleOf(vocabulary({ article: 'der/die', german: 'der/die Kanzler/in' }))).toBeNull()
    expect(articleOf(vocabulary({ article: null, german: 'im Stau stehen' }))).toBeNull()
  })
})
