import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'

import { clearChatHistory } from '../lib/chatStorage'
import { ApiError, api, unwrap, type Schemas } from './client'

export type User = Schemas['UserRead']

export const authKeys = {
  me: ['auth', 'me'] as const,
}

/** Drops everything cached for the previous user (keeps only the login state). */
function forgetUserData(queryClient: QueryClient) {
  queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== 'auth' })
}

/** The logged-in user, or null when nobody is logged in. */
export function useMe() {
  return useQuery({
    queryKey: authKeys.me,
    queryFn: async (): Promise<User | null> => {
      const result = await api.GET('/api/auth/me')
      if (result.response.status === 401) return null
      return unwrap(result)
    },
    staleTime: Infinity,
    retry: false,
  })
}

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: { username: string; password: string }) =>
      unwrap(await api.POST('/api/auth/login', { body })),
    onSuccess: (user) => {
      forgetUserData(queryClient)
      queryClient.setQueryData(authKeys.me, user)
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { response } = await api.POST('/api/auth/logout')
      // 401: the session had already ended, which is what we wanted.
      if (!response.ok && response.status !== 401) {
        throw new ApiError('http_error', `HTTP ${response.status}`, response.status)
      }
    },
    onSuccess: () => {
      clearChatHistory()
      forgetUserData(queryClient)
      queryClient.setQueryData(authKeys.me, null)
    },
  })
}
