import { MutationCache, QueryCache, QueryClient, type DefaultOptions } from '@tanstack/react-query'

import { authKeys } from './auth'
import { ApiError } from './client'

/**
 * The app's query client. A 401 from any request means the session has ended (expired,
 * logged out elsewhere): the app then shows the login page.
 */
export function createQueryClient(defaultOptions?: DefaultOptions): QueryClient {
  const queryClient: QueryClient = new QueryClient({
    defaultOptions,
    queryCache: new QueryCache({ onError: sessionEnded }),
    mutationCache: new MutationCache({ onError: sessionEnded }),
  })

  function sessionEnded(error: unknown) {
    if (error instanceof ApiError && error.code === 'not_authenticated') {
      queryClient.setQueryData(authKeys.me, null)
    }
  }

  return queryClient
}

/** Retry once for network and server errors, never for 4xx answers. */
export function retryUnlessClientError(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status < 500) return false
  return failureCount < 1
}
