import { Link, Outlet } from 'react-router'

export function Layout() {
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
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>
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
