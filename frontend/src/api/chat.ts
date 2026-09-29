import { useMutation } from '@tanstack/react-query'

import { api, unwrap, type Schemas } from './client'

export type ChatMessage = Schemas['ChatMessageIn']

/** Sends the conversation (oldest first, ending with the new question) to the AI tutor. */
export function useAskTutor() {
  return useMutation({
    mutationFn: async (messages: ChatMessage[]) =>
      unwrap(await api.POST('/api/chat', { body: { messages } })),
  })
}
