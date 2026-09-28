import type { Schemas } from '../api/client'
import type { SessionMode, VocabularyItem } from '../api/learning'

export type WordStatus = 'new' | 'learning' | 'weak' | 'mastered'

export const STATUS_LABELS: Record<WordStatus, string> = {
  new: 'Yeni',
  learning: 'Öğreniliyor',
  weak: 'Zayıf',
  mastered: 'Öğrenildi',
}

export const ITEM_TYPE_LABELS: Record<VocabularyItem['item_type'], string> = {
  word: 'kelime',
  noun: 'isim',
  verb: 'fiil',
  phrase: 'kalıp',
  expression: 'ifade',
  grammar_pattern: 'dilbilgisi kalıbı',
}

export const MODE_LABELS: Record<SessionMode, string> = {
  new: 'Yeni kelimeler',
  review: 'Tekrar',
}

export const QUESTION_TYPE_LABELS: Record<Schemas['QuestionType'], string> = {
  german_to_turkish: 'Almanca → Türkçe',
  turkish_to_german: 'Türkçe → Almanca',
  article: 'Artikel',
  preposition: 'Edat',
  verb_conjugation: 'Fiil çekimi',
  sentence_translation: 'Cümle çevirisi',
  fill_blank: 'Boşluk doldurma',
  free_sentence: 'Serbest cümle',
}

export const ERROR_TYPE_LABELS: Record<Schemas['ErrorType'], string> = {
  article: 'Artikel',
  case: 'Hal (durum eki)',
  preposition: 'Edat',
  word_order: 'Kelime sırası',
  verb_conjugation: 'Fiil çekimi',
  spelling: 'Yazım',
  vocabulary_usage: 'Kelime kullanımı',
  meaning: 'Anlam',
  grammar: 'Dilbilgisi',
}

/** Only German→Turkish questions are answered in Turkish. */
export function answerLanguage(questionType: Schemas['QuestionType']): 'de' | 'tr' {
  return questionType === 'german_to_turkish' ? 'tr' : 'de'
}
