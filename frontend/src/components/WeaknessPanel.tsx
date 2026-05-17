import React, { useState, useEffect } from 'react'
import { getUserProfile, getMotifDebug } from '../api/client'
import type { MotifWeakness, UserProfile, MotifDebug } from '../api/client'
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

export default function WeaknessPanel({ onMotifClick, refreshKey = 0 }: Props) {
  const { user } = useAuth()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [debug, setDebug] = useState<MotifDebug | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)

  // Invalidate cache when refreshKey bumps (e.g. after "Réinitialiser les analyses").
  useEffect(() => {
    setProfile(null)
    setDebug(null)
  }, [refreshKey])

  useEffect(() => {
    if (!user || !open || profile) return
    setLoading(true)
    setError(null)
    // Profile (for the weakness list) + debug (for the empty-state
    // breakdown) fetched in parallel. Failure of the debug call is
    // non-fatal — the profile still drives the main UI.
    getMotifDebug().then(setDebug).catch(() => setDebug(null))
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
        </div>
      )}
    </div>
  )
}
