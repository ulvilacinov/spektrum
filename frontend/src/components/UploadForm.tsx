import { useRef, useState, type FormEvent } from 'react'

import { errorMessage } from '../api/client'
import { useUploadDocument } from '../api/documents'

export function UploadForm() {
  const upload = useUploadDocument()
  const input = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [clientError, setClientError] = useState<string | null>(null)

  function choose(selected: File | null) {
    upload.reset()
    setFile(selected)
    setClientError(
      selected && !selected.name.toLowerCase().endsWith('.pdf')
        ? 'Yalnızca PDF dosyaları yüklenebilir.'
        : null,
    )
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!file || clientError) return
    upload.mutate(file, {
      onSuccess: () => {
        setFile(null)
        if (input.current) input.current.value = ''
      },
    })
  }

  const error = clientError ?? (upload.error ? errorMessage(upload.error) : null)

  return (
    <form className="card upload" onSubmit={submit}>
      <h2>PDF yükle</h2>
      <p className="muted">Almanca kelime listesi içeren bir PDF seç.</p>
      <div className="upload__row">
        <input
          ref={input}
          type="file"
          accept="application/pdf,.pdf"
          aria-label="PDF dosyası"
          onChange={(event) => choose(event.target.files?.[0] ?? null)}
        />
        <button type="submit" disabled={!file || !!clientError || upload.isPending}>
          {upload.isPending ? 'Yükleniyor…' : 'Yükle'}
        </button>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {upload.isSuccess && <p className="success">Yüklendi. Şimdi analiz edebilirsin.</p>}
    </form>
  )
}
