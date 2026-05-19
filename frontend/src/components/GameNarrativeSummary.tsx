/**
 * Five cards summarising a finished game's analysis (J4).
 *
 * Backed by GET /api/pedagogy/game/{game_id}/narrative which calls
 * dilf.profile.narrate_game on the persisted verdicts. Each section
 * renders only when the underlying list/dict has content, so a
 * spotless game doesn't show empty placeholder cards.
 *
 *   1. Headline                 — outcome + half-move count + accuracy
 *   2. Phase summary            — opening / middlegame / endgame ACPL
 *   3. Tournants                — top-K worst moves (click → jump board)
 *   4. Faiblesses persistantes  — longest-running structural weaknesses
 *   5. Motifs + drills          — counts + click-to-drill links
 */

import { useEffect, useState } from 'react'
import { getGameNarrative } from '../api/client'
import type {
  GameNarrative,
  PersistentWeakness,
  TurningPoint,
} from '../api/client'

interface Props {
  gameId: string
  /** Locale forwarded to the narrator. The contract is "fr" today,
   *  "en" supported, anything else silently degrades to fr server-side. */
  lang?: string
  /** Click on a tournant row → jump the board to that half-move.
   *  Wired to the same handler the verdict-list rows use. */
  onJumpTo?: (halfMove: number) => void
  /** Click on a recommended drill / motif badge → open the motif drill
   *  page. Same handler used by PedagogyPanel's motif chips. */
  onMotifClick?: (slug: string) => void
  /** Click on a persistent-weakness row → highlight those squares on
   *  the board. Optional — when absent the row stays informational. */
  onWeaknessClick?: (squares: number[]) => void
}

export default function GameNarrativeSummary({
  gameId, lang = 'fr', onJumpTo, onMotifClick, onWeaknessClick,
}: Props) {
  const [narrative, setNarrative] = useState<GameNarrative | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    getGameNarrative(gameId, lang)
      .then(n => { if (!cancelled) setNarrative(n) })
      .catch(err => {
        if (cancelled) return
        const status = (err as { response?: { status?: number } })?.response?.status
        // 404 = game never analysed; surface a soft hint rather than
        // an error banner — the user can hit "Analyser la partie".
        if (status === 404) {
          setNarrative(null)
        } else {
          setError(String((err as Error).message ?? err))
        }
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [gameId, lang])

  if (loading) {
    return (
      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-3 text-xs text-gray-400">
        Chargement du résumé…
      </div>
    )
  }
  if (error) {
    return (
      <div className="bg-gray-800/50 border border-red-800/40 rounded-xl p-3 text-xs text-red-400">
        Erreur : {error}
      </div>
    )
  }
  if (!narrative) return null

  return (
    <div className="flex flex-col gap-2">
      {/* 1. Headline */}
      <div className="bg-gray-800/60 border border-amber-700/40 rounded-xl px-3 py-2">
        <p className="text-base font-bold text-amber-300">{narrative.headline}</p>
      </div>

      {/* 2. Phase summary */}
      {narrative.phase_summary.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700 rounded-xl px-3 py-2">
          <p className="text-xs font-semibold text-gray-300 mb-1.5">Par phase</p>
          <div className="flex flex-col gap-0.5 text-xs text-gray-300">
            {narrative.phase_summary.map(p => (
              <p key={p.phase}>{p.summary}</p>
            ))}
          </div>
        </div>
      )}

      {/* 3. Turning points */}
      {narrative.turning_points.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700 rounded-xl px-3 py-2">
          <p className="text-xs font-semibold text-gray-300 mb-1.5">Tournants de la partie</p>
          <div className="flex flex-col gap-1.5">
            {narrative.turning_points.map(tp => (
              <TurningPointRow key={tp.move_number} tp={tp} onJumpTo={onJumpTo} />
            ))}
          </div>
        </div>
      )}

      {/* 4. Persistent weaknesses */}
      {narrative.persistent_weaknesses.length > 0 && (
        <div className="bg-gray-800/40 border border-gray-700 rounded-xl px-3 py-2">
          <p className="text-xs font-semibold text-gray-300 mb-1.5">Faiblesses persistantes</p>
          <div className="flex flex-col gap-1 text-xs">
            {narrative.persistent_weaknesses.map((w, i) => (
              <WeaknessRow key={i} w={w} onClick={onWeaknessClick} />
            ))}
          </div>
        </div>
      )}

      {/* 5. Motifs + drills */}
      {(Object.keys(narrative.motifs_played).length > 0
        || Object.keys(narrative.motifs_missed).length > 0
        || narrative.strengths.length > 0) && (
        <div className="bg-gray-800/40 border border-gray-700 rounded-xl px-3 py-2 flex flex-col gap-2">
          {narrative.strengths.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-300 mb-1">Points forts</p>
              <ul className="text-xs text-gray-300 list-disc pl-4">
                {narrative.strengths.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
          {Object.keys(narrative.motifs_played).length > 0 && (
            <MotifChipRow
              label="Motifs joués"
              counts={narrative.motifs_played}
              colour="green"
              onClick={onMotifClick}
            />
          )}
          {Object.keys(narrative.motifs_missed).length > 0 && (
            <MotifChipRow
              label="Motifs ratés"
              counts={narrative.motifs_missed}
              colour="red"
              onClick={onMotifClick}
            />
          )}
          {narrative.recommended_drills.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-300 mb-1">
                À travailler
              </p>
              <div className="flex flex-wrap gap-1">
                {narrative.recommended_drills.map(slug => (
                  <button
                    key={slug}
                    onClick={() => onMotifClick?.(slug)}
                    disabled={!onMotifClick}
                    className="px-1.5 py-0.5 rounded text-xs bg-amber-700/30 text-amber-200 hover:bg-amber-700/50 disabled:opacity-50 cursor-pointer disabled:cursor-default"
                  >
                    {slug.replace(/_/g, ' ')} →
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────

function TurningPointRow({
  tp, onJumpTo,
}: {
  tp: TurningPoint
  onJumpTo?: (halfMove: number) => void
}) {
  const sideLabel = tp.side === 'white' ? '⬜' : '⬛'
  return (
    <button
      onClick={() => onJumpTo?.(tp.move_number)}
      disabled={!onJumpTo}
      className="text-left text-xs px-2 py-1 rounded hover:bg-gray-700/60 disabled:cursor-default cursor-pointer flex items-center gap-2"
      title={onJumpTo ? 'Aller à cette position' : undefined}
    >
      <span className="font-mono text-gray-200 w-16 flex-shrink-0">
        {sideLabel} {tp.notation}
      </span>
      <span className="font-bold text-red-400 w-12 flex-shrink-0">
        -{tp.delta_cp}cp
      </span>
      <span className="text-gray-300 flex-1 min-w-0 truncate">{tp.reason}</span>
    </button>
  )
}

function WeaknessRow({
  w, onClick,
}: {
  w: PersistentWeakness
  onClick?: (squares: number[]) => void
}) {
  return (
    <button
      onClick={() => onClick?.([w.square])}
      disabled={!onClick}
      className="text-left text-xs px-2 py-1 rounded hover:bg-gray-700/60 disabled:cursor-default cursor-pointer text-gray-300"
      title={onClick ? `Surligner la case ${w.square}` : undefined}
    >
      {w.summary}
    </button>
  )
}

function MotifChipRow({
  label, counts, colour, onClick,
}: {
  label: string
  counts: Record<string, number>
  colour: 'green' | 'red'
  onClick?: (slug: string) => void
}) {
  const bg = colour === 'green' ? 'bg-green-700/30 text-green-200 hover:bg-green-700/50'
                                 : 'bg-red-700/30 text-red-200 hover:bg-red-700/50'
  return (
    <div>
      <p className="text-xs font-semibold text-gray-300 mb-1">{label}</p>
      <div className="flex flex-wrap gap-1">
        {Object.entries(counts).map(([slug, n]) => (
          <button
            key={slug}
            onClick={() => onClick?.(slug)}
            disabled={!onClick}
            className={`px-1.5 py-0.5 rounded text-xs ${bg} disabled:opacity-50 cursor-pointer disabled:cursor-default`}
          >
            {slug.replace(/_/g, ' ')} <span className="font-mono">×{n}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
