import { type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api, auth } from '../lib/api'

function useActivePatientId(): string | undefined {
  const { pathname } = useLocation()
  return pathname.match(/^\/patients\/([^/]+)/)?.[1]
}

function PatientList({ activeId }: { activeId?: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['patients'],
    queryFn: () => api.listPatients(),
  })

  if (isLoading) {
    return (
      <div className="px-3 space-y-2 animate-pulse">
        <div className="h-10 bg-zinc-100 rounded" />
      </div>
    )
  }

  return (
    <nav className="px-2 space-y-0.5">
      {data?.map((p) => {
        const active = p.id === activeId
        return (
          <div key={p.id}>
            <Link
              to={`/patients/${p.id}`}
              className={`block rounded-md px-3 py-2 transition ${
                active
                  ? 'bg-zinc-900 text-white'
                  : 'text-zinc-700 hover:bg-zinc-100'
              }`}
            >
              <div className="text-sm font-medium truncate">{p.name}</div>
              <div
                className={`text-xs ${active ? 'text-zinc-300' : 'text-zinc-400'}`}
              >
                Age {p.age} · {p.num_embryos} embryos
              </div>
            </Link>
            {active && (
              <Link
                to={`/patients/${p.id}/compare`}
                className="block ml-3 mt-0.5 rounded-md px-3 py-1.5 text-xs text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900"
              >
                Compare timelines →
              </Link>
            )}
          </div>
        )
      })}
    </nav>
  )
}

export function AppShell({ children }: { children: ReactNode }) {
  const activeId = useActivePatientId()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const adminActive = pathname.startsWith('/admin')
  const user = auth.user()

  function handleSignOut() {
    auth.signOut()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen flex bg-zinc-50">
      <aside className="w-60 shrink-0 border-r border-zinc-200 bg-white flex flex-col">
        <Link
          to="/"
          className="px-4 py-3 border-b border-zinc-200 flex items-baseline justify-between"
        >
          <span className="text-xs uppercase tracking-widest text-zinc-700 font-semibold">
            embpred
          </span>
          <span className="text-[10px] uppercase tracking-wider text-zinc-400">
            demo
          </span>
        </Link>
        <div className="px-4 pt-4 pb-2 text-[10px] uppercase tracking-wider text-zinc-400">
          Patients
        </div>
        <div className="flex-1 overflow-y-auto pb-4">
          <PatientList activeId={activeId} />
        </div>
        <div className="border-t border-zinc-200 p-2 space-y-0.5">
          <Link
            to="/admin"
            className={`block rounded-md px-3 py-2 text-sm font-medium transition ${
              adminActive
                ? 'bg-zinc-900 text-white'
                : 'text-zinc-700 hover:bg-zinc-100'
            }`}
          >
            Admin
          </Link>
          <button
            onClick={handleSignOut}
            className="w-full text-left rounded-md px-3 py-2 text-sm text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 transition"
          >
            Sign out
          </button>
          {user && (
            <div
              className="px-3 pt-1 pb-0.5 text-[10px] text-zinc-400 truncate"
              title={user}
            >
              {user}
            </div>
          )}
        </div>
      </aside>
      <main className="flex-1 min-w-0">{children}</main>
    </div>
  )
}
