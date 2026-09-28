import { Link } from 'react-router'

import { errorMessage } from '../api/client'
import { useSession, useSessionItems } from '../api/learning'
import { NotFound } from '../components/Layout'
import { WordCard } from '../components/WordCard'
import { MODE_LABELS } from '../lib/labels'
import { useIdParam } from '../lib/params'

export function SessionPage() {
  const sessionId = useIdParam('sessionId')
  return sessionId === null ? <NotFound /> : <SessionWords sessionId={sessionId} />
}

function SessionWords({ sessionId }: { sessionId: number }) {
  const session = useSession(sessionId)
  const items = useSessionItems(sessionId)

  const error = session.error ?? items.error
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
  if (!session.data || !items.data) return <p className="muted">Yükleniyor…</p>

  return (
    <div className="stack">
      <Link to={`/documents/${session.data.document_id}`}>← Bölümler</Link>
      <section className="card">
        <p className="muted">{MODE_LABELS[session.data.mode]}</p>
        <h2>
          {session.data.chapter_title}: {items.data.length} kelime
        </h2>
        <p className="muted">
          Kelimeleri, anlamlarını ve örnek cümleleri incele. Hazır olduğunda quiz’e geç.
        </p>
      </section>
      <ul className="stack list-reset">
        {items.data.map((item) => (
          <WordCard key={item.position} item={item} />
        ))}
      </ul>
    </div>
  )
}
