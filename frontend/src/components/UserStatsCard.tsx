import React, { useState, useEffect } from 'react'
import { getUserStats, importLidraughtsGames } from '../api/client'
import type { UserStats } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import WeaknessPanel from './WeaknessPanel'
import MotifsCatalogPanel from './MotifsCatalogPanel'

function StatBox({
  label,
  value,
  color,
  pctOf,
}: {
  label: string
  value: number | string
  color?: string
  /** When set and `value` is a number, render "N (XX%)" with the
   *  percentage computed as `value / pctOf * 100`, rounded. Used for
   *  Bévues / Erreurs / Imprécisions to put each count in context of
   *  the total move count. */
  pctOf?: number
}) {
  const display =
    pctOf != null && typeof value === 'number' && pctOf > 0
      ? `${value} (${Math.round((value / pctOf) * 100)}%)`
      : value
  return (
    <div className="flex flex-col items-center bg-gray-700 rounded-lg px-4 py-3 min-w-[80px]">
      <span className={`text-2xl font-bold ${color ?? 'text-white'}`}>{display}</span>
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
  const { user, setUser } = useAuth()
  const { t } = useLanguage()
  const [stats, setStats] = useState<UserStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(defaultOpen)
  const [lidraughtsUsername, setLidraughtsUsername] = useState<string>(user?.lidraughts_username ?? '')
  const [lidraughtsCount, setLidraughtsCount] = useState<number>(50)
  const [importing, setImporting] = useState(false)
  const [importMsg, setImportMsg] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    setLidraughtsUsername(user?.lidraughts_username ?? '')
  }, [user?.lidraughts_username])

  useEffect(() => {
    if (!user || !open) return
    setLoading(true)
    getUserStats()
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false))
  }, [user, open])

  const handleImport = async () => {
    const uname = lidraughtsUsername.trim()
    if (!uname) return
    setImporting(true)
    setImportMsg(null)
    try {
      const count = Math.max(1, Math.min(100, Math.floor(lidraughtsCount || 50)))
      const res = await importLidraughtsGames(uname, count)
      setImportMsg({
        kind: 'success',
        text: `${res.imported} / ${res.fetched} parties importées (${res.total_lidraughts_games} au total).`,
      })
      if (user && user.lidraughts_username !== res.username) {
        setUser({ ...user, lidraughts_username: res.username })
      }
      const fresh = await getUserStats().catch(() => null)
      if (fresh) setStats(fresh)
    } catch (err: any) {
      const detail = err?.response?.data?.detail || t('lidraughtsImportError')
      setImportMsg({ kind: 'error', text: detail })
    } finally {
      setImporting(false)
    }
  }

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
                  <StatBox label="Bévues" value={stats.blunders} color="text-red-400" pctOf={stats.total_moves} />
                  <StatBox label="Erreurs" value={stats.mistakes} color="text-orange-400" pctOf={stats.total_moves} />
                  <StatBox label="Imprécisions" value={stats.inaccuracies} color="text-yellow-400" pctOf={stats.total_moves} />
                  {(stats.games_from_lidraughts ?? 0) > 0 && (
                    <StatBox
                      label="Lidraughts"
                      value={stats.games_from_lidraughts ?? 0}
                      color="text-sky-400"
                    />
                  )}
                </div>
              </div>

              {/* "Parties récentes" block removed (chat) — redundant
                  with the full Historique des parties list shown
                  below in the Profil tab, and the truncated player
                  names made it unreadable. */}
            </>
          )}

          {!loading && (
            <div className="mt-4 border-t border-gray-700 pt-3">
              <p className="text-xs text-gray-400 mb-2">{t('lidraughtsImportButton')}</p>
              <div className="flex flex-col gap-2">
                <input
                  type="text"
                  value={lidraughtsUsername}
                  onChange={e => setLidraughtsUsername(e.target.value)}
                  placeholder={t('lidraughtsUsernamePlaceholder')}
                  className="bg-gray-700 text-white text-sm rounded px-2 py-1.5 border border-gray-600 focus:border-amber-500 focus:outline-none"
                  disabled={importing}
                />
                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-400">{t('lidraughtsCountLabel')}</label>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={lidraughtsCount}
                    onChange={e => setLidraughtsCount(Number(e.target.value))}
                    className="w-20 bg-gray-700 text-white text-sm rounded px-2 py-1 border border-gray-600 focus:border-amber-500 focus:outline-none"
                    disabled={importing}
                  />
                </div>
                <button
                  onClick={handleImport}
                  disabled={importing || !lidraughtsUsername.trim()}
                  className="w-full bg-amber-600 hover:bg-amber-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white text-sm font-semibold rounded px-3 py-2 transition-colors"
                >
                  {importing ? t('lidraughtsImporting') : t('lidraughtsImportButton')}
                </button>
                {importMsg && (
                  <p className={`text-xs mt-1 ${importMsg.kind === 'success' ? 'text-green-400' : 'text-red-400'}`}>
                    {importMsg.text}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
      {onMotifClick && <WeaknessPanel onMotifClick={onMotifClick} />}
      <MotifsCatalogPanel onMotifClick={onMotifClick} />
    </div>
  )
}
