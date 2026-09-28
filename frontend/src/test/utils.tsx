import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router'
import { vi } from 'vitest'

import { routes } from '../router'

/** Renders the real routes at ``path`` with a fresh, non-retrying query client. */
export function renderRoute(path = '/') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

type Handler = (request: Request) => Response | Promise<Response>

/**
 * Replaces fetch with a tiny fake backend: ``routes`` maps "METHOD /path" to a handler.
 * Returns the recorded requests so tests can assert what was sent.
 */
export function mockApi(handlers: Record<string, Handler>) {
  const requests: Request[] = []
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const request = input instanceof Request ? input : new Request(input)
    requests.push(request.clone())
    const { pathname } = new URL(request.url, 'http://test')
    const handler = handlers[`${request.method} ${pathname}`]
    if (!handler) throw new Error(`Unexpected request: ${request.method} ${pathname}`)
    return handler(request)
  })
  return requests
}

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export function apiError(code: string, status: number, message = code): Response {
  return json({ error: { code, message, details: {} } }, status)
}
