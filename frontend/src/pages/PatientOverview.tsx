import { useParams, Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { api, apiUrl, foldPloidy, type EmbryoCard } from '../lib/api'

function PloidyDot({ ploidy }: { ploidy: string | null | undefined }) {
  const folded = foldPloidy(ploidy)
  if (!folded) return <span className="text-xs text-zinc-400">ploidy —</span>
  const euploid = folded === 'euploid'
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium">
      <span
        className={`w-2.5 h-2.5 rounded-full ${euploid ? 'bg-emerald-500' : 'bg-rose-500'}`}
      />
      <span className={euploid ? 'text-emerald-700' : 'text-rose-700'}>
        {euploid ? 'Euploid' : 'Aneuploid'}
      </span>
    </span>
  )
}

function embryoHref(patientId: string, label: string) {
  // Always enter an embryo at the start of its timelapse (tp 0).
  return `/patients/${patientId}/embryos/${label}/timepoints/0`
}

function lbPercent(e: EmbryoCard): number | null {
  const lb = e.live_birth?.score
  return lb !== undefined ? Math.round(lb * 100) : null
}

function TopCard({
  embryo,
  rank,
  patientId,
}: {
  embryo: EmbryoCard
  rank: number
  patientId: string
}) {
  const pct = lbPercent(embryo)
  return (
    <Link
      to={embryoHref(patientId, embryo.label)}
      className="group block rounded-xl border border-zinc-200 bg-white overflow-hidden ring-1 ring-zinc-200 hover:ring-indigo-300 hover:border-indigo-300 hover:shadow-md transition-all"
    >
      <div className="relative aspect-square bg-zinc-100">
        {embryo.thumbnail && (
          <img
            src={apiUrl(embryo.thumbnail.url)}
            alt={embryo.label}
            className="absolute inset-0 w-full h-full object-cover"
          />
        )}
        <div className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-indigo-600 text-white text-xs font-semibold tabular-nums shadow-sm">
          #{rank}
        </div>
        <div className="absolute top-2 right-2 px-1.5 py-0.5 rounded bg-white/90 text-zinc-800 text-xs font-medium">
          {embryo.label}
        </div>
      </div>
      <div className="p-3 flex items-center justify-between">
        <PloidyDot ploidy={embryo.ploidy?.ploidy} />
        <div className="text-right">
          <div className="text-[10px] uppercase tracking-wider text-zinc-400 leading-none">
            live birth
          </div>
          <div className="text-lg font-semibold tabular-nums text-zinc-700 leading-tight">
            {pct !== null ? `${pct}%` : '—'}
          </div>
        </div>
      </div>
    </Link>
  )
}

function OtherRow({
  embryo,
  rank,
  patientId,
}: {
  embryo: EmbryoCard
  rank: number
  patientId: string
}) {
  const pct = lbPercent(embryo)
  return (
    <Link
      to={embryoHref(patientId, embryo.label)}
      className="flex items-center gap-3 px-3 py-2 hover:bg-zinc-50 transition-colors"
    >
      <span className="w-6 text-xs text-zinc-400 tabular-nums text-right">
        {rank}
      </span>
      <div className="relative w-10 h-10 rounded bg-zinc-100 overflow-hidden shrink-0">
        {embryo.thumbnail && (
          <img
            src={apiUrl(embryo.thumbnail.url)}
            alt={embryo.label}
            className="absolute inset-0 w-full h-full object-cover"
          />
        )}
      </div>
      <span className="text-sm font-medium text-zinc-800 w-16">
        {embryo.label}
      </span>
      <div className="flex-1">
        <PloidyDot ploidy={embryo.ploidy?.ploidy} />
      </div>
      <span className="text-sm text-zinc-400 tabular-nums">
        {pct !== null ? `${pct}%` : '—'}
      </span>
    </Link>
  )
}

function OverviewSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 animate-pulse">
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className="rounded-xl border border-zinc-200 bg-white overflow-hidden"
        >
          <div className="aspect-square bg-zinc-100" />
          <div className="p-3 h-12" />
        </div>
      ))}
    </div>
  )
}

export default function PatientOverview() {
  const { patientId = '' } = useParams()
  const { data, isLoading, error } = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => api.getPatient(patientId),
    enabled: Boolean(patientId),
  })

  if (error) {
    return (
      <div className="max-w-5xl mx-auto p-8">
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-700">
          {String(error)}
        </div>
      </div>
    )
  }

  const top = data?.embryos.slice(0, 3) ?? []
  const rest = data?.embryos.slice(3) ?? []
  const euploidCount =
    data?.embryos.filter((e) => foldPloidy(e.ploidy?.ploidy) === 'euploid')
      .length ?? 0
  const aneuploidCount =
    data?.embryos.filter((e) => foldPloidy(e.ploidy?.ploidy) === 'aneuploid')
      .length ?? 0

  return (
    <div className="max-w-5xl mx-auto px-8 py-6">
      <header className="mb-6 pb-4 border-b border-zinc-200">
        {data ? (
          <div className="flex items-end justify-between gap-4 flex-wrap">
            <div>
              <div className="text-xs uppercase tracking-wider text-zinc-500 mb-1">
                {data.office}
              </div>
              <h1 className="text-2xl font-semibold text-zinc-900">
                {data.name}
              </h1>
              <div className="text-sm text-zinc-500 mt-0.5">
                Age {data.age} · {data.embryos.length} embryos
              </div>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <span className="text-zinc-600">
                  <b className="tabular-nums">{euploidCount}</b> euploid
                </span>
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                <span className="text-zinc-600">
                  <b className="tabular-nums">{aneuploidCount}</b> aneuploid
                </span>
              </span>
              <Link
                to={`/patients/${data.id}/compare`}
                className="rounded-md border border-zinc-300 px-3 py-1.5 text-zinc-700 hover:border-zinc-500 hover:text-zinc-900 transition"
              >
                Compare timelines →
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-2 animate-pulse">
            <div className="h-3 bg-zinc-100 rounded w-32" />
            <div className="h-7 bg-zinc-100 rounded w-64" />
            <div className="h-4 bg-zinc-100 rounded w-48" />
          </div>
        )}
      </header>

      <section className="mb-8">
        <div className="flex items-baseline justify-between mb-1">
          <h2 className="text-sm font-semibold text-zinc-800">Top 3 picks</h2>
          <span className="text-xs text-zinc-500">
            click an embryo to view its timelapse
          </span>
        </div>
        <p className="text-xs text-zinc-500 mb-4 max-w-2xl">
          Ranked by predicted live birth. Model performance is strongest on the
          top 3; neural-net scores are not calibrated probabilities, so treat
          the numbers as guidance and the ploidy call as the harder signal.
        </p>
        {isLoading || !data ? (
          <OverviewSkeleton />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {top.map((e, i) => (
              <TopCard key={e.label} embryo={e} rank={i + 1} patientId={data.id} />
            ))}
          </div>
        )}
      </section>

      {rest.length > 0 && data && (
        <section>
          <h2 className="text-sm font-semibold text-zinc-800 mb-2">
            Other embryos
          </h2>
          <div className="rounded-lg border border-zinc-200 bg-white divide-y divide-zinc-100 overflow-hidden">
            {rest.map((e, i) => (
              <OtherRow
                key={e.label}
                embryo={e}
                rank={i + 4}
                patientId={data.id}
              />
            ))}
          </div>
        </section>
      )}

      <p className="mt-8 text-[11px] text-zinc-400">
        Live-birth and ploidy predictions are fabricated for this demo
        (model_version <code>fabricated-v0</code>).
      </p>
    </div>
  )
}
