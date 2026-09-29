import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { TEST_USER, apiError, json, mockApi, renderRoute } from '../test/utils'

/** A fake backend with sessions: nobody is logged in until a login succeeds. */
function authBackend({ password = 'richtig-geheim', documents = () => json([]) } = {}) {
  let user: typeof TEST_USER | null = null
  const requests = mockApi({
    'GET /api/auth/me': () => (user ? json(user) : apiError('not_authenticated', 401)),
    'POST /api/auth/login': async (request) => {
      const body = (await request.json()) as { username: string; password: string }
      if (body.password !== password) return apiError('invalid_credentials', 401)
      user = TEST_USER
      return json(user)
    },
    'POST /api/auth/logout': () => {
      user = null
      return new Response(null, { status: 204 })
    },
    'GET /api/documents': () => (user ? documents() : apiError('not_authenticated', 401)),
  })
  return requests
}

async function logIn(password = 'richtig-geheim') {
  await userEvent.type(await screen.findByLabelText('Kullanıcı adı'), 'anna')
  await userEvent.type(screen.getByLabelText('Şifre'), password)
  await userEvent.click(screen.getByRole('button', { name: 'Giriş yap' }))
}

describe('Login', () => {
  it('shows the login page instead of the app when nobody is logged in', async () => {
    authBackend()

    renderRoute('/documents/2')

    expect(await screen.findByRole('heading', { name: 'Giriş yap' })).toBeInTheDocument()
    expect(screen.getByLabelText('Şifre')).toHaveAttribute('autocomplete', 'current-password')
    expect(screen.queryByRole('button', { name: /Dilbilgisi/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Sor/ })).not.toBeInTheDocument()
  })

  it('opens the app after logging in', async () => {
    const requests = authBackend()
    renderRoute('/')

    await logIn()

    expect(await screen.findByRole('heading', { name: 'Belgelerim' })).toBeInTheDocument()
    expect(screen.getByText(/anna/)).toBeInTheDocument()
    const login = requests.find((request) => request.url.endsWith('/api/auth/login'))!
    expect(await login.json()).toEqual({ username: 'anna', password: 'richtig-geheim' })
  })

  it('says so when the password is wrong', async () => {
    authBackend()
    renderRoute('/')

    await logIn('falsch-falsch')

    expect(await screen.findByRole('alert')).toHaveTextContent('Kullanıcı adı veya şifre yanlış.')
  })

  it('explains the pause after too many failed attempts', async () => {
    mockApi({
      'GET /api/auth/me': () => apiError('not_authenticated', 401),
      'POST /api/auth/login': () => apiError('too_many_login_attempts', 429),
    })
    renderRoute('/')

    await logIn()

    expect(await screen.findByRole('alert')).toHaveTextContent('Çok fazla hatalı deneme')
  })

  it('logs out and forgets the chat conversation', async () => {
    authBackend()
    localStorage.setItem('spektrum.chat', JSON.stringify([{ role: 'user', content: 'Hallo' }]))
    renderRoute('/')
    await logIn()
    await screen.findByRole('heading', { name: 'Belgelerim' })

    await userEvent.click(screen.getByRole('button', { name: 'Çıkış' }))

    expect(await screen.findByRole('heading', { name: 'Giriş yap' })).toBeInTheDocument()
    expect(localStorage.getItem('spektrum.chat')).toBeNull()
  })

  it('returns to the login page when the session ends while using the app', async () => {
    let expired = false
    mockApi({
      'GET /api/auth/me': () => json(TEST_USER),
      'GET /api/documents': () => (expired ? apiError('not_authenticated', 401) : json([])),
      'GET /api/documents/1': () => apiError('not_authenticated', 401),
      'GET /api/progress': () => apiError('not_authenticated', 401),
    })
    renderRoute('/documents/1')
    expired = true

    expect(await screen.findByRole('heading', { name: 'Giriş yap' })).toBeInTheDocument()
  })
})
