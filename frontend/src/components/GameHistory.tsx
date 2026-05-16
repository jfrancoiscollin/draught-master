import { useState, useEffect, useCallback } from 'react'
import type { HistoryItem, GameDetailResponse } from '../types'
import {
  getHistory,
  getGameDetail,
  analyzeGamePedagogy,
} from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'

interface GameHistoryProps {
  onReplay: (detail: GameDetailResponse) => void
}

function formatDate(iso: string, language: string): string {
  try {
    const locale = language === 'en' ? 'en-GB' : 'fr-FR'
    const d = new Date(iso)
    return d.toLocaleDateString(locale, {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

type BulkMode = 'idle' | 'dilf'

export default function GameHistory({ onReplay }: GameHistoryProps) {
  const { t, language } = useLanguage()
  const [games, setGames] = useState<HistoryItem[]>([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)

  const [bulkMode, setBulkMode] = useState<BulkMode>('idle')
  const [bulkProgress, setBulkProgress] = useState({ done: 0, total: 0, current: '' })
  const [bulkError, setBulkError] = useState<string | null>(null)

  const loadGames = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getHistory(page, 10)
      setGames(data.games)
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => { loadGames() }, [loadGames])

  const handleSelect = async (id: string) => {
    const detail = await getGameDetail(id)
    onReplay(detail)
  }

  const getResultLabel = (result: string | null): string => {
    if (result === 'white') return t('resultWhiteWins')
    if (result === 'black') return t('resultBlackWins')
    if (result === 'draw') return t('resultDraw')
    return t('inProgress')
  }

  const resultBadge = (result: string | null) => {
    if (!result) return <span className="text-gray-500 text-[10px]">{t('inProgress')}</span>
    const colors: Record<string, string> = {
      white: 'bg-gray-200 text-gray-900',
      black: 'bg-gray-800 text-gray-200 border border-gray-600',
      draw: 'bg-yellow-800 text-yellow-200',
    }
    return (
      <span className={`text-[10px] px-1.5 py-0.5 rounded ${colors[result] || 'bg-gray-700 text-gray-300'}`}>
        {getResultLabel(result)}
      </span>
    )
  }

  /** Slot for one analysis engine's check : ✓ green if done, dim ✗ otherwise. */
  const analysisSlot = (done: boolean | undefined, label: string) => (
    <span
      className={`inline-flex items-center justify-center w-6 h-6 rounded text-xs font-bold ${
        done ? 'bg-green-700/40 text-green-300' : 'bg-gray-800 text-gray-600'
      }`}
      title={done ? `${label} ✓ analysé` : `${label} — pas encore analysé`}
    >
      {done ? '✓' : '–'}
    </span>
  )

  // ─── Bulk analyse ────────────────────────────────────────────────────
  const dilfPending = games.filter(g => !g.has_dilf_analysis)

  const runBulkDilf = async () => {
    if (bulkMode !== 'idle' || dilfPending.length === 0) return
    setBulkMode('dilf')
    setBulkError(null)
    setBulkProgress({ done: 0, total: dilfPending.length, current: '' })
    let ok = 0
    let fail = 0
    const lastErrors: string[] = []
    for (let i = 0; i < dilfPending.length; i++) {
      const g = dilfPending[i]
      setBulkProgress({ done: i, total: dilfPending.length, current: `${g.white_player} vs ${g.black_player}` })
      try {
        const detail = await getGameDetail(g.id)
        // Pick the user's side from the saved game, fallback to white.
        // dilf's /analyze-game also persists legacy Scan annotations as a
        // side-effect (cf cascade in pedagogy/api.py), so a single click
        // suffices to populate both the move_verdicts table and
        // games.annotations_json.
        const userSide = ((detail as { user_side?: string }).user_side as 'white' | 'black') ?? 'white'
        await analyzeGamePedagogy(g.id, userSide, language)
        ok += 1
      } catch (err: unknown) {
        fail += 1
        const status = (err as { response?: { status?: number } })?.response?.status
        const msg = (err as { message?: string })?.message ?? String(err)
        const label = `${g.white_player} vs ${g.black_player}`
        lastErrors.push(`${label}${status ? ` [${status}]` : ''}: ${msg}`)
      }
    }
    setBulkProgress({ done: dilfPending.length, total: dilfPending.length, current: '' })
    if (fail > 0) {
      const summary = `${ok} OK · ${fail} échec(s). Détails : ${lastErrors.slice(-3).join(' | ')}`
      setBulkError(summary)
    }
    setBulkMode('idle')
    await loadGames()  // refresh checkmarks
  }

  const bulkRunning = bulkMode !== 'idle'

  return (
    <div className="flex flex-col gap-3">

      {/* ─── Bulk-analyze section ────────────────────────────────── */}
      <div className="panel">
        <h3 className="text-lg font-bold text-amber-600 mb-2">Analyser mes parties</h3>
        <p className="text-xs text-gray-400 mb-3">
          Analyse en lot avec dilf : détection des motifs tactiques et
          notation de chaque coup (Parfait / Imprécision / Erreur / Gaffe).
        </p>
        <button
          onClick={runBulkDilf}
          disabled={bulkRunning || dilfPending.length === 0}
          className="w-full px-3 py-2 mb-3 rounded font-semibold text-sm transition-colors bg-purple-700 hover:bg-purple-600 text-white disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed"
        >
          🎓 Analyser avec dilf
          {dilfPending.length > 0 && ` (${dilfPending.length})`}
        </button>
        {bulkRunning && bulkProgress.total > 0 && (
          <div>
            <div className="flex justify-between text-xs text-gray-300 mb-1">
              <span>🎓 dilf — {bulkProgress.done}/{bulkProgress.total}</span>
              {bulkProgress.current && <span className="text-gray-500 truncate ml-2">{bulkProgress.current}</span>}
            </div>
            <div className="w-full h-2 bg-gray-700 rounded overflow-hidden">
              <div
                className="h-full transition-all duration-300 bg-purple-500"
                style={{ width: `${Math.round((bulkProgress.done / bulkProgress.total) * 100)}%` }}
              />
            </div>
          </div>
        )}
        {bulkError && !bulkRunning && (
          <p className="text-amber-400 text-xs mt-2">{bulkError}</p>
        )}
      </div>

      {/* ─── Games list ──────────────────────────────────────────── */}
      <div className="panel">
        <h3 className="text-lg font-bold text-amber-600 mb-3">{t('gameHistory')}</h3>

        {loading ? (
          <div className="flex justify-center py-4">
            <div className="spinner" />
          </div>
        ) : games.length === 0 ? (
          <p className="text-gray-500 italic text-sm">{t('noGames')}</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            {games.map(game => (
              <div
                key={game.id}
                className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
              >
                <button
                  onClick={() => handleSelect(game.id)}
                  className="flex-1 text-left p-3 min-w-0"
                >
                  <div className="text-sm font-medium text-white truncate">
                    {game.white_player} vs {game.black_player}
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5 flex items-center gap-2 flex-wrap">
                    <span>{formatDate(game.date, language)}</span>
                    <span>·</span>
                    <span>{game.move_count} {t('moves')}</span>
                    {resultBadge(game.result)}
                  </div>
                </button>
                <div className="flex items-center gap-1 pr-3 flex-shrink-0">
                  {analysisSlot(game.has_dilf_analysis, 'dilf')}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex justify-between mt-3">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1 || bulkRunning}
            className="btn-secondary text-sm"
          >
            {t('previous')}
          </button>
          <span className="text-gray-400 text-sm self-center">Page {page}</span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={games.length < 10 || bulkRunning}
            className="btn-secondary text-sm"
          >
            {t('next')}
          </button>
        </div>
      </div>
    </div>
  )
}

