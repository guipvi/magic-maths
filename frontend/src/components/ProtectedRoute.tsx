import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

/**
 * Route guard component for Magic Maths.
 *
 * Checks `useAuth()` for an authenticated user. While auth state is
 * being resolved (loading), shows a spinner. If the user is
 * authenticated, renders child routes via `<Outlet />`. Otherwise,
 * redirects to `/login`.
 *
 * @file ProtectedRoute.tsx
 */
export default function ProtectedRoute() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-magic-bg">
        <div className="flex items-center gap-3 text-magic-muted">
          <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          Carregando...
        </div>
      </div>
    )
  }

  return user ? <Outlet /> : <Navigate to="/login" replace />
}
