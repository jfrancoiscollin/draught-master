import React, { useState, useEffect } from 'react'
import { getUserProfile } from '../api/client'
import type { MotifWeakness, UserProfile } from '../api/client'
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
}

function FreqBar({ score, max }: { score: number; max: number }) {
  const pct = max > 0 ? Math.round((score / max) * 100) : 0
  return (
    <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
      <div className="h-full rounded-full bg-amber-500 transition-all" style={{ width: `${pct}%` }} />
    </div>
  )
}

export default function WeaknessPanel({ onMotifClick }: Props) {
  const { user } = useAuth()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!user || !open || profile) return
    setLoading(true)
    getUserProfile()
      .then(setProfile)
      .catch(() => setProfile(null))
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

          {!loading && profile && weaknesses.length === 0 && (
            <div className="text-center py-3">
              <p className="text-gray-500 text-xs">
                Pas encore assez de données.
              </p>
              <p className="text-gray-600 text-xs mt-1">
                Analysez au moins 3 parties pour voir vos faiblesses.
              </p>
            </div>
          )}

          {!loading && !profile && (
            <p className="text-gray-500 text-xs text-center py-2">
              Aucune partie analysée.
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
