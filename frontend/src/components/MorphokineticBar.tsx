import { useLayoutEffect, useRef, useState } from 'react'
import { type Timeline } from '../lib/api'

export const STAGE_COLORS: Record<string, string> = {
  t1: 'bg-zinc-300',
  tPN: 'bg-sky-300',
  tPNf: 'bg-sky-400',
  t2: 'bg-blue-400',
  t3: 'bg-blue-400',
  t4: 'bg-blue-500',
  t5: 'bg-blue-500',
  t6: 'bg-blue-600',
  t7: 'bg-indigo-500',
  t8: 'bg-indigo-600',
  tM: 'bg-violet-500',
  tB: 'bg-emerald-400',
  tEB: 'bg-emerald-600',
  tEmpty: 'bg-zinc-200',
}

const STAGE_DEFAULT = 'bg-zinc-300'

type Segment = { stage: string; start: number; length: number }

function computeSegments(stream: Timeline['stream']): Segment[] {
  const out: Segment[] = []
  for (const p of stream) {
    const last = out[out.length - 1]
    if (
      last &&
      last.stage === p.stage &&
      last.start + last.length === p.timepoint
    ) {
      last.length++
    } else {
      out.push({ stage: p.stage, start: p.timepoint, length: 1 })
    }
  }
  return out
}

// Greedy row assignment so every milestone label is shown without overlap:
// place each label in the topmost row whose previous label has cleared its
// left edge. Morphokinetic milestones bunch up early (fast cell divisions),
// so single-row layouts drop short-lived stages like t3 entirely.
function assignRows(
  labels: { left: number; widthPct: number }[],
): number[] {
  const rowRightEdge: number[] = []
  return labels.map((l) => {
    const leftEdge = l.left - l.widthPct / 2
    for (let r = 0; r < rowRightEdge.length; r++) {
      if (leftEdge >= rowRightEdge[r]) {
        rowRightEdge[r] = l.left + l.widthPct / 2
        return r
      }
    }
    rowRightEdge.push(l.left + l.widthPct / 2)
    return rowRightEdge.length - 1
  })
}

export function MorphokineticBar({
  timeline,
  currentTp,
  onJump,
  height = 'h-3',
  showLabels = true,
}: {
  timeline: Timeline
  currentTp?: number
  onJump?: (tp: number) => void
  height?: string
  showLabels?: boolean
}) {
  const segments = computeSegments(timeline.stream)
  const K = timeline.num_timepoints
  const pct = (n: number) => `${(n / K) * 100}%`
  // Floor so a 1-frame stage in a ~700-frame timelapse stays a visible sliver.
  const MIN_SEG_PCT = 0.8

  const wrapRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)
  useLayoutEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setWidth(e.contentRect.width))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // Approximate label width in % of the bar (~6px per glyph at the 10px font).
  const labels = timeline.milestones.map((m) => {
    const left = (m.first_seen / K) * 100
    const approxPx = m.stage.length * 6 + 6
    const widthPct = width ? (approxPx / width) * 100 : 5
    return { ...m, left, widthPct }
  })
  const rows = showLabels ? assignRows(labels) : []
  const rowCount = rows.length ? Math.max(...rows) + 1 : 0
  const ROW_H = 13

  return (
    <div className="space-y-1" ref={wrapRef}>
      {showLabels && rowCount > 0 && (
        <div
          className="relative text-[10px] text-zinc-500 font-mono"
          style={{ height: rowCount * ROW_H }}
        >
          {labels.map((m, i) => (
            <button
              key={m.stage}
              onClick={onJump ? () => onJump(m.first_seen) : undefined}
              className={`absolute -translate-x-1/2 whitespace-nowrap leading-none ${
                onJump ? 'hover:text-zinc-900 cursor-pointer' : 'cursor-default'
              }`}
              style={{ left: pct(m.first_seen), top: rows[i] * ROW_H }}
              title={`${m.stage} · first seen tp ${m.first_seen} · ${m.frames_at_stage} frames`}
            >
              {m.stage}
            </button>
          ))}
        </div>
      )}

      <div
        className={`relative ${height} w-full rounded overflow-hidden bg-zinc-100`}
      >
        {segments.map((seg, i) => {
          const cls = STAGE_COLORS[seg.stage] ?? STAGE_DEFAULT
          const common = `absolute top-0 h-full ${cls}`
          const widthPctNum = Math.max((seg.length / K) * 100, MIN_SEG_PCT)
          const style = { left: pct(seg.start), width: `${widthPctNum}%` }
          const title = `${seg.stage} · tp ${seg.start}–${seg.start + seg.length - 1} (${seg.length} frames)`
          return onJump ? (
            <button
              key={i}
              onClick={() => onJump(seg.start)}
              className={`${common} hover:brightness-110 transition cursor-pointer`}
              style={style}
              title={title}
            />
          ) : (
            <div key={i} className={common} style={style} title={title} />
          )
        })}
        {currentTp !== undefined && (
          <div
            className="absolute top-0 h-full w-0.5 bg-white ring-1 ring-zinc-900 pointer-events-none"
            style={{ left: pct(currentTp), transform: 'translateX(-1px)' }}
          />
        )}
      </div>

      {showLabels && (
        <div className="flex justify-between text-[10px] text-zinc-400 tabular-nums">
          <span>0</span>
          {currentTp !== undefined && <span>tp {currentTp}</span>}
          <span>{K - 1}</span>
        </div>
      )}
    </div>
  )
}
