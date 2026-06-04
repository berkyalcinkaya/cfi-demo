import { useQuery } from '@tanstack/react-query'
import { api, type IngestRun, type RunStatus } from '../lib/api'

function fmtTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const STATUS_STYLE: Record<RunStatus, string> = {
  succeeded: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  failed: 'bg-rose-50 text-rose-700 ring-rose-200',
  running: 'bg-amber-50 text-amber-700 ring-amber-200',
}

function StatusBadge({ status }: { status: RunStatus }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${STATUS_STYLE[status]}`}
    >
      {status}
    </span>
  )
}

function tpRange(r: IngestRun): string {
  if (r.tp_start === null || r.tp_end === null) return '—'
  return `${r.tp_start}–${r.tp_end}`
}

function IngestLog() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['ingest-runs'],
    queryFn: () => api.getIngestRuns(),
  })

  return (
    <section className="mb-10">
      <div className="flex items-baseline justify-between mb-1">
        <h2 className="text-sm font-semibold text-zinc-800">Ingest log</h2>
        <span className="text-xs text-zinc-500">
          nightly batch inference runs · newest first
        </span>
      </div>
      <p className="text-xs text-zinc-500 mb-3 max-w-2xl">
        Provenance ledger for the unattended pipeline — one run per embryo per
        model. Failed runs are resumable on the next nightly batch.
      </p>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-700 text-sm">
          {String(error)}
        </div>
      )}

      {isLoading && (
        <div className="space-y-1.5 animate-pulse">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-9 bg-zinc-100 rounded" />
          ))}
        </div>
      )}

      {data && (
        <div className="rounded-lg border border-zinc-200 bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-zinc-400 border-b border-zinc-100">
                <th className="px-3 py-2 font-medium">Embryo</th>
                <th className="px-3 py-2 font-medium">Model</th>
                <th className="px-3 py-2 font-medium">Timepoints</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium text-right">Rows</th>
                <th className="px-3 py-2 font-medium text-right">Finished</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-50">
              {data.map((r) => (
                <tr key={r.run_id} className="hover:bg-zinc-50/60">
                  <td className="px-3 py-2 text-zinc-800">
                    <span className="text-zinc-400">{r.patient_external_id}</span>{' '}
                    · {r.embryo_label}
                  </td>
                  <td className="px-3 py-2">
                    <span className="font-mono text-xs text-zinc-600">
                      {r.model_version}
                    </span>
                    {r.is_fabricated && (
                      <span className="ml-1.5 text-[10px] uppercase tracking-wide text-zinc-400">
                        fabricated
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-zinc-500">
                    {tpRange(r)}
                  </td>
                  <td className="px-3 py-2">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-600">
                    {r.rows_written.toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-zinc-500">
                    {fmtTime(r.finished_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function EvictedEmbryos() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['evicted'],
    queryFn: () => api.getEvicted(),
  })

  return (
    <section className="mb-10">
      <div className="flex items-baseline justify-between mb-1">
        <h2 className="text-sm font-semibold text-zinc-800">
          Recently evicted embryos
        </h2>
        <span className="text-xs text-zinc-500">
          local disk is a cache, not source of truth
        </span>
      </div>
      <p className="text-xs text-zinc-500 mb-3 max-w-2xl">
        Under disk pressure the evictor frees the oldest completed cases first.
        Predictions are never evicted; images fall back to cold storage and are
        re-fetched on demand.
      </p>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-700 text-sm">
          {String(error)}
        </div>
      )}

      {isLoading && (
        <div className="space-y-1.5 animate-pulse">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="h-14 bg-zinc-100 rounded" />
          ))}
        </div>
      )}

      {data && data.length === 0 && (
        <div className="rounded-lg border border-zinc-200 bg-white p-4 text-sm text-zinc-500">
          No evicted embryos — all images are on local disk.
        </div>
      )}

      {data && data.length > 0 && (
        <div className="rounded-lg border border-zinc-200 bg-white divide-y divide-zinc-100 overflow-hidden">
          {data.map((e) => (
            <div
              key={`${e.patient_external_id}/${e.embryo_label}`}
              className="flex items-center justify-between gap-4 px-4 py-3"
            >
              <div className="min-w-0">
                <div className="text-sm font-medium text-zinc-800">
                  {e.patient_name}{' '}
                  <span className="text-zinc-400">· {e.embryo_label}</span>
                </div>
                <div className="text-xs text-zinc-500 mt-0.5">
                  {e.num_images.toLocaleString()} images ·{' '}
                  <span className="inline-flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
                    {e.source_hint}
                  </span>
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className="text-[10px] uppercase tracking-wider text-zinc-400 leading-none">
                  evicted
                </div>
                <div className="text-sm tabular-nums text-zinc-600">
                  {fmtTime(e.evicted_at)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

const COMING_SOON = [
  { title: 'Audit Log', desc: 'Who viewed or changed which patient record, when.' },
  { title: 'User Management', desc: 'Invite embryologists, manage roles and device access.' },
  { title: 'Model Registry', desc: 'Versions, rollout status, and validation metrics per model.' },
]

function ComingSoon() {
  return (
    <section>
      <h2 className="text-sm font-semibold text-zinc-800 mb-3">Coming soon</h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {COMING_SOON.map((c) => (
          <div
            key={c.title}
            aria-disabled
            className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50/60 p-4 opacity-70 cursor-not-allowed select-none"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-zinc-700">{c.title}</h3>
              <span className="text-[10px] uppercase tracking-wider text-zinc-400 rounded-full bg-white ring-1 ring-zinc-200 px-2 py-0.5">
                Coming soon
              </span>
            </div>
            <p className="text-xs text-zinc-500 mt-2 leading-relaxed">{c.desc}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

export default function Admin() {
  return (
    <div className="max-w-5xl mx-auto px-8 py-6">
      <header className="mb-6 pb-4 border-b border-zinc-200">
        <div className="text-xs uppercase tracking-wider text-zinc-500 mb-1">
          Carolina's Fertility Clinic
        </div>
        <h1 className="text-2xl font-semibold text-zinc-900">Admin</h1>
        <div className="text-sm text-zinc-500 mt-0.5">
          Pipeline health & data operations
        </div>
      </header>

      <IngestLog />
      <EvictedEmbryos />
      <ComingSoon />

      <p className="mt-8 text-[11px] text-zinc-400">
        Ingest runs and eviction state are fabricated for this demo, backed by
        real <code>inference_runs</code> and <code>images.evicted_at</code>{' '}
        tables.
      </p>
    </div>
  )
}
