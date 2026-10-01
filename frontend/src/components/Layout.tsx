import { Link, Outlet } from 'react-router'

import { useLogout, useMe, type User } from '../api/auth'
import { errorMessage } from '../api/client'
import { ChatPanel } from './ChatPanel'
import { GrammarHelp } from './GrammarHelp'
import { LoginPage } from './LoginPage'

function UserMenu({ user }: { user: User }) {
  const logout = useLogout()
  return (
    <div className="header__user">
      <span className="header__username" title="Giriş yapan kullanıcı">
        👤 {user.username}
      </span>
      <button
        type="button"
        className="header__logout"
        onClick={() => logout.mutate()}
        disabled={logout.isPending}
      >
        Çıkış
      </button>
    </div>
  )
}

export function Layout() {
  const me = useMe()
  const user = me.data

  let content
  if (me.isPending) content = <p className="muted">Yükleniyor…</p>
  else if (me.isError)
    content = (
      <p className="error" role="alert">
        {errorMessage(me.error)}
      </p>
    )
  else if (user) content = <Outlet />
  else content = <LoginPage />

  return (
    <>
      <header className="header">
        <div className="header__inner">
          <span className="header__logo" aria-hidden>
            🥨
          </span>
          <div>
            <Link to="/" className="header__brand">
              Almanca Kelime Antrenörü
            </Link>
            <p className="header__tagline">
              Deutsch lernen macht Spaß! · Her gün biraz, adım adım.
            </p>
          </div>
          {user && (
            <div className="header__actions">
              <Link to="/settings" className="header__settings" title="Yapay zekâ ayarları">
                ⚙️ <span className="header__settings-label">Ayarlar</span>
              </Link>
              <GrammarHelp />
              <UserMenu user={user} />
            </div>
          )}
        </div>
      </header>
      <main className="main">{content}</main>
      {user && <ChatPanel />}
    </>
  )
}

export function NotFound() {
  return (
    <div className="card empty">
      <span className="empty__emoji" aria-hidden>
        🧭
      </span>
      <h2>Sayfa bulunamadı</h2>
      <Link to="/">Belgelere dön</Link>
    </div>
  )
}
