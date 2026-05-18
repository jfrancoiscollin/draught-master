import React from 'react'
import type { SquareWeaknessCounts } from '../api/client'

// Shared 10×10 heatmap visualisation for the four geometric weakness
// families. Consumed by both the cross-game weakness profile
// (WeaknessPanel) and the per-game review (PedagogyPanel) so the two
// views render identically — same colours, same intensity scale, same
// in-tile count.

export type HeatMetric = 'all' | 'isolated' | 'backward' | 'holes' | 'outposts'

export const HEAT_METRIC_LABEL: Record<HeatMetric, string> = {
  all: 'Toutes',
  isolated: 'Isolés',
  backward: 'Retardés',
  holes: 'Trous',
  outposts: 'Postes',
}

export const HEAT_METRICS: ReadonlyArray<HeatMetric> = [
  'all', 'isolated', 'backward', 'holes', 'outposts',
]

export function HeatmapBoard({
  bySquare, metric, maxWidth = 220,
}: {
  bySquare: Record<string, SquareWeaknessCounts>
  metric: HeatMetric
  maxWidth?: number
}) {
  const counts: Record<number, number> = {}
  for (const [sqStr, bucket] of Object.entries(bySquare)) {
    const sq = Number(sqStr)
    counts[sq] = metric === 'all'
      // "all" sums the three real weaknesses; outposts are strengths
      // and counted separately. Matches dilf's narrator convention.
      ? bucket.isolated + bucket.backward + bucket.holes
      : bucket[metric]
  }
  const maxCount = Math.max(1, ...Object.values(counts))
  const isStrength = metric === 'outposts'
  const cells: React.ReactNode[] = []
  for (let r = 0; r < 10; r++) {
    for (let c = 0; c < 10; c++) {
      const isDark = (r + c) % 2 === 1
      const sq = isDark ? r * 5 + Math.floor(c / 2) + 1 : null
      const n = sq !== null ? (counts[sq] ?? 0) : 0
      const intensity = n > 0 ? Math.min(1, n / maxCount) : 0
      const bg = !isDark
        ? '#4b3b22'
        : intensity === 0
        ? '#1f2937'
        : isStrength
        ? `rgba(34, 197, 94, ${0.15 + 0.65 * intensity})`
        : `rgba(239, 68, 68, ${0.15 + 0.7 * intensity})`
      cells.push(
        <div
          key={`${r}-${c}`}
          title={sq !== null ? `Case ${sq} · ${n}×` : ''}
          style={{
            background: bg,
            aspectRatio: '1',
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'rgba(255,255,255,0.7)',
            fontSize: 9,
            fontWeight: 600,
            fontFamily: 'monospace',
            lineHeight: 1,
          }}
        >
          {isDark && n > 0 ? n : ''}
        </div>
      )
    }
  }
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(10, 1fr)',
      width: '100%',
      maxWidth,
      border: '2px solid #4b3b22',
      borderRadius: 3,
    }}>
      {cells}
    </div>
  )
}

export function HeatMetricSelector({
  value, onChange,
}: {
  value: HeatMetric
  onChange: (m: HeatMetric) => void
}) {
  return (
    <div className="flex gap-1 flex-wrap">
      {HEAT_METRICS.map(m => (
        <button
          key={m}
          onClick={() => onChange(m)}
          className={
            'px-1.5 py-0.5 rounded text-xs transition-colors ' +
            (value === m
              ? 'bg-amber-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600 cursor-pointer')
          }
        >
          {HEAT_METRIC_LABEL[m]}
        </button>
      ))}
    </div>
  )
}
