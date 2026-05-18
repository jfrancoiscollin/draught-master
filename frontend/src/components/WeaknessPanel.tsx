import React, { useState, useEffect } from 'react'
import { getUserProfile, getMotifDebug, getWeaknessHeatmap } from '../api/client'
import type { MotifWeakness, UserProfile, MotifDebug, WeaknessHeatmap } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

const MOTIF_NAME_FR: Record<string, string> = {
  coup_royal: 'Coup royal',
  coup_turc: 'Coup turc',
  coup_de_talon: 'Coup du talon',
  envoi_a_dame: 'Envoi à dame',
  sacrifice: 'Sacrifice',
  prise_max_ratee: 'Prise maximale ratée',
  coup_philippe: 'Coup Philippe',
  coup_raphael: 'Coup Raphaël',
  coup_express: 'Coup express',
  coup_bonnard: 'Coup Bonnard',
}

interface Props {
  onMotifClick: (slug: string) => void
  refreshKey?: number
}

function FreqBar({ score, max }: { score: number; max: number }) {
  const pct = max > 0 ? Math.round((score / max) * 100) : 0
  return (
    <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
      <div className="h-full rounded-full bg-amber-500 transition-all" style={{ width: `${pct}%` }} />
    </div>
  )
}

// ── Weakness heatmap ─────────────────────────────────────────────────────
// Renders the 50 dark squares of the FMJD board, each tinted by how often
// the selected weakness metric (or sum of all) appeared on that square
// across the user's recent games. Empty squares stay neutral; high-count
// squares glow amber (or green for outposts — those are strengths).

type HeatMetric = 'all' | 'isolated' | 'backward' | 'holes' | 'outposts'

const HEAT_METRIC_LABEL: Record<HeatMetric, string> = {
  all: 'Toutes',
  isolated: 'Isolés',
  backward: 'Retardés',
  holes: 'Trous',
  outposts: 'Postes',
}

function sqToRowCol(sq: number): { row: number; col: number } {
  const row = Math.floor((sq - 1) / 5)
  const colInRow = (sq - 1) % 5
  const col = colInRow * 2 + (row % 2 === 0 ? 1 : 0)
  return { row, col }
}

function HeatmapBoard({
  heatmap, metric,
}: {
  heatmap: WeaknessHeatmap
  metric: HeatMetric
}) {
  const counts: Record<number, number> = {}
  for (const [sqStr, bucket] of Object.entries(heatmap.by_square)) {
    const sq = Number(sqStr)
    counts[sq] = metric === 'all'
      ? bucket.isolated + bucket.backward + bucket.holes + bucket.outposts
      : bucket[metric]
  }
  const maxCount = Math.max(1, ...Object.values(counts))
  // Outposts are strengths, not weaknesses — flip the colour cue.
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
      maxWidth: 220,
      border: '2px solid #4b3b22',
      borderRadius: 3,
    }}>
      {cells}
    </div>
  )
}

export default function WeaknessPanel({ onMotifClick, refreshKey = 0 }: Props) {
  const { user } = useAuth()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [debug, setDebug] = useState<MotifDebug | null>(null)
  const [heatmap, setHeatmap] = useState<WeaknessHeatmap | null>(null)
  const [heatMetric, setHeatMetric] = useState<HeatMetric>('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)

  // Invalidate cache when refreshKey bumps (e.g. after "Réinitialiser les analyses").
  useEffect(() => {
    setProfile(null)
    setDebug(null)
    setHeatmap(null)
  }, [refreshKey])

  useEffect(() => {
    if (!user || !open || profile) return
    setLoading(true)
    setError(null)
    // Profile (for the weakness list) + debug (for the empty-state
    // breakdown) fetched in parallel. Failure of the debug call is
    // non-fatal — the profile still drives the main UI.
    getMotifDebug().then(setDebug).catch(() => setDebug(null))
    getWeaknessHeatmap().then(setHeatmap).catch(() => setHeatmap(null))
    getUserProfile()
      .then(setProfile)
      .catch((err: unknown) => {
        const status = (err as { response?: { status?: number } })?.response?.status
        const rawDetail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
        const msg = (err as { message?: string })?.message ?? String(err)
        // FastAPI 422 returns `detail` as an array of {loc, msg, type}
        // objects. JS string concat would render those as
        // "[object Object]" — extract the human-readable message
        // instead so the user (and us in chat) can act on it.
        let detailStr: string
        if (Array.isArray(rawDetail)) {
          detailStr = rawDetail
            .map(d => {
              if (typeof d === 'string') return d
              const obj = d as { msg?: unknown; loc?: unknown[] }
              const msgPart = typeof obj?.msg === 'string' ? obj.msg : JSON.stringify(d)
              const locPart = Array.isArray(obj?.loc) ? ` @ ${obj.loc.join('.')}` : ''
              return msgPart + locPart
            })
            .join(' ; ')
        } else if (typeof rawDetail === 'string') {
          detailStr = rawDetail
        } else if (rawDetail != null) {
          detailStr = JSON.stringify(rawDetail)
        } else {
          detailStr = msg
        }
        setError(status ? `${status} — ${detailStr}` : detailStr)
        setProfile(null)
      })
      .finally(() => setLoading(false))
  }, [user, open, profile])

  if (!user) return null

  const weaknesses: MotifWeakness[] = profile?.weaknesses ?? []
  const maxScore = weaknesses.reduce((m, w) => Math.max(m, w.missed + w.suffered), 0)

  return (
    <div className="panel mt-2">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between bg-transparent border-0 cursor-pointer p-0"
      >
        <h3 className="text-base font-bold text-amber-600">Points faibles</h3>
        <span className="text-gray-400 text-sm">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="mt-3">
          {loading && (
            <p className="text-gray-400 text-xs text-center py-2 animate-pulse">Chargement…</p>
          )}

          {!loading && error && (
            <p className="text-red-400 text-xs text-center py-2">
              Erreur de chargement : {error}
            </p>
          )}

          {!loading && !error && profile && weaknesses.length === 0 && (
            <div className="py-3">
              <p className="text-gray-500 text-xs text-center">
                {(() => {
                  // Prefer the actual analysed-count from /motif-debug,
                  // not profile.games_count (which counts every game in
                  // the lookback window, analysed or not). After a
                  // "Réinitialiser les analyses" the latter still shows
                  // 30 even though zero verdicts remain.
                  const analysedN = debug?.games_with_verdicts ?? 0
                  const thresh = debug?.missed_threshold ?? 2
                  if (analysedN === 0) {
                    return 'Aucune partie analysée pour l’instant.'
                  }
                  return (
                    `${analysedN} partie${analysedN > 1 ? 's' : ''} analysée${analysedN > 1 ? 's' : ''}` +
                    ` — aucun motif n’apparaît encore au moins ${thresh} fois.`
                  )
                })()}
              </p>
              <p className="text-gray-600 text-xs mt-1 text-center">
                Plus vous analysez de parties, mieux les faiblesses récurrentes ressortent.
              </p>

              {/* Diagnostic breakdown — visible when no weakness rises
                  above the threshold. Lets the user (and us in chat)
                  see whether motifs are detected at all and how the
                  threshold filter affects them. */}
              {debug && (
                <details open className="mt-3 bg-gray-800/60 border border-gray-700 rounded px-2 py-1.5 text-xs">
                  <summary className="cursor-pointer text-gray-400 select-none">
                    Détail diagnostic
                  </summary>
                  <div className="mt-2 space-y-2 text-gray-300">
                    <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
                      <span className="text-gray-500">Parties analysées</span>
                      <span className="tabular-nums">{debug.games_with_verdicts}</span>
                      <span className="text-gray-500">Parties (lookback)</span>
                      <span className="tabular-nums text-gray-400">{debug.games_count}</span>
                      <span className="text-gray-500">Verdicts total</span>
                      <span className="tabular-nums">{debug.verdicts_total}</span>
                      <span className="text-gray-500">avec motifs</span>
                      <span className="tabular-nums">{debug.verdicts_with_motifs}</span>
                      <span className="text-gray-500">Seuil faiblesse</span>
                      <span className="tabular-nums">≥{debug.missed_threshold}</span>
                    </div>

                    {Object.keys(debug.by_motif).length > 0 ? (
                      <div>
                        <p className="text-gray-500 mb-1">Motifs détectés (toutes rôles) :</p>
                        <ul className="space-y-0.5 ml-2">
                          {Object.entries(debug.by_motif).map(([motif, n]) => {
                            const wScore = debug.weakness_score[motif] ?? 0
                            return (
                              <li key={motif} className="flex justify-between gap-2">
                                <span className="truncate">
                                  {MOTIF_NAME_FR[motif] ?? motif}
                                </span>
                                <span className="text-gray-500 tabular-nums flex-shrink-0">
                                  ×{n}{' '}
                                  <span className={wScore >= debug.missed_threshold ? 'text-amber-400' : 'text-gray-600'}>
                                    (faiblesse {wScore})
                                  </span>
                                </span>
                              </li>
                            )
                          })}
                        </ul>
                      </div>
                    ) : (
                      <p className="text-gray-500">
                        Aucun motif détecté par dilf sur ces parties. Les coups
                        sont passés au crible mais aucun ne correspond à un
                        motif tactique reconnu.
                      </p>
                    )}
                  </div>
                </details>
              )}
            </div>
          )}

          {!loading && !error && !profile && (
            <p className="text-gray-500 text-xs text-center py-2">
              Aucune donnée disponible.
            </p>
          )}

          {!loading && weaknesses.length > 0 && (
            <div className="flex flex-col gap-2">
              {weaknesses.map(w => {
                const score = w.missed + w.suffered
                const name = MOTIF_NAME_FR[w.motif] ?? w.motif
                return (
                  <div key={w.motif} className="flex items-center gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-xs text-gray-300 truncate">{name}</span>
                        <span className="text-xs text-gray-500 flex-shrink-0 tabular-nums">×{score}</span>
                      </div>
                      <FreqBar score={score} max={maxScore} />
                    </div>
                    <button
                      onClick={() => onMotifClick(w.motif)}
                      className="flex-shrink-0 text-xs bg-amber-600 hover:bg-amber-500 text-white px-2 py-0.5 rounded transition-colors"
                    >
                      Travailler →
                    </button>
                  </div>
                )
              })}
              <p className="text-gray-600 text-xs mt-1">
                {profile.games_count} partie{profile.games_count > 1 ? 's' : ''} analysée{profile.games_count > 1 ? 's' : ''} · précision moy.{' '}
                {Math.round(profile.average_accuracy * 100)}%
              </p>
            </div>
          )}

          {/* Geometric heatmap — recurring weakness squares (and outposts). */}
          {!loading && heatmap && heatmap.half_moves_analyzed > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-700 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-300">Carte des faiblesses</span>
                <span className="text-xs text-gray-500">{heatmap.games_analyzed} partie{heatmap.games_analyzed > 1 ? 's' : ''}</span>
              </div>
              <div className="flex gap-1 flex-wrap">
                {(['all', 'isolated', 'backward', 'holes', 'outposts'] as const).map(m => (
                  <button
                    key={m}
                    onClick={() => setHeatMetric(m)}
                    className={
                      'px-1.5 py-0.5 rounded text-xs transition-colors ' +
                      (heatMetric === m
                        ? 'bg-amber-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600 cursor-pointer')
                    }
                  >
                    {HEAT_METRIC_LABEL[m]}
                  </button>
                ))}
              </div>
              <HeatmapBoard heatmap={heatmap} metric={heatMetric} />
              <p className="text-xs text-gray-600">
                {heatmap.half_moves_analyzed} demi-coups · {heatMetric === 'outposts' ? 'vert = postes (fort)' : 'rouge = récurrence (faible)'}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
