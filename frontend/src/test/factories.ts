import type { Document } from '../api/documents'
import type {
  ChapterProgress,
  LearningSession,
  Progress,
  SessionItem,
  VocabularyItem,
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
