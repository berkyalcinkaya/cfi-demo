import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router'
import { useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { api, apiUrl } from '../lib/api'
import { MorphokineticBar } from '../components/MorphokineticBar'

const DEFAULT_IMAGE_SIZE = 800

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-block px-1.5 py-0.5 bg-white border border-zinc-300 rounded text-xs font-mono shadow-sm text-zinc-700">
      {children}
    </kbd>
  )
}

export default function FocalScroll() {
  const { patientId = '', embryoLabel = '', timepoint = '0' } = useParams()
  const tp = parseInt(timepoint, 10)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [focalIdx, setFocalIdx] = useState(1) // default F0 (middle of -15/0/15)
  const [imgDims, setImgDims] = useState<{ w: number; h: number }>({
    w: DEFAULT_IMAGE_SIZE,
    h: DEFAULT_IMAGE_SIZE,
  })

  const { data: patient } = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => api.getPatient(patientId),
    enabled: Boolean(patientId),
  })

  const {
    data: stack,
    isLoading: stackLoading,
    error: stackError,
  } = useQuery({
    queryKey: ['focal', patientId, embryoLabel, tp],
    queryFn: () => api.getFocalStack(patientId, embryoLabel, tp),
    enabled: Boolean(patientId && embryoLabel) && Number.isFinite(tp) && tp >= 0,
    placeholderData: keepPreviousData,
  })

  const { data: timeline } = useQuery({
    queryKey: ['timeline', patientId, embryoLabel],
    queryFn: () => api.getTimeline(patientId, embryoLabel),
    enabled: Boolean(patientId && embryoLabel),
  })

  const numTp = stack?.num_timepoints ?? 0
  const embryos = patient?.embryos ?? []

  useEffect(() => {
    document.title = `${embryoLabel} · tp ${tp} · embpred`
  }, [embryoLabel, tp])

  // Prefetch neighbor timepoints so left/right feels instant
  useEffect(() => {
    if (!numTp) return
    for (const offset of [-1, 1]) {
      const ntp = tp + offset
      if (ntp >= 0 && ntp < numTp) {
        queryClient.prefetchQuery({
          queryKey: ['focal', patientId, embryoLabel, ntp],
          queryFn: () => api.getFocalStack(patientId, embryoLabel, ntp),
        })
      }
    }
  }, [tp, numTp, patientId, embryoLabel, queryClient])

  // Preload all focal images for current tp so up/down has no flash
  useEffect(() => {
    if (!stack) return
    for (const f of stack.focal_stack) {
      const img = new Image()
      img.src = apiUrl(f.url)
    }
  }, [stack])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const focals = stack?.focal_stack
      if (!focals || focals.length === 0) return

      switch (e.key) {
        case 'ArrowUp':
        case 'ArrowDown': {
          e.preventDefault()
          if (e.ctrlKey || e.metaKey) {
            if (embryos.length === 0) return
            const idx = embryos.findIndex((x) => x.label === embryoLabel)
            if (idx === -1) return
            const dir = e.key === 'ArrowDown' ? 1 : -1
            const nextIdx = (idx + dir + embryos.length) % embryos.length
            const next = embryos[nextIdx]
            // Switching embryos starts at the beginning of its timelapse.
            navigate(
              `/patients/${patientId}/embryos/${next.label}/timepoints/0`,
            )
          } else {
            const dir = e.key === 'ArrowUp' ? -1 : 1
            setFocalIdx((i) => Math.max(0, Math.min(focals.length - 1, i + dir)))
          }
          break
        }
        case 'ArrowLeft':
        case 'ArrowRight': {
          e.preventDefault()
          const dir = e.key === 'ArrowRight' ? 1 : -1
          const newTp = tp + dir
          if (newTp >= 0 && newTp < numTp) {
            navigate(
              `/patients/${patientId}/embryos/${embryoLabel}/timepoints/${newTp}`,
            )
          }
          break
        }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [tp, numTp, patientId, embryoLabel, embryos, stack, navigate])

  const safeFocalIdx = Math.min(
    focalIdx,
    (stack?.focal_stack.length ?? 1) - 1,
  )
  const currentFocal = stack?.focal_stack[safeFocalIdx]

  const goTp = (next: number) =>
    navigate(`/patients/${patientId}/embryos/${embryoLabel}/timepoints/${next}`)

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
        <div className="text-sm text-zinc-500 tabular-nums">
          tp {tp} / {numTp || '…'}
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-8">
        <div className="text-center mb-3 min-h-[28px]">
          {stack?.stage && (
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-900 text-white text-sm font-medium">
              {stack.stage}
            </span>
          )}
        </div>

        <div
          className="relative bg-zinc-900 rounded-lg overflow-hidden"
          style={{ aspectRatio: `${imgDims.w}/${imgDims.h}` }}
        >
          {currentFocal && (
            <img
              key={currentFocal.url}
              src={apiUrl(currentFocal.url)}
              alt={`${embryoLabel} tp${tp} F${currentFocal.focal_depth}`}
              className="absolute inset-0 w-full h-full object-contain"
              onLoad={(e) => {
                const img = e.currentTarget
                if (
                  img.naturalWidth > 0 &&
                  (img.naturalWidth !== imgDims.w ||
                    img.naturalHeight !== imgDims.h)
                ) {
                  setImgDims({ w: img.naturalWidth, h: img.naturalHeight })
                }
              }}
            />
          )}
          {stack?.bbox && (
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              viewBox={`0 0 ${imgDims.w} ${imgDims.h}`}
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
          <button
            onClick={() => goTp(tp - 1)}
            disabled={tp <= 0}
            aria-label="previous timepoint"
            className="absolute left-3 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-black/40 hover:bg-black/70 text-white text-lg flex items-center justify-center disabled:opacity-10 disabled:cursor-not-allowed transition"
          >
            ‹
          </button>
          <button
            onClick={() => goTp(tp + 1)}
            disabled={!numTp || tp >= numTp - 1}
            aria-label="next timepoint"
            className="absolute right-3 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-black/40 hover:bg-black/70 text-white text-lg flex items-center justify-center disabled:opacity-10 disabled:cursor-not-allowed transition"
          >
            ›
          </button>
          {stackLoading && !stack && (
            <div className="absolute inset-0 flex items-center justify-center text-zinc-500 text-sm">
              loading…
            </div>
          )}
          {stackError && (
            <div className="absolute inset-0 flex items-center justify-center text-rose-300 text-sm">
              {String(stackError)}
            </div>
          )}
        </div>

        <div className="mt-4 flex items-center justify-center gap-2 text-sm">
          {stack?.focal_stack.map((f, i) => (
            <button
              key={f.focal_depth}
              onClick={() => setFocalIdx(i)}
              className={`px-3 py-1 rounded font-mono tabular-nums transition ${
                i === safeFocalIdx
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-white text-zinc-600 border border-zinc-200 hover:border-zinc-400'
              }`}
            >
              F{f.focal_depth > 0 ? '+' : ''}
              {f.focal_depth}
            </button>
          ))}
        </div>

        {timeline && (
          <div className="mt-8">
            <div className="flex items-baseline justify-between mb-2">
              <span className="text-xs uppercase tracking-wider text-zinc-500">
                morphokinetic timeline
              </span>
              <Link
                to={`/patients/${patientId}/embryos/${embryoLabel}/timeline`}
                className="text-xs text-zinc-500 hover:text-zinc-900"
              >
                full view →
              </Link>
            </div>
            <MorphokineticBar
              timeline={timeline}
              currentTp={tp}
              onJump={goTp}
            />
          </div>
        )}

        <div className="mt-10 flex justify-center gap-6 text-xs text-zinc-500">
          <span className="flex items-center gap-1">
            <Kbd>←</Kbd>
            <Kbd>→</Kbd>
            <span className="ml-1">time</span>
          </span>
          <span className="flex items-center gap-1">
            <Kbd>↑</Kbd>
            <Kbd>↓</Kbd>
            <span className="ml-1">focal</span>
          </span>
          <span className="flex items-center gap-1">
            <Kbd>⌘↑</Kbd>
            <Kbd>⌘↓</Kbd>
            <span className="ml-1">embryo</span>
          </span>
        </div>
      </div>
    </>
  )
}
