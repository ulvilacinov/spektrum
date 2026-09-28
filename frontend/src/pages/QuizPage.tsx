import { useState } from 'react'
import { Link } from 'react-router'

import { errorMessage } from '../api/client'
import { useSession } from '../api/learning'
import { useAnswerQuestion, useQuiz } from '../api/quiz'
import { AnswerFeedback } from '../components/AnswerFeedback'
import { NotFound } from '../components/Layout'
import { QuestionForm } from '../components/QuestionForm'
import { QuizSummary } from '../components/QuizSummary'
import { streak } from '../lib/fun'
import type { WordStatus } from '../lib/labels'
import { useIdParam } from '../lib/params'

export function QuizPage() {
  const sessionId = useIdParam('sessionId')
  return sessionId === null ? <NotFound /> : <SessionQuiz sessionId={sessionId} />
}

function SessionQuiz({ sessionId }: { sessionId: number }) {
  const session = useSession(sessionId)
  const quiz = useQuiz(sessionId)
  const answer = useAnswerQuestion(sessionId)
  // The question whose feedback is on screen; stays until the learner moves on.
  const [feedback, setFeedback] = useState<{ id: number; status: WordStatus } | null>(null)

  const error = session.error ?? quiz.error
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
  if (!session.data || !quiz.data) return <p className="muted">Quiz hazırlanıyor…</p>

  const questions = quiz.data.questions
  const answered = questions.filter((question) => question.user_answer !== null).length
  const shown = feedback && questions.find((question) => question.id === feedback.id)
  const next = questions.find((question) => question.user_answer === null)
  const inARow = streak(questions)

  let content
  if (shown) {
    content = (
      <AnswerFeedback
        question={shown}
        status={feedback.status}
        isLast={next === undefined}
        onNext={() => setFeedback(null)}
      />
    )
  } else if (next) {
    content = (
      <QuestionForm
        key={next.id} // fresh input for every question
        question={next}
        pending={answer.isPending}
        error={answer.variables?.questionId === next.id ? answer.error : null}
        onSubmit={(text) =>
          answer.mutate(
            { questionId: next.id, answer: text },
            {
              onSuccess: (result) =>
                setFeedback({ id: result.question.id, status: result.vocabulary_status }),
            },
          )
        }
      />
    )
  } else {
    content = <QuizSummary session={session.data} questions={questions} />
  }

  return (
    <div className="stack">
      <Link to={`/sessions/${sessionId}`}>← Kelimeler</Link>
      <div className="quiz__header">
        <h2>{session.data.chapter_title} · Quiz</h2>
        <div className="quiz__meta">
          {inARow >= 2 && <span className="streak">🔥 {inARow} doğru üst üste</span>}
          <span className="muted" aria-label="İlerleme">
            {next || shown
              ? `Soru ${Math.min(answered + (shown ? 0 : 1), questions.length)} / ${questions.length}`
              : `${questions.length} soru`}
          </span>
        </div>
      </div>
      <progress className="quiz__progress" max={questions.length} value={answered} aria-hidden />
      {content}
    </div>
  )
}
