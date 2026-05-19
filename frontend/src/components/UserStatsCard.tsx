import { useState, useEffect, useCallback } from 'react'
import { deleteMyAccount, getUserStats } from '../api/client'
import type { UserStats } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'

/** Profile header — username display + danger zone (delete account).
 * Sits at the very top of the stats card so the user sees their
 * identity before anything else. */
function ProfileHeader() {
  const { user, logout } = useAuth()
  const [deleting, setDeleting] = useState(false)

  const handleDelete = useCallback(async () => {
    if (!user) return
    const ok = window.confirm(
      `Supprimer ton compte « ${user.username ?? user.email} » ? `
      + 'Toutes tes parties, analyses et statistiques seront effacées. '
      + 'Cette action est irréversible.',
    )
    if (!ok) return
    setDeleting(true)
    try {
      await deleteMyAccount()
      logout()
      // Force a reload so any cached component state tied to the user
      // (board state, lobby panels…) doesn't survive past the wipe.
      window.location.reload()
    } catch (e) {
      alert('Suppression échouée : ' + String((e as Error).message ?? e))
      setDeleting(false)
    }
  }, [user, logout])

  if (!user) return null
  return (
    <div className="flex items-center gap-3 mb-3">
      <div className="flex-1 min-w-0">
        <h2 className="text-lg font-bold text-white truncate">
          {user.username ?? '(pseudo non défini)'}
        </h2>
        <p className="text-xs text-gray-500 truncate">{user.email}</p>
      </div>
      <button
        onClick={handleDelete}
        disabled={deleting}
        className="flex-shrink-0 text-xs text-red-400 hover:text-red-300 hover:bg-red-900/30 border border-red-800/40 px-2 py-1 rounded transition-colors cursor-pointer disabled:opacity-40"
        title="Supprime définitivement ton compte et toutes ses données"
      >
        {deleting ? 'Suppression…' : 'Supprimer le compte'}
      </button>
    </div>
  )
}

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
}

export default function UserStatsCard({
  defaultOpen = false,
}: UserStatsCardProps) {
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

  // Lidraughts import + analyses reset + cross-game weakness/motif
  // panels were moved out of the profile card per UX refactor: the
  // profile now keeps only identity (pseudo + delete) + raw numbers.
  // Those workflows live in MyGamesPanel.tsx alongside the games
  // list itself.

  if (!user) return null

  return (
    <div className="panel">
      <ProfileHeader />
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

          {/* Lidraughts import + reset analyses removed: see
              LidraughtsImporter.tsx, mounted in MyGamesPanel. */}
          {!loading && (
            <div className="mt-4 border-t border-gray-700 pt-3 text-xs text-gray-500">
              <p>
                Importer des parties Lidraughts ou analyser les parties
                existantes :{' '}onglet <strong className="text-gray-300">Analyser</strong>{' '}
                → <em>Analyser mes parties</em>.
              </p>
            </div>
          )}
        </div>
      )}
      {/* WeaknessPanel + MotifsCatalogPanel moved to MyGamesPanel
          as part of the profile slim-down. */}
    </div>
  )
}
