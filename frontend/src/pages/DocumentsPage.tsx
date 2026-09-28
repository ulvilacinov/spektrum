import { errorMessage } from '../api/client'
import { useDocuments } from '../api/documents'
import { DocumentRow } from '../components/DocumentRow'
import { UploadForm } from '../components/UploadForm'

export function DocumentsPage() {
  const documents = useDocuments()

  return (
    <div className="stack">
      <UploadForm />
      <section className="stack">
        <h2>Belgelerim</h2>
        {documents.isPending && <p className="muted">Yükleniyor…</p>}
        {documents.isError && (
          <p className="error" role="alert">
            {errorMessage(documents.error)}
          </p>
        )}
        {documents.data?.length === 0 && (
          <div className="card empty">
            <span className="empty__emoji" aria-hidden>
              📚
            </span>
            <p className="muted">Henüz belge yok. Başlamak için bir PDF yükle.</p>
          </div>
        )}
        {documents.data && documents.data.length > 0 && (
          <ul className="stack list-reset">
            {documents.data.map((document) => (
              <DocumentRow key={document.id} document={document} />
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
