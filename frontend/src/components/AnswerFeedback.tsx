import type { QuizQuestion } from '../api/quiz'
import { cheer } from '../lib/fun'
import { ERROR_TYPE_LABELS, STATUS_LABELS, type WordStatus } from '../lib/labels'
import { Confetti } from './Confetti'

interface Props {
  question: QuizQuestion
  status: WordStatus | null
  isLast: boolean
  onNext: () => void
}

export function AnswerFeedback({ question, status, isLast, onNext }: Props) {
  const correct = question.is_correct === true
  const showCorrection =
    question.corrected_answer &&
    question.corrected_answer !== question.expected_answer &&
    question.corrected_answer !== question.user_answer

  return (
    <section
      className={`card feedback ${correct ? 'feedback--correct' : 'feedback--wrong'}`}
      aria-live="polite"
    >
      {correct && <Confetti />}
      <div className="feedback__title">
        <span className="feedback__emoji" aria-hidden>
          {correct ? '🎉' : '🙈'}
        </span>
        <div>
          <h2>{correct ? 'Doğru!' : 'Yanlış'}</h2>
          <p className="feedback__cheer">{cheer(question.id, correct)}</p>
        </div>
      </div>
      <p className="muted">{question.question}</p>
      <dl className="feedback__answers">
        <div>
          <dt>Senin cevabın</dt>
          <dd>{question.user_answer}</dd>
        </div>
        <div>
          <dt>Kitaptaki cevap</dt>
          <dd lang="de">{question.expected_answer}</dd>
        </div>
        {showCorrection && (
          <div>
            <dt>Düzeltilmiş hâli</dt>
            <dd>{question.corrected_answer}</dd>
          </div>
        )}
      </dl>
      {question.ai_feedback && <p className="feedback__explanation">{question.ai_feedback}</p>}
      <p className="muted">
        {!correct && question.error_type && (
          <>Hata türü: {ERROR_TYPE_LABELS[question.error_type]} · </>
        )}
        {question.score !== null && <>Puan: {Math.round(question.score * 100)}/100</>}
        {status && <> · Kelime durumu: {STATUS_LABELS[status]}</>}
      </p>
      <div>
        <button type="button" onClick={onNext} autoFocus>
          {isLast ? 'Sonuçları gör' : 'Sonraki soru'}
        </button>
      </div>
    </section>
  )
}
