import React, { useEffect, useState } from 'react'
import { getContinuations } from '../api/client'
import type { OpeningExplorerData, OpeningContinuation } from '../api/client'
import type { Arrow } from './Board'

interface OpeningExplorerProps {
  fen: string | null
  onArrows: (arrows: Arrow[]) => void
}

function parseMoveEnds(move: string): [number | null, number | null] {
  const sep = move.includes('x') ? 'x' : '-'
  const parts = move.split(sep).map(Number)
  if (parts.length < 2 || parts.some(isNaN)) return [null, null]
  return [parts[0], parts[parts.length - 1]]
}

function scoreLabel(score: number | null): string {
  if (score === null) return '–'
  if (score > 150) return '+'
  if (score > 40) return '+='
  if (score >= -40) return '='
  if (score >= -150) return '=−'
  return '−'
}

function scoreColor(score: number | null): string {
  if (score === null) return '#6b7280'
  if (score > 100) return '#22c55e'
  if (score > 30) return '#86efac'
  if (score >= -30) return '#9ca3af'
  if (score >= -100) return '#fca5a5'
  return '#ef4444'
}

export default function OpeningExplorer({ fen, onArrows }: OpeningExplorerProps) {
  const [data, setData] = useState<OpeningExplorerData | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!fen) {
      setData(null)
      onArrows([])
      return
    }

    let cancelled = false
    setLoading(true)

    getContinuations(fen).then(result => {
      if (cancelled) return
      if (!result || result.total_games === 0) {
        setData(null)
        onArrows([])
      } else {
        setData(result)
        onArrows(buildArrows(result))
      }
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })

    return () => { cancelled = true }
  }, [fen])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-500 py-1">
        <div className="spinner" style={{ width: 12, height: 12 }} />
        Explorateur…
      </div>
    )
  }

  if (!data || data.total_games === 0) return null

  const maxFreq = Math.max(...data.continuations.map(c => c.frequency), 1)

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-amber-500">
          📊 Explorateur — {data.total_games} partie{data.total_games > 1 ? 's' : ''}
        </span>
        {data.engine_best && (
          <span className="text-xs text-gray-500">
            Moteur : <span className="font-mono text-green-400">{data.engine_best}</span>
          </span>
        )}
      </div>

      <div className="flex flex-col gap-0.5">
        {data.continuations.map((c, i) => (
          <ContinuationRow
            key={i}
            cont={c}
            maxFreq={maxFreq}
            isEngineBest={c.move === data.engine_best}
          />
        ))}
      </div>
    </div>
  )
}

function ContinuationRow({
  cont,
  maxFreq,
  isEngineBest,
}: {
  cont: OpeningContinuation
  maxFreq: number
  isEngineBest: boolean
}) {
  const barW = Math.round((cont.frequency / maxFreq) * 100)
  const sc = scoreLabel(cont.score)
  const scColor = scoreColor(cont.score)

  return (
    <div className="relative flex items-center gap-2 rounded px-2 py-1 text-xs overflow-hidden"
      style={{ background: 'rgba(255,255,255,0.03)' }}>
      {/* Frequency bar */}
      <div
        className="absolute left-0 top-0 bottom-0 rounded"
        style={{
          width: `${barW}%`,
          background: isEngineBest ? 'rgba(34,197,94,0.12)' : 'rgba(59,130,246,0.10)',
          transition: 'width 0.3s',
        }}
      />
      {/* Move */}
      <span className="relative font-mono font-semibold w-14 shrink-0"
        style={{ color: isEngineBest ? '#22c55e' : '#93c5fd' }}>
        {cont.move}
        {isEngineBest && <span className="ml-1 text-green-400">★</span>}
      </span>
      {/* Bar label: percent */}
      <span className="relative text-gray-400 w-8 text-right shrink-0">{cont.pct}%</span>
      {/* Frequency */}
      <span className="relative text-gray-600 shrink-0">{cont.frequency}p</span>
      {/* Score */}
      <span className="relative ml-auto font-mono font-bold shrink-0"
        style={{ color: scColor }}>{sc}</span>
    </div>
  )
}

function buildArrows(data: OpeningExplorerData): Arrow[] {
  const maxFreq = Math.max(...data.continuations.map(c => c.frequency), 1)
  const arrows: Arrow[] = []
  for (const c of data.continuations) {
    const [from, to] = parseMoveEnds(c.move)
    if (!from || !to) continue
    const ratio = c.frequency / maxFreq
    const isEngine = c.move === data.engine_best
    arrows.push({
      from,
      to,
      color: isEngine ? '#22c55e' : '#3b82f6',
      opacity: 0.35 + 0.55 * ratio,
      width: 1.2 + 3.0 * ratio,
    })
  }
  return arrows
}
