import { useState, type FormEvent } from 'react'

import { useLogin } from '../api/auth'
import { errorMessage } from '../api/client'

export function LoginPage() {
  const login = useLogin()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    if (username.trim() && password) login.mutate({ username: username.trim(), password })
  }

  return (
    <form className="card login" onSubmit={submit} aria-labelledby="login-title">
      <span className="empty__emoji" aria-hidden>
        🥨
      </span>
      <h2 id="login-title">Giriş yap</h2>
      <p className="muted">Kelimelerine kaldığın yerden devam et.</p>
      <label className="login__field">
        Kullanıcı adı
        <input
          type="text"
          name="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          autoFocus
          required
        />
      </label>
      <label className="login__field">
        Şifre
        <input
          type="password"
          name="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
        />
      </label>
      <button type="submit" disabled={login.isPending || !username.trim() || !password}>
        {login.isPending ? 'Giriş yapılıyor…' : 'Giriş yap'}
      </button>
      {login.isError && (
        <p className="error" role="alert">
          {errorMessage(login.error)}
        </p>
      )}
    </form>
  )
}
