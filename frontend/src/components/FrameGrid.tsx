import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { api, apiUrl, foldPloidy, type ComparisonEmbryo } from '../lib/api'

const DEFAULT_IMAGE_SIZE = 800
const FOCAL_COUNT_FALLBACK = 3

// A single shared frame index drives every embryo: one arrow press advances
// all of them by exactly one frame. Embryos shorter than the index hold on
// their final frame.
function frameFor(K: number, masterIdx: number): number {
  return Math.min(masterIdx, K - 1)
}

function GridCell({
  patientId,
  embryo,
  frame,
  focalIdx,
  rank,
  highlight,
}: {
  patientId: string
  embryo: ComparisonEmbryo
  frame: number
  focalIdx: number
  rank: number
  highlight: boolean
}) {
  const navigate = useNavigate()
  const [dims, setDims] = useState({ w: DEFAULT_IMAGE_SIZE, h: DEFAULT_IMAGE_SIZE })

  const { data: stack } = useQuery({
    queryKey: ['focal', patientId, embryo.label, frame],
    queryFn: () => api.getFocalStack(patientId, embryo.label, frame),
    placeholderData: keepPreviousData,
  })

  const focals = stack?.focal_stack ?? []
  const focal = focals[Math.min(focalIdx, focals.length - 1)]
  const ploidy = foldPloidy(embryo.ploidy)

  return (
    <button
      onClick={() =>
        navigate(
          `/patients/${patientId}/embryos/${embryo.label}/timepoints/${frame}`,
        )
      }
      title={`Open ${embryo.label} at tp ${frame}`}
      className={`group text-left rounded-lg overflow-hidden border bg-white transition ${
        highlight
          ? 'border-indigo-300 ring-1 ring-indigo-300'
          : 'border-zinc-200 hover:border-zinc-400'
      }`}
    >
      <div
        className={`flex items-center justify-between px-2 py-1 text-xs ${
          highlight ? 'bg-indigo-600 text-white' : 'bg-zinc-100 text-zinc-700'
        }`}
      >
        <span className="flex items-center gap-1.5 font-medium">
          {highlight && (
            <span className="tabular-nums opacity-90">#{rank}</span>
          )}
          {embryo.label}
          {ploidy && (
            <span
              className={`w-2 h-2 rounded-full ${
                ploidy === 'euploid' ? 'bg-emerald-400' : 'bg-rose-400'
              }`}
              title={ploidy}
            />
          )}
        </span>
        <span
          className={`tabular-nums ${highlight ? 'text-indigo-100' : 'text-zinc-400'}`}
        >
          {stack?.stage ?? '·'}
        </span>
      </div>

      <div
        className="relative bg-zinc-900"
        style={{ aspectRatio: `${dims.w}/${dims.h}` }}
      >
        {focal && (
          <img
            key={focal.url}
            src={apiUrl(focal.url)}
            alt={`${embryo.label} tp${frame}`}
            className="absolute inset-0 w-full h-full object-contain"
            onLoad={(e) => {
              const img = e.currentTarget
              if (
                img.naturalWidth > 0 &&
                (img.naturalWidth !== dims.w || img.naturalHeight !== dims.h)
              ) {
                setDims({ w: img.naturalWidth, h: img.naturalHeight })
              }
            }}
          />
        )}
        {stack?.bbox && (
          <svg
            className="absolute inset-0 w-full h-full pointer-events-none"
            viewBox={`0 0 ${dims.w} ${dims.h}`}
            preserveAspectRatio="none"
          >
            <rect
              x={stack.bbox.ul_x}
              y={stack.bbox.ul_y}
              width={stack.bbox.lr_x - stack.bbox.ul_x}
              height={stack.bbox.lr_y - stack.bbox.ul_y}
              fill="none"
              stroke="rgb(99 102 241)"
              strokeWidth="3"
              strokeDasharray="8 4"
            />
          </svg>
        )}
        <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/55 text-white text-[10px] tabular-nums">
          {frame}/{embryo.num_timepoints - 1}
        </div>
      </div>
    </button>
  )
}

export function FrameGrid({
  patientId,
  embryos,
}: {
  patientId: string
  embryos: ComparisonEmbryo[]
}) {
  const queryClient = useQueryClient()
  const maxK = Math.max(1, ...embryos.map((e) => e.num_timepoints))
  const focalCount = FOCAL_COUNT_FALLBACK
  const [masterIdx, setMasterIdx] = useState(0)
  const [focalIdx, setFocalIdx] = useState(1) // F0 (middle of -15/0/15)

  // Prefetch the neighbouring master positions for every embryo so left/right
  // scrolling stays instant across the whole grid.
  useEffect(() => {
    for (const offset of [-1, 1]) {
      const m = masterIdx + offset
      if (m < 0 || m > maxK - 1) continue
      for (const e of embryos) {
        const f = frameFor(e.num_timepoints, m)
        queryClient.prefetchQuery({
          queryKey: ['focal', patientId, e.label, f],
          queryFn: () => api.getFocalStack(patientId, e.label, f),
        })
      }
    }
  }, [masterIdx, maxK, embryos, patientId, queryClient])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowLeft':
        case 'ArrowRight': {
          e.preventDefault()
          const step = (e.shiftKey ? 10 : 1) * (e.key === 'ArrowRight' ? 1 : -1)
          setMasterIdx((i) => Math.max(0, Math.min(maxK - 1, i + step)))
          break
        }
        case 'ArrowUp':
        case 'ArrowDown': {
          e.preventDefault()
          const dir = e.key === 'ArrowUp' ? -1 : 1
          setFocalIdx((i) => Math.max(0, Math.min(focalCount - 1, i + dir)))
          break
        }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [maxK, focalCount])

  const focalDepth = [-15, 0, 15][focalIdx] ?? 0

  return (
    <div>
      <div className="sticky top-0 z-10 -mx-8 px-8 py-3 bg-zinc-50/90 backdrop-blur border-b border-zinc-200 mb-4">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="text-sm text-zinc-600 tabular-nums w-28">
            frame {masterIdx} / {maxK - 1}
          </span>
          <input
            type="range"
            min={0}
            max={maxK - 1}
            value={masterIdx}
            onChange={(e) => setMasterIdx(Number(e.target.value))}
            className="flex-1 min-w-[180px] accent-indigo-600"
            aria-label="timelapse progress"
          />
          <span className="text-sm font-mono text-zinc-700 w-12 text-center">
            F{focalDepth > 0 ? '+' : ''}
            {focalDepth}
          </span>
          <span className="flex items-center gap-3 text-xs text-zinc-500">
            <span className="flex items-center gap-1">
              <Kbd>←</Kbd>
              <Kbd>→</Kbd> time
            </span>
            <span className="flex items-center gap-1">
              <Kbd>↑</Kbd>
              <Kbd>↓</Kbd> focal
            </span>
            <span className="hidden sm:inline text-zinc-400">
              shift+← → jumps 10
            </span>
          </span>
        </div>
      </div>

      <div
        className="grid gap-3"
        style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))' }}
      >
        {embryos.map((e, i) => (
          <GridCell
            key={e.label}
            patientId={patientId}
            embryo={e}
            frame={frameFor(e.num_timepoints, masterIdx)}
            focalIdx={focalIdx}
            rank={i + 1}
            highlight={i < 3}
          />
        ))}
      </div>
    </div>
  )
}

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-block px-1.5 py-0.5 bg-white border border-zinc-300 rounded text-xs font-mono shadow-sm text-zinc-700">
      {children}
    </kbd>
  )
}
