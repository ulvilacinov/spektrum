import { Link, Outlet } from 'react-router'

export function Layout() {
  return (
    <>
      <header className="header">
        <Link to="/" className="header__brand">
          Almanca Kelime Antrenörü
        </Link>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </>
  )
}

export function NotFound() {
  return (
    <div className="card">
      <h2>Sayfa bulunamadı</h2>
      <Link to="/">Belgelere dön</Link>
    </div>
  )
}
