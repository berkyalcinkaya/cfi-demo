import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api, foldPloidy, type ComparisonEmbryo, type Timeline } from '../lib/api'
import { MorphokineticBar, STAGE_COLORS } from '../components/MorphokineticBar'
import { FrameGrid } from '../components/FrameGrid'

type Tab = 'timelines' | 'grid'

// Stages shown in the legend, in developmental order.
const LEGEND_STAGES = [
  't1',
  'tPN',
  'tPNf',
  't2',
  't3',
  't4',
  't5',
  't6',
  't7',
  't8',
  'tM',
  'tB',
  'tEB',
]

function asTimeline(patientId: string, e: ComparisonEmbryo): Timeline {
  return {
    patient_id: patientId,
    embryo: e.label,
    num_timepoints: e.num_timepoints,
    stream: e.stream,
    milestones: e.milestones,
  }
}

function PloidyDot({ ploidy }: { ploidy: string | null }) {
  const folded = foldPloidy(ploidy)
  if (!folded) return <span className="w-2.5 h-2.5 rounded-full bg-zinc-300" />
  return (
    <span
      className={`w-2.5 h-2.5 rounded-full ${folded === 'euploid' ? 'bg-emerald-500' : 'bg-rose-500'}`}
      title={folded}
    />
  )
}

const TABS: { id: Tab; label: string }[] = [
  { id: 'timelines', label: 'Timelines' },
  { id: 'grid', label: 'Frame grid' },
]

export default function Comparison() {
  const { patientId = '' } = useParams()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('timelines')

  const { data, isLoading, error } = useQuery({
    queryKey: ['comparison', patientId],
    queryFn: () => api.getComparison(patientId),
    enabled: Boolean(patientId),
  })

  return (
    <>
      <div className="border-b border-zinc-200 bg-white px-6 flex items-center justify-between">
        <Link
          to={`/patients/${patientId}`}
          className="text-sm text-zinc-500 hover:text-zinc-900 py-3"
        >
          ← Overview
        </Link>
        <div className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-3 py-3 text-sm border-b-2 -mb-px transition ${
                tab === t.id
                  ? 'border-indigo-600 text-zinc-900 font-medium'
                  : 'border-transparent text-zinc-500 hover:text-zinc-800'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <span className="w-16" />
      </div>

      <div className="max-w-5xl mx-auto px-8 py-6">
        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-700">
            {String(error)}
          </div>
        )}

        {isLoading && (
          <div className="space-y-4 animate-pulse">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-8 bg-zinc-100 rounded" />
            ))}
          </div>
        )}

        {data && tab === 'grid' && (
          <FrameGrid patientId={patientId} embryos={data.embryos} />
        )}

        {data && tab === 'timelines' && (
          <>
            <p className="text-sm text-zinc-500 mb-5 max-w-2xl">
              Every embryo's timeline is normalized to its full length (0–100%),
              so the <em>proportion</em> of development spent in each stage lines
              up across embryos regardless of how many frames each was imaged
              for. Embryos are ordered by predicted live birth. Click any segment
              to open that frame.
            </p>

            <div className="flex flex-wrap gap-x-3 gap-y-1 mb-6">
              {LEGEND_STAGES.map((s) => (
                <span
                  key={s}
                  className="inline-flex items-center gap-1.5 text-xs"
                >
                  <span
                    className={`w-3 h-3 rounded-sm ${STAGE_COLORS[s] ?? 'bg-zinc-300'}`}
                  />
                  <span className="font-mono text-zinc-600">{s}</span>
                </span>
              ))}
            </div>

            <div className="space-y-3">
              {data.embryos.map((e, i) => (
              <div
                key={e.label}
                className="flex items-center gap-4 bg-white rounded-lg border border-zinc-200 px-4 py-3"
              >
                <div className="flex items-center gap-2 w-28 shrink-0">
                  <span className="text-xs text-zinc-400 tabular-nums w-4 text-right">
                    {i + 1}
                  </span>
                  <PloidyDot ploidy={e.ploidy} />
                  <Link
                    to={`/patients/${patientId}/embryos/${e.label}/timeline`}
                    className="text-sm font-medium text-zinc-800 hover:text-indigo-600"
                  >
                    {e.label}
                  </Link>
                </div>
                <div className="flex-1 min-w-0">
                  <MorphokineticBar
                    timeline={asTimeline(patientId, e)}
                    height="h-4"
                    showLabels={false}
                    onJump={(tp) =>
                      navigate(
                        `/patients/${patientId}/embryos/${e.label}/timepoints/${tp}`,
                      )
                    }
                  />
                </div>
                <div className="w-12 shrink-0 text-right text-xs text-zinc-400 tabular-nums">
                  {e.num_timepoints}f
                </div>
              </div>
            ))}
            </div>
          </>
        )}
      </div>
    </>
  )
}
