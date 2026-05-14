import React, { useState, useCallback } from 'react'
import type { PedagogyAnalysis, VerdictOut } from '../api/client'
import { explainMovePedagogy } from '../api/client'

interface Props {
  gameId: string
  analysis: PedagogyAnalysis | null
  loading: boolean
  userSide: 'white' | 'black'
  lang: string
  onAnalyze: () => void
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

// ── Sub-components ─────────────────────────────────────────────────────────

function AccuracyBar({ accuracy }: { accuracy: number }) {
  const pct = Math.round(accuracy * 100)
  const color = pct >= 90 ? '#22c55e' : pct >= 75 ? '#86efac' : pct >= 60 ? '#fbbf24' : '#ef4444'
  return (
    <div className="flex items-center gap-2 flex-1">
      <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-sm font-bold tabular-nums" style={{ color }}>{pct}%</span>
    </div>
  )
}

function VerdictBadge({ verdict }: { verdict: VerdictOut['verdict'] }) {
  return (
    <span
      className="inline-block w-6 text-center font-bold text-xs"
      style={{ color: VERDICT_COLOR[verdict] }}
      title={VERDICT_FR[verdict]}
    >
      {VERDICT_LABEL[verdict]}
    </span>
  )
}

function MoveRow({
  verdict,
  gameId,
  lang,
}: {
  verdict: VerdictOut
  gameId: string
  lang: string
}) {
  const [expanded, setExpanded] = useState(false)
  const [explanation, setExplanation] = useState<string | null>(null)
  const [loadingExpl, setLoadingExpl] = useState(false)

  const handleToggle = useCallback(async () => {
    if (!expanded && explanation === null) {
      setLoadingExpl(true)
      const text = await explainMovePedagogy(gameId, verdict.move_number, 'template', lang)
      setExplanation(text)
      setLoadingExpl(false)
    }
    setExpanded(prev => !prev)
  }, [expanded, explanation, gameId, verdict.move_number, lang])

  const delta = Math.abs(verdict.delta_winchance)
  const showDelta = delta >= 0.02 && verdict.verdict !== 'forced' && verdict.verdict !== 'book'

  return (
    <div className="border-b border-gray-800 last:border-0">
      <button
        onClick={handleToggle}
        className="w-full flex items-center gap-2 px-2 py-1.5 hover:bg-gray-800/60 transition-colors text-left"
      >
        <span className="text-xs text-gray-500 w-4 tabular-nums flex-shrink-0">
          {verdict.side === 'white' ? Math.ceil(verdict.move_number / 2) + '.' : ''}
        </span>
        <span
          className="text-xs font-medium w-5 text-center flex-shrink-0"
          style={{ color: verdict.side === 'white' ? '#e5e7eb' : '#9ca3af' }}
        >
          {verdict.side === 'white' ? '⬜' : '⬛'}
        </span>
        <span className="font-mono text-xs text-white flex-1">{verdict.move_notation}</span>
        <VerdictBadge verdict={verdict.verdict} />
        {showDelta && (
          <span className="text-xs tabular-nums" style={{ color: VERDICT_COLOR[verdict.verdict] }}>
            -{Math.round(delta * 100)}%
          </span>
        )}
        {verdict.motifs.length > 0 && (
          <span className="text-xs text-indigo-400" title={verdict.motifs.map(m => m.motif).join(', ')}>
            ◆{verdict.motifs.length}
          </span>
        )}
        <span className="text-gray-600 text-xs">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="px-3 pb-2 pt-0.5 bg-gray-900/60 text-xs text-gray-300 leading-relaxed">
          {loadingExpl ? (
            <span className="text-gray-500 animate-pulse">Chargement…</span>
          ) : explanation ? (
            <p>{explanation}</p>
          ) : (
            <p className="text-gray-500 italic">Pas d'explication disponible.</p>
          )}
          {verdict.motifs.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {verdict.motifs.map((m, i) => (
                <span
                  key={i}
                  className="px-1.5 py-0.5 rounded text-xs"
                  style={{
                    background: m.role === 'missed' ? 'rgba(239,68,68,0.15)' : 'rgba(99,102,241,0.15)',
                    color: m.role === 'missed' ? '#fca5a5' : '#a5b4fc',
                  }}
                >
                  {m.role === 'missed' ? '↗ ' : ''}{m.motif.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export default function PedagogyPanel({ gameId, analysis, loading, userSide, lang, onAnalyze }: Props) {
  const [filter, setFilter] = useState<'all' | 'errors'>('all')

  if (!analysis && !loading) {
    return (
      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-3 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-300">Analyse pédagogique</span>
          <span className="text-xs text-gray-500">dilf</span>
        </div>
        <p className="text-xs text-gray-500">
          Analyse coup par coup avec détection des motifs tactiques.
        </p>
        <button
          onClick={onAnalyze}
          className="w-full py-1.5 rounded-lg bg-indigo-700 hover:bg-indigo-600 text-white text-xs font-medium transition-colors"
        >
          🎓 Analyser la partie
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

  const { verdicts, summary } = analysis!
  const userVerdicts = verdicts.filter(v => v.side === userSide)
  const opponentSide = userSide === 'white' ? 'black' : 'white'
  const oppVerdicts = verdicts.filter(v => v.side === opponentSide)

  const shown = filter === 'errors'
    ? verdicts.filter(v => ['inaccuracy', 'mistake', 'blunder'].includes(v.verdict))
    : verdicts

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl flex flex-col">
      {/* Header summary */}
      <div className="px-3 py-2 border-b border-gray-700 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-300">Analyse pédagogique</span>
          <span className="text-xs text-gray-500">{verdicts.length} demi-coups</span>
        </div>

        {/* Accuracy bars */}
        {[
          { side: userSide, label: userSide === 'white' ? '⬜' : '⬛', vs: userVerdicts },
          { side: opponentSide, label: opponentSide === 'white' ? '⬜' : '⬛', vs: oppVerdicts },
        ].map(({ side, label, vs }) => {
          const bl = vs.filter(v => v.verdict === 'blunder').length
          const mk = vs.filter(v => v.verdict === 'mistake').length
          const acc = vs.length
            ? 1 - vs.reduce((s, v) => s + Math.max(v.delta_winchance, 0), 0) / vs.length
            : 1
          return (
            <div key={side} className="flex items-center gap-1.5">
              <span className="text-xs w-4">{label}</span>
              <AccuracyBar accuracy={acc} />
              {bl > 0 && <span className="text-xs font-bold" style={{ color: '#ef4444' }}>{bl}??</span>}
              {mk > 0 && <span className="text-xs font-bold" style={{ color: '#f97316' }}>{mk}?</span>}
            </div>
          )
        })}
      </div>

      {/* Filter toggle */}
      <div className="flex border-b border-gray-700">
        {(['all', 'errors'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`flex-1 py-1 text-xs font-medium transition-colors ${
              filter === f ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {f === 'all' ? 'Tous les coups' : 'Erreurs uniquement'}
          </button>
        ))}
      </div>

      {/* Move list */}
      <div className="overflow-y-auto max-h-64">
        {shown.length === 0 ? (
          <p className="text-xs text-center text-gray-500 py-4">Aucune erreur détectée 🎉</p>
        ) : (
          shown.map(v => (
            <MoveRow key={v.move_number} verdict={v} gameId={gameId} lang={lang} />
          ))
        )}
      </div>
    </div>
  )
}
