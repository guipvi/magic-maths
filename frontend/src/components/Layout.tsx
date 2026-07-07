import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { BarChart3, Layers, PackageOpen, LogOut, Sword, Plus } from 'lucide-react'

/**
 * Application shell / layout wrapper for Magic Maths.
 *
 * Renders a top navigation bar with the logo, nav links (Dashboard,
 * Novo Deck, Coleção), the current user's username, and a logout
 * button. Uses React Router's `<Outlet />` to render child routes.
 * Intended to be nested inside `<ProtectedRoute />`.
 *
 * @file Layout.tsx
 */
const navItems = [
  { path: '/', label: 'Dashboard', icon: BarChart3 },
  { path: '/decks/new', label: 'Novo Deck', icon: Plus },
  { path: '/collection', label: 'Coleção', icon: PackageOpen },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-magic-surface border-b border-magic-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-8">
              <Link to="/" className="flex items-center gap-2 text-xl font-bold text-indigo-400">
                <Sword className="w-6 h-6" />
                Magic Maths
              </Link>
              <nav className="hidden md:flex items-center gap-1">
                {navItems.map((item) => {
                  const Icon = item.icon
                  const isActive = location.pathname === item.path
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-indigo-600/20 text-indigo-300'
                          : 'text-magic-muted hover:text-magic-text hover:bg-slate-800'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      {item.label}
                    </Link>
                  )
                })}
              </nav>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-magic-muted hidden sm:block">{user?.username}</span>
              <button onClick={handleLogout} className="btn-secondary flex items-center gap-2 text-sm py-1.5">
                <LogOut className="w-4 h-4" />
                Sair
              </button>
            </div>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        <Outlet />
      </main>
    </div>
  )
}
