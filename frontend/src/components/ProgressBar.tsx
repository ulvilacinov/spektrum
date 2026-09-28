import { STATUS_LABELS, type WordStatus } from '../lib/labels'

interface Counts {
  total: number
  new: number
  learning: number
  weak: number
  mastered: number
}

const ORDER: WordStatus[] = ['mastered', 'learning', 'weak', 'new']

/** A segmented bar plus the same numbers as text, so no information depends on colour. */
export function ProgressBar({ counts }: { counts: Counts }) {
  return (
    <div className="progress">
      <div className="progress__bar" aria-hidden>
        {counts.total > 0 &&
          ORDER.map((status) =>
            counts[status] > 0 ? (
              <span
                key={status}
                className={`progress__segment progress__segment--${status}`}
                style={{ width: `${(counts[status] / counts.total) * 100}%` }}
              />
            ) : null,
          )}
      </div>
      <p className="progress__legend">
        {ORDER.map((status) => (
          <span key={status} className="progress__legend-item">
            <span className={`dot dot--${status}`} aria-hidden />
            {STATUS_LABELS[status]}: {counts[status]}
          </span>
        ))}
      </p>
    </div>
  )
}
