import type { Document } from '../api/documents'
import type { QuizQuestion } from '../api/quiz'
import type {
  ChapterProgress,
  LearningSession,
  Progress,
  SessionItem,
  VocabularyItem,
  WeakWord,
} from '../api/learning'

export function document(overrides: Partial<Document> = {}): Document {
  return {
    id: 1,
    user_id: null,
    original_file_name: 'spektrum_b1.pdf',
    file_name: 'abc.pdf',
    status: 'parsed',
    uploaded_at: '2026-09-27T18:12:38Z',
    processed_at: '2026-09-27T18:20:00Z',
    error_message: null,
    ...overrides,
  }
}

export function chapterProgress(overrides: Partial<ChapterProgress> = {}): ChapterProgress {
  return {
    chapter_id: 21,
    document_id: 1,
    chapter_number: 1,
    title: 'Kapitel 1',
    total: 64,
    new: 64,
    learning: 0,
    weak: 0,
    mastered: 0,
    mastery_ratio: 0,
    can_start_new_batch: true,
    can_review: false,
    ...overrides,
  }
}

export function progress(chapters: ChapterProgress[]): Progress {
  const sum = (key: 'total' | 'new' | 'learning' | 'weak' | 'mastered') =>
    chapters.reduce((total, chapter) => total + chapter[key], 0)
  const total = sum('total')
  return {
    total,
    new: sum('new'),
    learning: sum('learning'),
    weak: sum('weak'),
    mastered: sum('mastered'),
    mastery_ratio: total ? sum('mastered') / total : 0,
    chapters,
  }
}

export function session(overrides: Partial<LearningSession> = {}): LearningSession {
  return {
    id: 7,
    chapter_id: 21,
    chapter_title: 'Kapitel 1',
    document_id: 1,
    batch_size: 10,
    mode: 'new',
    item_count: 2,
    started_at: '2026-09-28T10:00:00Z',
    completed_at: null,
    correct_count: 0,
    wrong_count: 0,
    ...overrides,
  }
}

export function vocabulary(overrides: Partial<VocabularyItem> = {}): VocabularyItem {
  return {
    id: 1,
    chapter_id: 21,
    order: 1,
    german: 'im Stau stehen',
    turkish: 'Trafikte kalmak/beklemek',
    item_type: 'phrase',
    article: null,
    base_verb: 'stehen',
    prateritum: 'stand',
    perfekt: 'hat gestanden',
    preposition: 'in',
    grammatical_case: 'Dativ',
    example_german: 'Morgens stehe ich oft im Stau.',
    example_turkish: 'Sabahları sık sık trafikte kalırım.',
    source_text: 'im Stau stehen',
    source_page: 1,
    ...overrides,
  }
}

export function sessionItem(position: number, word: Partial<VocabularyItem> = {}): SessionItem {
  return { position, status: 'learning', vocabulary_item: vocabulary({ id: position, ...word }) }
}

export function question(id: number, overrides: Partial<QuizQuestion> = {}): QuizQuestion {
  return {
    id,
    position: id,
    vocabulary_item_id: id,
    question_type: 'turkish_to_german',
    question: `„kelime${id}“ Almanca nasıl söylenir?`,
    user_answer: null,
    is_correct: null,
    score: null,
    expected_answer: null,
    corrected_answer: null,
    ai_feedback: null,
    error_type: null,
    evaluation_method: null,
    answered_at: null,
    ...overrides,
  }
}

/** The answered form of ``unanswered``, as the backend returns it. */
export function answered(
  unanswered: QuizQuestion,
  answer: string,
  expected: string,
  overrides: Partial<QuizQuestion> = {},
): QuizQuestion {
  const correct = answer === expected
  return {
    ...unanswered,
    user_answer: answer,
    is_correct: correct,
    score: correct ? 1 : 0,
    expected_answer: expected,
    corrected_answer: expected,
    ai_feedback: correct ? 'Doğru!' : 'Anlam yanlış.',
    error_type: correct ? null : 'meaning',
    evaluation_method: correct ? 'exact' : 'ai',
    answered_at: '2026-09-28T10:05:00Z',
    ...overrides,
  }
}

export function weakWord(
  id: number,
  word: Partial<VocabularyItem> = {},
  mistake: Partial<NonNullable<WeakWord['last_mistake']>> | null = {},
): WeakWord {
  return {
    vocabulary_item: vocabulary({ id, german: `Wort${id}`, turkish: `kelime${id}`, ...word }),
    progress: {
      status: 'weak',
      seen_count: 2,
      correct_count: 1,
      wrong_count: 1,
      consecutive_correct: 0,
      mastery_score: 0,
      last_seen_at: '2026-09-28T10:05:00Z',
      next_review_at: null,
    },
    last_mistake: mistake && {
      question_id: 100 + id,
      question_type: 'turkish_to_german',
      question: `„kelime${id}“ Almanca nasıl söylenir?`,
      user_answer: 'falsch',
      expected_answer: `Wort${id}`,
      corrected_answer: `Wort${id}`,
      feedback: 'Anlam yanlış.',
      error_type: 'meaning',
      answered_at: '2026-09-28T10:05:00Z',
      ...mistake,
    },
  }
}
