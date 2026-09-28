import type { Document } from '../api/documents'

const LABELS: Record<Document['status'], string> = {
  uploaded: 'Yüklendi',
  parsing: 'Analiz ediliyor',
  parsed: 'Hazır',
  failed: 'Hata',
}

export function StatusBadge({ status }: { status: Document['status'] }) {
  return <span className={`badge badge--${status}`}>{LABELS[status]}</span>
}
