import { useState, type FormEvent } from 'react'
import { useNavigate, useLocation } from 'react-router'
import { auth } from '../lib/api'

// Demo credential — prefilled, but any non-empty email + password is accepted.
const DEMO_EMAIL = 'admin@carolinafertility.com'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const from =
    (location.state as { from?: { pathname: string } } | null)?.from?.pathname ??
    '/'

  const [email, setEmail] = useState(DEMO_EMAIL)
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!email.trim() || !password.trim()) {
      setError('Enter an email and password to continue.')
      return
    }
    auth.signIn(email.trim())
    navigate(from, { replace: true })
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="text-xs uppercase tracking-widest text-zinc-700 font-semibold">
            embpred
          </div>
          <div className="text-[10px] uppercase tracking-wider text-zinc-400">
            demo
          </div>
        </div>

        <form
          onSubmit={onSubmit}
          className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6 space-y-4"
        >
          <div>
            <h1 className="text-lg font-semibold text-zinc-900">Sign in</h1>
            <p className="text-xs text-zinc-500 mt-0.5">
              Carolina's Fertility Clinic
            </p>
          </div>

          <label className="block">
            <span className="text-xs font-medium text-zinc-600">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
              className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-900 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 outline-none"
            />
          </label>

          <label className="block">
            <span className="text-xs font-medium text-zinc-600">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-900 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 outline-none"
            />
          </label>

          {error && <p className="text-xs text-rose-600">{error}</p>}

          <button
            type="submit"
            className="w-full rounded-md bg-zinc-900 text-white py-2 text-sm font-medium hover:bg-zinc-800 transition"
          >
            Sign in
          </button>

          <p className="text-[11px] text-zinc-400 text-center leading-relaxed">
            Mock authentication for this demo — any email + password works. In
            production this gates access to registered clinic devices.
          </p>
        </form>
      </div>
    </div>
  )
}
