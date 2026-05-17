import React, { useState, useCallback, useEffect, useRef } from 'react'
import type { PedagogyAnalysis, VerdictOut } from '../api/client'
import { explainMovePedagogy } from '../api/client'

interface Props {
  gameId: string
  analysis: PedagogyAnalysis | null
  loading: boolean
  userSide: 'white' | 'black'
  lang: string
  onAnalyze: () => void
  error?: string | null
  onMotifClick?: (slug: string) => void
  /** Currently displayed half-move on the board (0 = initial position,
   *  1 = after the first move, etc.). Used to highlight & auto-scroll
   *  the matching verdict row. */
  currentHalfMove?: number
  /** Called when the user clicks a verdict row to jump the board to
   *  that half-move. Receives the verdict's ``move_number``. */
  onJumpTo?: (halfMove: number) => void
}

// ── Verdict styling ────────────────────────────────────────────────────────

const VERDICT_LABEL: Record<VerdictOut['verdict'], string> = {
  brilliant:  '!!',
  best:       '✓',
  excellent:  '✓',
  good:       '!',
  inaccuracy: '?!',
  mistake:    '?',
  blunder:    '??',
  forced:     '—',
  book:       '≡',
}

const VERDICT_COLOR: Record<VerdictOut['verdict'], string> = {
  brilliant:  '#f59e0b',
  best:       '#22c55e',
  excellent:  '#34d399',
  good:       '#86efac',
  inaccuracy: '#fbbf24',
  mistake:    '#f97316',
  blunder:    '#ef4444',
  forced:     '#6b7280',
  book:       '#818cf8',
}

const VERDICT_FR: Record<VerdictOut['verdict'], string> = {
  brilliant:  'Brillant',
  best:       'Meilleur coup',
  excellent:  'Excellent',
  good:       'Bon',
  inaccuracy: 'Imprécision',
  mistake:    'Erreur',
  blunder:    'Gaffe',
  forced:     'Forcé',
  book:       'Théorie',
}

// ── Helpers ────────────────────────────────────────────────────────────────

/** Format a score (pawn units, white's perspective) as a signed string. */
function fmtScore(scoreWhitePerspective: number): string {
  const sign = scoreWhitePerspective >= 0 ? '+' : ''
  return `${sign}${scoreWhitePerspective.toFixed(2)}`
}

/** Centipawn loss for one move (same formula as scan_advisor). */
function cpLoss(v: VerdictOut): number {
  return Math.round(Math.max(v.delta_winchance, 0) * 100)
}

/** Average centipawn loss across a set of verdicts. */
function acpl(vs: VerdictOut[]): number {
  const movable = vs.filter(v => v.verdict !== 'forced' && v.verdict !== 'book')
  if (!movable.length) return 0
  return Math.round(movable.reduce((s, v) => s + cpLoss(v), 0) / movable.length)
}

// ── Sub-components ─────────────────────────────────────────────────────────

function AccuracyBar({ accuracy }: { accuracy: number }) {
  const pct = Math.round(accuracy * 100)
  const color = pct >= 90 ? '#22c55e' : pct >= 75 ? '#86efac' : pct >= 60 ? '#fbbf24' : '#ef4444'
  return (
    <div className="flex items-center gap-2 flex-1">
      <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-bold tabular-nums" style={{ color }}>{pct}%</span>
    </div>
  )
}

function VerdictBadge({ verdict }: { verdict: VerdictOut['verdict'] }) {
  return (
    <span
      className="inline-block w-6 text-center font-bold text-xs flex-shrink-0"
      style={{ color: VERDICT_COLOR[verdict] }}
      title={VERDICT_FR[verdict]}
    >
      {VERDICT_LABEL[verdict]}
    </span>
  )
}

function MoveRow({
  verdict, gameId, lang, onMotifClick, isActive, onJump,
}: {
  verdict: VerdictOut
  gameId: string
  lang: string
  onMotifClick?: (slug: string) => void
  isActive: boolean
  onJump?: (halfMove: number) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [explanation, setExplanation] = useState<string | null>(null)
  const [loadingExpl, setLoadingExpl] = useState(false)
  const rowRef = useRef<HTMLDivElement | null>(null)

  // Scroll the active row into view whenever the board navigation moves
  // to a different half-move. ``nearest`` avoids jumping the page when
  // the row is already visible.
  useEffect(() => {
    if (isActive && rowRef.current) {
      rowRef.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [isActive])

  const fetchExplanation = useCallback(async () => {
    if (explanation === null) {
      setLoadingExpl(true)
      const text = await explainMovePedagogy(gameId, verdict.move_number, 'template', lang)
      setExplanation(text)
      setLoadingExpl(false)
    }
  }, [explanation, gameId, verdict.move_number, lang])

  const handleRowClick = useCallback(() => {
    onJump?.(verdict.move_number)
  }, [onJump, verdict.move_number])

  const handleToggleExpand = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    if (!expanded) void fetchExplanation()
    setExpanded(prev => !prev)
  }, [expanded, fetchExplanation])

  const cp = cpLoss(verdict)
  const showCp = cp >= 2 && verdict.verdict !== 'forced' && verdict.verdict !== 'book'
  // score_before is already white's perspective from the backend
  const scoreStr = fmtScore(verdict.score_before)
  const scoreColor = verdict.score_before >= 0 ? '#86efac' : '#fca5a5'

  return (
    <div
      ref={rowRef}
      className={`border-b border-gray-800 last:border-0 ${isActive ? 'bg-amber-700/30' : ''}`}
    >
      <div className="w-full flex items-center gap-1.5 px-2 py-1.5 hover:bg-gray-800/60 transition-colors">
        <button
          onClick={handleRowClick}
          className="flex-1 flex items-center gap-1.5 min-w-0 text-left cursor-pointer"
          title="Aller à cette position"
        >
          {/* Move number (white moves only) */}
          <span className="text-xs text-gray-600 w-4 tabular-nums flex-shrink-0 text-right">
            {verdict.side === 'white' ? `${Math.ceil(verdict.move_number / 2)}.` : ''}
          </span>

          {/* Side indicator */}
          <span className="text-xs w-4 text-center flex-shrink-0"
            style={{ color: verdict.side === 'white' ? '#e5e7eb' : '#6b7280' }}>
            {verdict.side === 'white' ? '⬜' : '⬛'}
          </span>

          {/* Move notation */}
          <span className={`font-mono text-xs flex-1 min-w-0 ${isActive ? 'text-white font-bold' : 'text-white'}`}>
            {verdict.move_notation}
          </span>

          {/* Scan score (white perspective) — cross-check column */}
          <span className="text-xs font-mono tabular-nums flex-shrink-0 w-12 text-right" style={{ color: scoreColor }}>
            {scoreStr}
          </span>

          {/* Verdict badge */}
          <VerdictBadge verdict={verdict.verdict} />

          {/* CP loss — mirrors scan_advisor ACPL metric */}
          {showCp ? (
            <span className="text-xs tabular-nums w-10 text-right flex-shrink-0"
              style={{ color: VERDICT_COLOR[verdict.verdict] }}>
              -{cp}cp
            </span>
          ) : (
            <span className="w-10 flex-shrink-0" />
          )}

          {/* Motif indicator */}
          {verdict.motifs.length > 0 && (
            <span className="text-xs text-indigo-400 flex-shrink-0"
              title={verdict.motifs.map(m => m.motif).join(', ')}>
              ◆{verdict.motifs.length}
            </span>
          )}
        </button>

        <button
          onClick={handleToggleExpand}
          className="text-gray-600 hover:text-gray-300 text-xs flex-shrink-0 w-4 text-center cursor-pointer"
          title={expanded ? 'Replier' : 'Déplier'}
        >
          {expanded ? '▲' : '▼'}
        </button>
      </div>

      {expanded && (
        <div className="px-3 pb-2 pt-0.5 bg-gray-900/60 text-xs text-gray-300 leading-relaxed">
          {/* Scan raw data */}
          <div className="flex gap-3 mb-1.5 text-gray-500 font-mono">
            <span>avant : <span className="text-gray-300">{fmtScore(verdict.score_before)}</span></span>
            <span>après : <span className="text-gray-300">{fmtScore(verdict.score_after)}</span></span>
            <span>Δwc : <span style={{ color: VERDICT_COLOR[verdict.verdict] }}>
              {verdict.delta_winchance >= 0 ? '-' : '+'}{Math.abs(Math.round(verdict.delta_winchance * 100))}%
            </span></span>
          </div>

          {/* Explanation */}
          {loadingExpl ? (
            <span className="text-gray-500 animate-pulse">Chargement…</span>
          ) : explanation ? (
            <p>{explanation}</p>
          ) : (
            <p className="text-gray-500 italic">Pas d'explication disponible.</p>
          )}

          {/* Motifs — clickable to open motif drill */}
          {verdict.motifs.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {verdict.motifs.map((m, i) => (
                <button
                  key={i}
                  onClick={e => { e.stopPropagation(); onMotifClick?.(m.motif) }}
                  className="px-1.5 py-0.5 rounded text-xs transition-opacity hover:opacity-80"
                  style={{
                    background: m.role === 'missed' ? 'rgba(239,68,68,0.15)' : 'rgba(99,102,241,0.15)',
                    color: m.role === 'missed' ? '#fca5a5' : '#a5b4fc',
                    cursor: onMotifClick ? 'pointer' : 'default',
                  }}
                  title={onMotifClick ? 'Travailler ce motif →' : undefined}
                >
                  {m.role === 'missed' ? '↗ ' : ''}{m.motif.replace(/_/g, ' ')}
                  {onMotifClick && ' →'}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export default function PedagogyPanel({ gameId, analysis, loading, userSide, lang, onAnalyze, error, onMotifClick, currentHalfMove, onJumpTo }: Props) {
  const [filter, setFilter] = useState<'all' | 'errors'>('all')

  if (!analysis && !loading) {
    return (
      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-3 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-300">Analyse pédagogique</span>
          <span className="text-xs text-gray-500">dilf · cross-check Scan</span>
        </div>
        {error ? (
          <div className="text-xs text-red-400 bg-red-900/20 border border-red-800/40 rounded p-2 font-mono break-all">
            {error}
          </div>
        ) : (
          <p className="text-xs text-gray-500">
            Verdicts dilf + score Scan brut par coup, pour valider la cohérence du framework.
          </p>
        )}
        <button
          onClick={onAnalyze}
          className="w-full py-1.5 rounded-lg bg-indigo-700 hover:bg-indigo-600 text-white text-xs font-medium transition-colors"
        >
          {error ? '↺ Réessayer' : '🎓 Analyser la partie'}
        </button>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-3 flex items-center gap-2">
        <div className="w-3 h-3 rounded-full bg-indigo-400 animate-pulse flex-shrink-0" />
        <span className="text-xs text-indigo-300">Analyse en cours… (~20s)</span>
      </div>
    )
  }

  const { verdicts } = analysis!
  const opponentSide = userSide === 'white' ? 'black' : 'white'
  const userVerdicts = verdicts.filter(v => v.side === userSide)
  const oppVerdicts  = verdicts.filter(v => v.side === opponentSide)

  const shown = filter === 'errors'
    ? verdicts.filter(v => ['inaccuracy', 'mistake', 'blunder'].includes(v.verdict))
    : verdicts

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl flex flex-col">

      {/* Summary header */}
      <div className="px-3 py-2 border-b border-gray-700 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-300">Analyse pédagogique</span>
          <span className="text-xs text-gray-500">{verdicts.length} demi-coups · Scan</span>
        </div>

        {/* Accuracy + ACPL bars — one per side */}
        {([
          { side: userSide,     label: userSide === 'white' ? '⬜' : '⬛', vs: userVerdicts },
          { side: opponentSide, label: opponentSide === 'white' ? '⬜' : '⬛', vs: oppVerdicts },
        ] as const).map(({ side, label, vs }) => {
          const bl  = vs.filter(v => v.verdict === 'blunder').length
          const mk  = vs.filter(v => v.verdict === 'mistake').length
          const acc = vs.length
            ? 1 - vs.reduce((s, v) => s + Math.max(v.delta_winchance, 0), 0) / vs.length
            : 1
          const a = acpl(vs)
          return (
            <div key={side} className="flex items-center gap-1.5">
              <span className="text-xs w-4 flex-shrink-0">{label}</span>
              <AccuracyBar accuracy={acc} />
              {/* ACPL — same metric as the Scan annotation panel */}
              <span className="text-xs tabular-nums font-mono text-gray-400 w-12 text-right flex-shrink-0"
                title="Perte moyenne en centipions (même calcul que l'annotation Scan)">
                {a}cp
              </span>
              {bl > 0 && <span className="text-xs font-bold flex-shrink-0" style={{ color: '#ef4444' }}>{bl}??</span>}
              {mk > 0 && <span className="text-xs font-bold flex-shrink-0" style={{ color: '#f97316' }}>{mk}?</span>}
            </div>
          )
        })}

        {/* Column headers */}
        <div className="flex items-center gap-1.5 text-xs text-gray-600 border-t border-gray-800 pt-1">
          <span className="w-4" />
          <span className="w-4" />
          <span className="flex-1">coup</span>
          <span className="w-12 text-right">éval.</span>
          <span className="w-6 text-center">verdict</span>
          <span className="w-10 text-right">Δcp</span>
          <span className="w-4" />
          <span className="w-3" />
        </div>
      </div>

      {/* Filter toggle */}
      <div className="flex border-b border-gray-700">
        {(['all', 'errors'] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`flex-1 py-1 text-xs font-medium transition-colors ${
              filter === f ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300'
            }`}>
            {f === 'all' ? 'Tous les coups' : 'Erreurs uniquement'}
          </button>
        ))}
      </div>

      {/* Move list */}
      <div className="overflow-y-auto max-h-72">
        {shown.length === 0 ? (
          <p className="text-xs text-center text-gray-500 py-4">Aucune erreur détectée 🎉</p>
        ) : (
          shown.map(v => (
            <MoveRow
              key={v.move_number}
              verdict={v}
              gameId={gameId}
              lang={lang}
              onMotifClick={onMotifClick}
              isActive={currentHalfMove === v.move_number}
              onJump={onJumpTo}
            />
          ))
        )}
      </div>
    </div>
  )
}
