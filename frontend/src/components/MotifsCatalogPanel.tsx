import { useState, useEffect } from 'react'
import { getMotifDebug } from '../api/client'
import type { MotifDebug } from '../api/client'
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
  coup_napoleon: 'Coup Napoléon',
  coup_manoury: 'Coup Manoury',
  coup_enfilade: 'Coup d’enfilade',
  coup_du_bruleur: 'Coup du brûleur',
  combinaison_2_temps: 'Combinaison en 2 temps',
  combinaison_3_temps: 'Combinaison en 3 temps',
  combinaison_4_temps: 'Combinaison en 4 temps',
  combinaison_5_temps: 'Combinaison en 5 temps',
}

interface Props {
  onMotifClick?: (slug: string) => void
}

/** Always-visible roll-up of every motif detected across the user's
 *  analysed games. Complements <WeaknessPanel> which only surfaces
 *  motifs that crossed the missed+suffered threshold. */
export default function MotifsCatalogPanel({ onMotifClick }: Props) {
  const { user } = useAuth()
  const [debug, setDebug] = useState<MotifDebug | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!user || !open || debug) return
    setLoading(true)
    setError(null)
    getMotifDebug()
      .then(setDebug)
      .catch((err: unknown) => {
        const status = (err as { response?: { status?: number } })?.response?.status
        setError(status ? `Erreur ${status}` : 'Erreur de chargement')
        setDebug(null)
      })
      .finally(() => setLoading(false))
  }, [user, open, debug])

  if (!user) return null

  const entries = debug ? Object.entries(debug.by_motif) : []
  const maxN = entries.reduce((m, [, n]) => Math.max(m, n), 0)

  return (
    <div className="panel mt-2">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between bg-transparent border-0 cursor-pointer p-0"
      >
        <h3 className="text-base font-bold text-amber-600">Motifs détectés</h3>
        <span className="text-gray-400 text-sm">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="mt-3">
          {loading && <p className="text-gray-400 text-xs text-center py-2 animate-pulse">Chargement…</p>}
          {!loading && error && <p className="text-red-400 text-xs text-center py-2">{error}</p>}
          {!loading && !error && debug && entries.length === 0 && (
            <p className="text-gray-500 text-xs text-center py-2">
              Aucun motif détecté sur les {debug.games_count} partie{debug.games_count > 1 ? 's' : ''} analysée{debug.games_count > 1 ? 's' : ''}.
            </p>
          )}
          {!loading && !error && entries.length > 0 && debug && (
            <ul className="flex flex-col gap-1.5">
              {entries.map(([motif, n]) => {
                const name = MOTIF_NAME_FR[motif] ?? motif
                const isWeak = (debug.weakness_score[motif] ?? 0) >= debug.missed_threshold
                const pct = maxN > 0 ? Math.round((n / maxN) * 100) : 0
                return (
                  <li key={motif} className="flex items-center gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-0.5">
                        <span className={`text-xs truncate ${isWeak ? 'text-amber-400 font-semibold' : 'text-gray-300'}`}>{name}</span>
                        <span className="text-xs text-gray-500 flex-shrink-0 tabular-nums">×{n}</span>
                      </div>
                      <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${isWeak ? 'bg-amber-500' : 'bg-gray-500'}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                    {onMotifClick && (
                      <button
                        onClick={() => onMotifClick(motif)}
                        className="flex-shrink-0 text-xs bg-gray-700 hover:bg-amber-700 text-gray-300 hover:text-white px-2 py-0.5 rounded transition-colors"
                        title={`Voir le motif ${name}`}
                      >
                        ↗
                      </button>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
