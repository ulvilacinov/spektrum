import type { VocabularyItem } from '../api/learning'
import type { QuizQuestion } from '../api/quiz'

const CHEERS_CORRECT = ['Süper!', 'Wunderbar!', 'Harika gidiyorsun!', 'Sehr gut!', 'Klasse!']
const CHEERS_WRONG = ['Olsun, bir dahakine!', 'Kopf hoch!', 'Neredeyse!', 'Hatalar öğretir.']

/** A short cheer; picked by question id so it stays the same across re-renders. */
export function cheer(questionId: number, correct: boolean): string {
  const cheers = correct ? CHEERS_CORRECT : CHEERS_WRONG
  return cheers[questionId % cheers.length]
}

/** Correct answers in a row, counted back from the latest answered question. */
export function streak(questions: QuizQuestion[]): number {
  let count = 0
  for (const question of questions.filter((item) => item.user_answer !== null).reverse()) {
    if (!question.is_correct) break
    count += 1
  }
  return count
}

export function medal(ratio: number): { emoji: string; title: string } {
  if (ratio === 1) return { emoji: '🏆', title: 'Mükemmel!' }
  if (ratio >= 0.8) return { emoji: '🥇', title: 'Çok iyi!' }
  if (ratio >= 0.5) return { emoji: '🥈', title: 'İyi gidiyorsun!' }
  return { emoji: '💪', title: 'Pes etmek yok!' }
}

/** "der" / "die" / "das" when the word has exactly one article, for colour coding. */
export function articleOf(word: VocabularyItem): 'der' | 'die' | 'das' | null {
  const article = (word.article ?? word.german.split(' ')[0]).toLowerCase()
  return article === 'der' || article === 'die' || article === 'das' ? article : null
}
