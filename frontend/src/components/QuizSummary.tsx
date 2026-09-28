import { Link, useNavigate } from 'react-router'

import { errorMessage } from '../api/client'
import { useStartSession, type LearningSession } from '../api/learning'
import type { QuizQuestion } from '../api/quiz'

interface Props {
  session: LearningSession
  questions: QuizQuestion[]
}

export function QuizSummary({ session, questions }: Props) {
  const review = useStartSession()
  const navigate = useNavigate()
  const correct = questions.filter((question) => question.is_correct).length
  const wrong = questions.length - correct

  function startReview() {
    review.mutate(
      { chapter_id: session.chapter_id, batch_size: Math.max(wrong, 1), mode: 'review' },
      { onSuccess: (next) => navigate(`/sessions/${next.id}`) },
    )
  }

  return (
    <div className="stack">
      <section className="card">
        <h2>Quiz tamamlandı</h2>
        <p className="quiz__score">
          {correct} / {questions.length} doğru
        </p>
        <p className="muted">
          {wrong === 0
            ? 'Harika! Hepsini bildin.'
            : 'Yanlış cevapladığın kelimeler “zayıf” olarak işaretlendi. Tekrar ederek öğrenebilirsin.'}
        </p>
        <div className="chapter__actions">
          {wrong > 0 && (
            <button type="button" onClick={startReview} disabled={review.isPending}>
              Zayıf kelimeleri tekrar et
            </button>
          )}
          <Link
            className={wrong > 0 ? 'button button--secondary' : 'button'}
            to={`/documents/${session.document_id}`}
          >
            Bölümlere dön
          </Link>
        </div>
        {review.isError && (
          <p className="error" role="alert">
            {errorMessage(review.error)}
          </p>
        )}
      </section>

      <ol className="stack list-reset">
        {questions.map((question) => (
          <li
            key={question.id}
            className={`card summary-item ${question.is_correct ? 'summary-item--correct' : 'summary-item--wrong'}`}
          >
            <p>
              <strong>{question.is_correct ? '✓ Doğru' : '✗ Yanlış'}</strong> · {question.question}
            </p>
            <p className="muted">
              Cevabın: {question.user_answer} · Doğrusu:{' '}
              <span lang="de">{question.expected_answer}</span>
            </p>
            {!question.is_correct && question.ai_feedback && <p>{question.ai_feedback}</p>}
          </li>
        ))}
      </ol>
    </div>
  )
}
