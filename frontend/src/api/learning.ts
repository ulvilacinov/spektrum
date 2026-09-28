import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, unwrap, type Schemas } from './client'

export type ChapterProgress = Schemas['ChapterProgressRead']
export type Progress = Schemas['ProgressRead']
export type LearningSession = Schemas['LearningSessionRead']
export type SessionItem = Schemas['LearningSessionItemRead']
export type VocabularyItem = Schemas['VocabularyItemRead']
export type SessionMode = Schemas['SessionMode']

export const learningKeys = {
  progress: (documentId: number) => ['progress', documentId] as const,
  session: (sessionId: number) => ['learning-sessions', sessionId] as const,
  sessionItems: (sessionId: number) => ['learning-sessions', sessionId, 'items'] as const,
}

export function useDocument(documentId: number) {
  return useQuery({
    queryKey: ['documents', documentId],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/documents/{document_id}', {
          params: { path: { document_id: documentId } },
        }),
      ),
  })
}

export function useProgress(documentId: number) {
  return useQuery({
    queryKey: learningKeys.progress(documentId),
    queryFn: async () =>
      unwrap(await api.GET('/api/progress', { params: { query: { document_id: documentId } } })),
  })
}

export function useStartSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: { chapter_id: number; batch_size: number; mode: SessionMode }) =>
      unwrap(await api.POST('/api/learning-sessions', { body })),
    // Starting a session changes the words' status.
    onSuccess: (session) =>
      queryClient.invalidateQueries({ queryKey: learningKeys.progress(session.document_id) }),
  })
}

export function useSession(sessionId: number) {
  return useQuery({
    queryKey: learningKeys.session(sessionId),
    queryFn: async () =>
      unwrap(
        await api.GET('/api/learning-sessions/{learning_session_id}', {
          params: { path: { learning_session_id: sessionId } },
        }),
      ),
  })
}

export function useSessionItems(sessionId: number) {
  return useQuery({
    queryKey: learningKeys.sessionItems(sessionId),
    queryFn: async () =>
      unwrap(
        await api.GET('/api/learning-sessions/{learning_session_id}/items', {
          params: { path: { learning_session_id: sessionId } },
        }),
      ),
  })
}
