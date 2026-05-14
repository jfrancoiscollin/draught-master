import React, { useState, useEffect } from 'react'
import { getUserStats } from '../api/client'
import type { UserStats } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import WeaknessPanel from './WeaknessPanel'

function StatBox({ label, value, color }: { label: string; value: number | string; color?: string }) {
  return (
    <div className="flex flex-col items-center bg-gray-700 rounded-lg px-4 py-3 min-w-[80px]">
      <span className={`text-2xl font-bold ${color ?? 'text-white'}`}>{value}</span>
      <span className="text-xs text-gray-400 text-center mt-1">{label}</span>
    </div>
  )
}

function AccuracyRing({ pct }: { pct: number }) {
  const r = 28
  const circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ
  const color = pct >= 80 ? '#4ade80' : pct >= 60 ? '#facc15' : '#f87171'
  return (
    <div className="relative flex items-center justify-center" style={{ width: 72, height: 72 }}>
      <svg width="72" height="72" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="36" cy="36" r={r} fill="none" stroke="#374151" strokeWidth="6" />
        <circle
          cx="36" cy="36" r={r} fill="none"
          stroke={color} strokeWidth="6"
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.8s ease' }}
        />
      </svg>
      <span className="absolute text-sm font-bold" style={{ color }}>{pct}%</span>
    </div>
  )
}

interface UserStatsCardProps {
  defaultOpen?: boolean
  onMotifClick?: (slug: string) => void
}

export default function UserStatsCard({ defaultOpen = false, onMotifClick }: UserStatsCardProps) {
  const { user } = useAuth()
  const { t } = useLanguage()
  const [stats, setStats] = useState<UserStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(defaultOpen)

  useEffect(() => {
    if (!user || !open) return
    setLoading(true)
    getUserStats()
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
  }, [user, open])

  if (!user) return null

  return (
    <div className="panel">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between bg-transparent border-0 cursor-pointer p-0"
      >
        <h3 className="text-lg font-bold text-amber-600">{t('myStats')}</h3>
        <span className="text-gray-400 text-sm">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="mt-3">
          {loading && <p className="text-gray-400 text-sm text-center py-3">Chargement…</p>}
          {!loading && !stats && (
            <p className="text-gray-500 text-sm text-center py-3">Aucune partie enregistrée.</p>
          )}
          {!loading && stats && (
            <>
              <div className="flex items-center gap-4 mb-4">
                <AccuracyRing pct={stats.accuracy_pct} />
                <div className="flex flex-wrap gap-2">
                  <StatBox label="Parties" value={stats.total_games} />
                  <StatBox label="Coups" value={stats.total_moves} />
                  <StatBox label="Bévues" value={stats.blunders} color="text-red-400" />
                  <StatBox label="Erreurs" value={stats.mistakes} color="text-orange-400" />
                  <StatBox label="Imprécisions" value={stats.inaccuracies} color="text-yellow-400" />
                </div>
              </div>

              {stats.recent_games.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Parties récentes</p>
                  <div className="flex flex-col gap-1">
                    {stats.recent_games.map(g => (
                      <div key={g.id} className="flex items-center gap-2 bg-gray-750 rounded px-2 py-1.5 text-xs" style={{ backgroundColor: '#1e2a3a' }}>
                        <span className="text-gray-300 flex-1 truncate">{g.white_player} vs {g.black_player}</span>
                        <span className={`font-bold flex-shrink-0 ${g.result === 'white' ? 'text-amber-300' : g.result === 'black' ? 'text-blue-300' : 'text-gray-400'}`}>
                          {g.result === 'white' ? 'Blancs' : g.result === 'black' ? 'Noirs' : '='}
                        </span>
                        {(g.blunders > 0 || g.mistakes > 0) && (
                          <span className="flex-shrink-0 text-red-400">{g.blunders > 0 ? `${g.blunders}✗` : ''}{g.mistakes > 0 ? ` ${g.mistakes}?` : ''}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
      {onMotifClick && <WeaknessPanel onMotifClick={onMotifClick} />}
    </div>
  )
}
