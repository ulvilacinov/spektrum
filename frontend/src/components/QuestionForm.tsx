import { useState, type FormEvent } from 'react'

import { errorMessage } from '../api/client'
import type { QuizQuestion } from '../api/quiz'
import { QUESTION_TYPE_LABELS, answerLanguage } from '../lib/labels'

interface Props {
  question: QuizQuestion
  pending: boolean
  error: unknown
  onSubmit: (answer: string) => void
}

export function QuestionForm({ question, pending, error, onSubmit }: Props) {
  const [answer, setAnswer] = useState('')
  const language = answerLanguage(question.question_type)

  function submit(event: FormEvent) {
    event.preventDefault()
    if (answer.trim()) onSubmit(answer.trim())
  }

  return (
    <form className="card quiz__question" onSubmit={submit}>
      <p className="quiz__type">{QUESTION_TYPE_LABELS[question.question_type]}</p>
      <h2 className="quiz__prompt">{question.question}</h2>
      <label className="quiz__answer">
        Cevabın ({language === 'de' ? 'Almanca' : 'Türkçe'})
        <input
          type="text"
          lang={language}
          value={answer}
          onChange={(event) => setAnswer(event.target.value)}
          disabled={pending}
          // The browser must not correct the German for the learner.
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck={false}
          autoFocus
          maxLength={1000}
        />
      </label>
      <div>
        <button type="submit" disabled={pending || !answer.trim()}>
          {pending ? 'Değerlendiriliyor…' : 'Cevapla'}
        </button>
      </div>
      {error !== null && error !== undefined && (
        <p className="error" role="alert">
          {errorMessage(error)} Cevabın kaydedilmedi, tekrar deneyebilirsin.
        </p>
      )}
    </form>
  )
}
