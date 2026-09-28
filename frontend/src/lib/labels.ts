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
