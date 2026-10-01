import { QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router'
import { vi } from 'vitest'

import { createQueryClient } from '../api/queryClient'
import { routes } from '../router'

/** Renders the real routes at ``path`` with a fresh, non-retrying query client. */
export function renderRoute(path = '/') {
  const queryClient = createQueryClient({
    queries: { retry: false },
    mutations: { retry: false },
  })
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

type Handler = (request: Request) => Response | Promise<Response>

export const TEST_USER = { id: 1, username: 'anna' }

export const TEST_AI_SETTINGS = {
  configured: true,
  provider: 'gemini',
  model: 'gemini-3.8-flash',
  base_url: null,
  api_key_hint: '1234',
  updated_at: '2026-09-29T10:00:00Z',
}

/**
 * Replaces fetch with a tiny fake backend: ``routes`` maps "METHOD /path" to a handler.
 * Unless a test says otherwise, ``TEST_USER`` is logged in.
 * Returns the recorded requests so tests can assert what was sent.
 */
export function mockApi(routes: Record<string, Handler>) {
  const handlers: Record<string, Handler> = {
    'GET /api/auth/me': () => json(TEST_USER),
    'GET /api/ai-settings': () => json(TEST_AI_SETTINGS),
    ...routes,
  }
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
