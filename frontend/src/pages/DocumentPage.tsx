import { useState } from 'react'
import { Link } from 'react-router'

import { errorMessage } from '../api/client'
import { useDocument, useProgress } from '../api/learning'
import { ChapterCard } from '../components/ChapterCard'
import { NotFound } from '../components/Layout'
import { ProgressBar } from '../components/ProgressBar'
import { useIdParam } from '../lib/params'

const BATCH_SIZES = [5, 10, 20]

export function DocumentPage() {
  const documentId = useIdParam('documentId')
  return documentId === null ? <NotFound /> : <DocumentChapters documentId={documentId} />
}

function DocumentChapters({ documentId }: { documentId: number }) {
  const document = useDocument(documentId)
  const progress = useProgress(documentId)
  const [batchSize, setBatchSize] = useState(10)

  const error = document.error ?? progress.error
  if (error) {
    return (
      <div className="stack">
        <Link to="/">← Belgelerim</Link>
        <p className="error" role="alert">
          {errorMessage(error)}
        </p>
      </div>
    )
  }
  if (!document.data || !progress.data) return <p className="muted">Yükleniyor…</p>

  const chapters = progress.data.chapters

  return (
    <div className="stack">
      <Link to="/">← Belgelerim</Link>
      <section className="card">
        <h2>{document.data.original_file_name}</h2>
        <p className="muted">
          {chapters.length} bölüm · {progress.data.total} kelime · %
          {Math.round(progress.data.mastery_ratio * 100)} öğrenildi
        </p>
        <ProgressBar counts={progress.data} />
        {progress.data.weak > 0 && (
          <Link to={`/documents/${documentId}/weak`}>
            Zayıf kelimelerim ({progress.data.weak}) ve son hatalarım →
          </Link>
        )}
        <label className="batch-size">
          Bir seferde kaç kelime?{' '}
          <select value={batchSize} onChange={(event) => setBatchSize(Number(event.target.value))}>
            {BATCH_SIZES.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </label>
      </section>

      {chapters.length === 0 ? (
        <p className="muted">
          Bu belgede henüz bölüm yok. Belgeler sayfasından analiz etmen gerekiyor.
        </p>
      ) : (
        <ul className="stack list-reset">
          {chapters.map((chapter) => (
            <ChapterCard key={chapter.chapter_id} chapter={chapter} batchSize={batchSize} />
          ))}
        </ul>
      )}
    </div>
  )
}
