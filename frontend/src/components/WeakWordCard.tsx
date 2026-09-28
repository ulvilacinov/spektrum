import type { WeakWord } from '../api/learning'
import { formatDateTime } from '../lib/format'
import { ERROR_TYPE_LABELS, ITEM_TYPE_LABELS, QUESTION_TYPE_LABELS } from '../lib/labels'

export function WeakWordCard({ word }: { word: WeakWord }) {
  const item = word.vocabulary_item
  const mistake = word.last_mistake
  const showCorrection =
    mistake?.corrected_answer &&
    mistake.corrected_answer !== mistake.expected_answer &&
    mistake.corrected_answer !== mistake.user_answer

  return (
    <li className="card summary-item--wrong">
      <div className="word__head">
        <h3 className="word__german" lang="de">
          {item.german}
        </h3>
        <span className="muted">
          {word.progress.wrong_count} yanlış · {word.progress.correct_count} doğru
        </span>
      </div>
      <p className="word__turkish">
        {item.turkish} <span className="muted">({ITEM_TYPE_LABELS[item.item_type]})</span>
      </p>

      {mistake ? (
        <div className="stack weak__mistake">
          <p className="muted">
            Son hata · {QUESTION_TYPE_LABELS[mistake.question_type]}
            {mistake.answered_at && <> · {formatDateTime(mistake.answered_at)}</>}
          </p>
          <p>{mistake.question}</p>
          <dl className="feedback__answers">
            <div>
              <dt>Senin cevabın</dt>
              <dd>{mistake.user_answer}</dd>
            </div>
            <div>
              <dt>Kitaptaki cevap</dt>
              <dd lang="de">{mistake.expected_answer}</dd>
            </div>
            {showCorrection && (
              <div>
                <dt>Düzeltilmiş hâli</dt>
                <dd>{mistake.corrected_answer}</dd>
              </div>
            )}
          </dl>
          {mistake.feedback && <p className="feedback__explanation">{mistake.feedback}</p>}
          {mistake.error_type && (
            <p className="muted">Hata türü: {ERROR_TYPE_LABELS[mistake.error_type]}</p>
          )}
        </div>
      ) : (
        <p className="muted">Bu kelime için kayıtlı bir hata yok.</p>
      )}
    </li>
  )
}
