import { useParams, useNavigate, Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { MorphokineticBar } from '../components/MorphokineticBar'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export default function Timeline() {
  const { patientId = '', embryoLabel = '' } = useParams()
  const navigate = useNavigate()

  const { data: patient } = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => api.getPatient(patientId),
    enabled: Boolean(patientId),
  })

  const {
    data: timeline,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['timeline', patientId, embryoLabel],
    queryFn: () => api.getTimeline(patientId, embryoLabel),
    enabled: Boolean(patientId && embryoLabel),
  })

  const embryo = patient?.embryos.find((e) => e.label === embryoLabel)
  const jump = (tp: number) =>
    navigate(`/patients/${patientId}/embryos/${embryoLabel}/timepoints/${tp}`)

  return (
    <>
      <div className="border-b border-zinc-200 bg-white px-6 py-3 flex items-center justify-between">
        <Link
          to={`/patients/${patientId}`}
          className="text-sm text-zinc-500 hover:text-zinc-900"
        >
          ← Overview
        </Link>
        <div className="text-sm text-zinc-700">
          <span className="font-medium">{embryoLabel}</span>
          {patient && (
            <span className="text-zinc-400 ml-2">· {patient.name}</span>
          )}
        </div>
        <Link
          to={`/patients/${patientId}/embryos/${embryoLabel}/timepoints/0`}
          className="text-sm text-zinc-500 hover:text-zinc-900"
        >
          focal scroll →
        </Link>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-700">
            {String(error)}
          </div>
        )}

        {embryo && (
          <header className="mb-6">
            <h1 className="text-xl font-semibold text-zinc-900">
              {embryo.label} — morphokinetic timeline
            </h1>
            <div className="text-sm text-zinc-500 mt-1">
              {embryo.num_timepoints} timepoints · imaged{' '}
              {formatDate(embryo.date_seeded)} · well {embryo.well ?? '—'}
            </div>
          </header>
        )}

        {timeline && (
          <section className="bg-white rounded-lg border border-zinc-200 p-6 mb-6">
            <MorphokineticBar
              timeline={timeline}
              currentTp={embryo?.thumbnail?.timepoint}
              onJump={jump}
              height="h-5"
            />
            <p className="text-xs text-zinc-400 mt-3">
              click any segment to jump into the focal scroll at that frame
            </p>
          </section>
        )}

        {timeline && (
          <section className="bg-white rounded-lg border border-zinc-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 text-zinc-500 text-xs uppercase tracking-wider">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">stage</th>
                  <th className="text-right px-4 py-2 font-medium">first seen</th>
                  <th className="text-right px-4 py-2 font-medium">
                    frames at stage
                  </th>
                  <th className="w-12"></th>
                </tr>
              </thead>
              <tbody>
                {timeline.milestones.map((m) => (
                  <tr key={m.stage} className="border-t border-zinc-100">
                    <td className="px-4 py-2 font-mono text-zinc-800">
                      {m.stage}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums text-zinc-700">
                      {m.first_seen}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums text-zinc-700">
                      {m.frames_at_stage}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button
                        onClick={() => jump(m.first_seen)}
                        className="text-xs text-indigo-600 hover:text-indigo-900"
                      >
                        view →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {isLoading && !timeline && (
          <div className="text-sm text-zinc-500">loading…</div>
        )}
      </div>
    </>
  )
}
