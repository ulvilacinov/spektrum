import { Link, useNavigate } from 'react-router'

import { errorMessage } from '../api/client'
import {
  useDocument,
  useProgress,
  useStartSession,
  useWeakWords,
  type ChapterProgress,
  type WeakWord,
} from '../api/learning'
import { NotFound } from '../components/Layout'
import { WeakWordCard } from '../components/WeakWordCard'
import { useIdParam } from '../lib/params'

/** The backend's largest batch size. */
const MAX_BATCH_SIZE = 100

export function WeakWordsPage() {
  const documentId = useIdParam('documentId')
  return documentId === null ? <NotFound /> : <DocumentWeakWords documentId={documentId} />
}

function DocumentWeakWords({ documentId }: { documentId: number }) {
  const document = useDocument(documentId)
  const progress = useProgress(documentId)
  const weak = useWeakWords(documentId)
  const back = <Link to={`/documents/${documentId}`}>← Bölümler</Link>

  const error = document.error ?? progress.error ?? weak.error
  if (error) {
    return (
      <div className="stack">
        {back}
        <p className="error" role="alert">
          {errorMessage(error)}
        </p>
      </div>
    )
  }
  if (!document.data || !progress.data || !weak.data) return <p className="muted">Yükleniyor…</p>

  const words = weak.data
  // Chapters in reading order, each with its weak words.
  const chapters = progress.data.chapters
    .map((chapter) => ({
      chapter,
      words: words.filter((word) => word.vocabulary_item.chapter_id === chapter.chapter_id),
    }))
    .filter(({ chapter, words }) => chapter.weak > 0 || words.length > 0)

  return (
    <div className="stack">
      {back}
      <section className="card">
        <h2>Zayıf kelimeler</h2>
        <p className="muted">
          {document.data.original_file_name} · {progress.data.weak} zayıf kelime
        </p>
        {chapters.length > 0 && (
          <p className="muted">
            Son hatalarını ve açıklamalarını incele, sonra bölümü tekrar et. İki kez üst üste doğru
            bildiğin kelime öğrenilmiş sayılır.
          </p>
        )}
      </section>

      {chapters.length === 0 ? (
        <div className="card empty">
          <span className="empty__emoji" aria-hidden>
            🌟
          </span>
          <p className="success">Hiç zayıf kelimen yok. Harika!</p>
        </div>
      ) : (
        chapters.map(({ chapter, words }) => (
          <WeakChapter key={chapter.chapter_id} chapter={chapter} words={words} />
        ))
      )}
    </div>
  )
}

function WeakChapter({ chapter, words }: { chapter: ChapterProgress; words: WeakWord[] }) {
  const review = useStartSession()
  const navigate = useNavigate()
  const count = Math.max(chapter.weak, words.length)

  function startReview() {
    // Review sessions pick the weak words first.
    review.mutate(
      {
        chapter_id: chapter.chapter_id,
        batch_size: Math.min(count, MAX_BATCH_SIZE),
        mode: 'review',
      },
      { onSuccess: (session) => navigate(`/sessions/${session.id}`) },
    )
  }

  return (
    <section className="stack" aria-labelledby={`weak-chapter-${chapter.chapter_id}`}>
      <div className="chapter__head">
        <h3 id={`weak-chapter-${chapter.chapter_id}`}>
          {chapter.title} ({count})
        </h3>
        <button type="button" onClick={startReview} disabled={review.isPending}>
          Bu bölümü tekrar et
        </button>
      </div>
      {review.isError && (
        <p className="error" role="alert">
          {errorMessage(review.error)}
        </p>
      )}
      <ul className="stack list-reset">
        {words.map((word) => (
          <WeakWordCard key={word.vocabulary_item.id} word={word} />
        ))}
      </ul>
    </section>
  )
}
