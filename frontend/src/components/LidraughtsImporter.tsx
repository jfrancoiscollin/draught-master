/**
 * Import bulk lidraughts games + reset the dilf analyses on demand.
 *
 * Extracted from UserStatsCard so the profile screen can stay
 * focused on identity + stats and the "Analyser mes parties" view
 * can host the import + reset controls alongside the game list,
 * which is where they're actually used.
 */

import { useCallback, useEffect, useState } from 'react'
import { importLidraughtsGames, resetMyAnalyses } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'

interface Props {
  /** Bumped after a successful import or reset so siblings
   *  (GameHistory, WeaknessPanel…) can refetch. */
  onChanged: () => void
}

export default function LidraughtsImporter({ onChanged }: Props) {
  const { user, setUser } = useAuth()
  const { t } = useLanguage()
  const [open, setOpen] = useState(false)   // drop-down, closed by default
  const [lidraughtsUsername, setLidraughtsUsername] = useState<string>(user?.lidraughts_username ?? '')
  const [lidraughtsCount, setLidraughtsCount] = useState(50)
  const [importing, setImporting] = useState(false)
  const [importMsg, setImportMsg] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)
  const [resetting, setResetting] = useState(false)
  const [resetMsg, setResetMsg] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)

  // Re-sync when the AuthContext refreshes the user (e.g. after a
  // login or a /me refetch).
  useEffect(() => {
    setLidraughtsUsername(user?.lidraughts_username ?? '')
  }, [user?.lidraughts_username])

  const handleImport = useCallback(async () => {
    const uname = lidraughtsUsername.trim()
    if (!uname) return
    setImporting(true)
    setImportMsg(null)
    try {
      const res = await importLidraughtsGames(uname, lidraughtsCount)
      setImportMsg({
        kind: 'success',
        text: `${res.imported} importé${res.imported > 1 ? 's' : ''} · ${res.skipped} déjà présent${res.skipped > 1 ? 's' : ''}`,
      })
      if (user && user.lidraughts_username !== res.username) {
        setUser({ ...user, lidraughts_username: res.username })
      }
      onChanged()
    } catch (e) {
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'Erreur réseau'
      setImportMsg({ kind: 'error', text: String(detail) })
    } finally {
      setImporting(false)
    }
  }, [lidraughtsUsername, lidraughtsCount, user, setUser, onChanged])

  const handleReset = useCallback(async () => {
    if (!window.confirm('Effacer les verdicts et annotations sur toutes les parties ? Les parties elles-mêmes sont conservées.')) return
    setResetting(true)
    setResetMsg(null)
    try {
      const res = await resetMyAnalyses()
      setResetMsg({
        kind: 'success',
        text: `${res.verdicts_deleted} verdicts supprimés · ${res.games_cleared} partie(s) remise(s) à zéro`,
      })
      onChanged()
    } catch (e) {
      setResetMsg({ kind: 'error', text: String((e as Error).message ?? e) })
    } finally {
      setResetting(false)
    }
  }, [onChanged])

  if (!user) return null

  return (
    <div className="panel">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between bg-transparent border-0 cursor-pointer p-0"
      >
        <h3 className="text-base font-bold text-amber-600">Importer mes parties</h3>
        <span className="text-gray-400 text-sm">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="mt-3 flex flex-col gap-2">
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
          <button
            onClick={handleReset}
            disabled={resetting}
            className="w-full bg-gray-700 hover:bg-red-900 border border-gray-600 hover:border-red-700 disabled:bg-gray-800 disabled:cursor-not-allowed text-gray-300 hover:text-white text-xs font-semibold rounded px-3 py-2 transition-colors mt-2"
            title="Effacer les verdicts et annotations sur toutes les parties (les parties sont conservées)"
          >
            {resetting ? 'Réinitialisation…' : '↺ Réinitialiser les analyses'}
          </button>
          {resetMsg && (
            <p className={`text-xs mt-1 ${resetMsg.kind === 'success' ? 'text-green-400' : 'text-red-400'}`}>
              {resetMsg.text}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
