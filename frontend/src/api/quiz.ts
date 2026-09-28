import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, unwrap, type Schemas } from './client'
import { learningKeys } from './learning'

export type Quiz = Schemas['QuizRead']
export type QuizQuestion = Schemas['QuizQuestionRead']
export type AnswerResult = Schemas['AnswerResultRead']

export const quizKeys = {
  quiz: (sessionId: number) => ['learning-sessions', sessionId, 'quiz'] as const,
}

/**
 * The session's quiz. The endpoint is a POST but idempotent: the first call creates the
 * quiz, later calls return the same one, so it is safe to use as a query (and to repeat).
 */
export function useQuiz(sessionId: number) {
  return useQuery({
    queryKey: quizKeys.quiz(sessionId),
    queryFn: async () =>
      unwrap(
        await api.POST('/api/learning-sessions/{learning_session_id}/quiz', {
          params: { path: { learning_session_id: sessionId } },
        }),
      ),
    staleTime: Infinity, // only our own answers change it; they update the cache directly
  })
}

export function useAnswerQuestion(sessionId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ questionId, answer }: { questionId: number; answer: string }) =>
      unwrap(
        await api.POST('/api/quiz/{question_id}/answer', {
          params: { path: { question_id: questionId } },
          body: { answer },
        }),
      ),
    onSuccess: (result) => {
      queryClient.setQueryData<Quiz>(
        quizKeys.quiz(sessionId),
        (quiz) =>
          quiz && {
            ...quiz,
            questions: quiz.questions.map((question) =>
              question.id === result.question.id ? result.question : question,
            ),
          },
      )
      queryClient.setQueryData(learningKeys.session(sessionId), result.learning_session)
      queryClient.invalidateQueries({ queryKey: learningKeys.sessionItems(sessionId) })
      queryClient.invalidateQueries({
        queryKey: learningKeys.progress(result.learning_session.document_id),
      })
    },
  })
}
