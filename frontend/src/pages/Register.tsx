import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Sword } from 'lucide-react'

/**
 * Registration page for Magic Maths.
 *
 * Renders a form with username/email/password fields. On submit, calls
 * `useAuth().register` which POSTs to the backend `/auth/register`
 * endpoint. On success, navigates to `/`. Displays API error messages.
 * Links to `/login` for existing users.
 *
 * @file Register.tsx
 * @route /register
 */
export default function Register() {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const { register } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await register(username, email, password)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erro ao cadastrar')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-magic-bg px-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center gap-3 mb-8">
          <Sword className="w-8 h-8 text-indigo-400" />
          <h1 className="text-2xl font-bold text-indigo-400">Magic Maths</h1>
        </div>
        <div className="card">
          <h2 className="text-xl font-semibold mb-6">Criar Conta</h2>
          {error && (
            <div className="bg-red-900/30 border border-red-700 text-red-300 px-4 py-2 rounded-lg mb-4 text-sm">
              {error}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Usuário</label>
              <input
                type="text"
                className="input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="label">Email</label>
              <input
                type="email"
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="label">Senha</label>
              <input
                type="password"
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>
            <button type="submit" className="btn-primary w-full">
              Cadastrar
            </button>
          </form>
          <p className="text-sm text-magic-muted text-center mt-4">
            Já tem conta?{' '}
            <Link to="/login" className="text-indigo-400 hover:text-indigo-300">
              Entrar
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
