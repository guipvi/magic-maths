import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './hooks/useAuth'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import DeckBuilder from './pages/DeckBuilder'
import DeckAnalysis from './pages/DeckAnalysis'
import Collection from './pages/Collection'

/**
 * Root application component for Magic Maths.
 *
 * Wraps all routes in `<AuthProvider>` for global auth state.
 * Defines two top-level public routes (`/login`, `/register`) and a
 * set of protected routes nested inside `<ProtectedRoute>` and
 * `<Layout>` (Dashboard, DeckBuilder, DeckAnalysis, Collection).
 * Unknown paths redirect to `/`.
 *
 * @file App.tsx
 */
export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/decks/new" element={<DeckBuilder />} />
            <Route path="/decks/:id" element={<DeckAnalysis />} />
            <Route path="/collection" element={<Collection />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
