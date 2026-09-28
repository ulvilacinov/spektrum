import { Link } from 'react-router'

import { errorMessage } from '../api/client'
import { useAnalyzeDocument, type Document } from '../api/documents'
import { formatDateTime } from '../lib/format'
import { StatusBadge } from './StatusBadge'

const REANALYZE_WARNING =
  'Belge yeniden analiz edilirse bölümleri ve kelimeleri yeniden oluşturulur. ' +
  'Bu belgedeki bütün öğrenme ilerlemen silinir. Devam edilsin mi?'

export function DocumentRow({ document }: { document: Document }) {
  const analyze = useAnalyzeDocument()
  const running = analyze.isPending || document.status === 'parsing'

  function start(force: boolean) {
    if (force && !window.confirm(REANALYZE_WARNING)) return
    analyze.mutate({ documentId: document.id, force })
  }

  return (
    <li className="card document">
      <div className="document__main">
        <div>
          <h3 className="document__title">{document.original_file_name}</h3>
          <p className="muted">Yüklenme: {formatDateTime(document.uploaded_at)}</p>
        </div>
        <StatusBadge status={running ? 'parsing' : document.status} />
      </div>

      {document.status === 'failed' && document.error_message && !running && (
        <p className="error">Son analiz başarısız: {document.error_message}</p>
      )}

      <div className="document__actions">
        {running ? (
          <p className="muted" role="status">
            <span className="spinner" aria-hidden /> Bölümler ve kelimeler çıkarılıyor. Bu birkaç
            dakika sürebilir…
          </p>
        ) : document.status === 'parsed' ? (
          <>
            <Link className="button" to={`/documents/${document.id}`}>
              Bölümlere git
            </Link>
            <button type="button" className="secondary" onClick={() => start(true)}>
              Yeniden analiz et
            </button>
          </>
        ) : (
          <button type="button" onClick={() => start(false)}>
            Analiz et
          </button>
        )}
      </div>

      {analyze.isError && (
        <p className="error" role="alert">
          {errorMessage(analyze.error)}
        </p>
      )}
      {analyze.isSuccess && (
        <p className="success" role="status">
          {analyze.data.chapter_count} bölüm ve {analyze.data.vocabulary_count} kelime bulundu.
          {analyze.data.rejected_item_count > 0 &&
            ` PDF’te bulunamayan ${analyze.data.rejected_item_count} öğe atlandı.`}
        </p>
      )}
    </li>
  )
}
