import { useNavigate } from 'react-router'

import { errorMessage } from '../api/client'
import { useStartSession, type ChapterProgress, type SessionMode } from '../api/learning'
import { ProgressBar } from './ProgressBar'

function hint(chapter: ChapterProgress): string | null {
  if (chapter.total === 0) return 'Bu bölümde kelime yok.'
  if (chapter.new === 0 && !chapter.can_review)
    return 'Bölüm tamamlandı. Bütün kelimeler öğrenildi!'
  if (chapter.new > 0 && !chapter.can_start_new_batch)
    return 'Yeni kelimelere geçmek için önce öğrendiğin kelimeleri tekrar et.'
  return null
}

export function ChapterCard({
  chapter,
  batchSize,
}: {
  chapter: ChapterProgress
  batchSize: number
}) {
  const start = useStartSession()
  const navigate = useNavigate()

  function begin(mode: SessionMode) {
    start.mutate(
      { chapter_id: chapter.chapter_id, batch_size: batchSize, mode },
      { onSuccess: (session) => navigate(`/sessions/${session.id}`) },
    )
  }

  const note = hint(chapter)
  const percent = Math.round(chapter.mastery_ratio * 100)
  const done = chapter.total > 0 && chapter.mastered === chapter.total

  return (
    <li className={`card chapter${done ? ' chapter--done' : ''}`}>
      <div className="chapter__head">
        <div className="chapter__title">
          <span className="chapter__number" aria-hidden>
            {chapter.chapter_number}
          </span>
          <h3>{chapter.title}</h3>
        </div>
        <span className="muted">
          {chapter.total} kelime · %{percent} öğrenildi
        </span>
      </div>
      <ProgressBar counts={chapter} />
      <div className="chapter__actions">
        <button
          type="button"
          disabled={!chapter.can_start_new_batch || start.isPending}
          onClick={() => begin('new')}
        >
          Yeni {batchSize} kelime öğren
        </button>
        <button
          type="button"
          className="secondary"
          disabled={!chapter.can_review || start.isPending}
          onClick={() => begin('review')}
        >
          Tekrar et ({chapter.learning + chapter.weak})
        </button>
      </div>
      {note && <p className="muted">{note}</p>}
      {start.isError && (
        <p className="error" role="alert">
          {errorMessage(start.error)}
        </p>
      )}
    </li>
  )
}
