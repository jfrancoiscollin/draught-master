import React, { useState, useEffect, useCallback } from 'react'
import type { HistoryItem, GameDetailResponse } from '../types'
import {
  getHistory,
  getGameDetail,
  saveGameAnnotations,
  analyzeGamePedagogy,
} from '../api/client'
import { annotateGame } from '../lib/gameAnnotations'
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

type BulkMode = 'idle' | 'dilf' | 'scan'

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
  const scanPending = games.filter(g => !g.has_scan_analysis)

  const runBulkDilf = async () => {
    if (bulkMode !== 'idle' || dilfPending.length === 0) return
    setBulkMode('dilf')
    setBulkError(null)
    setBulkProgress({ done: 0, total: dilfPending.length, current: '' })
    for (let i = 0; i < dilfPending.length; i++) {
      const g = dilfPending[i]
      setBulkProgress({ done: i, total: dilfPending.length, current: `${g.white_player} vs ${g.black_player}` })
      try {
        const detail = await getGameDetail(g.id)
        // Pick the user's side from the saved game, fallback to white.
        const userSide = ((detail as { user_side?: string }).user_side as 'white' | 'black') ?? 'white'
        await analyzeGamePedagogy(g.id, userSide, language)
      } catch (err: unknown) {
        const msg = (err as { message?: string })?.message ?? String(err)
        // Keep going even on per-game error.
        setBulkError(`Échec partiel : ${g.id.slice(0, 8)}… (${msg})`)
      }
    }
    setBulkProgress({ done: dilfPending.length, total: dilfPending.length, current: '' })
    setBulkMode('idle')
    await loadGames()  // refresh checkmarks
  }

  const runBulkScan = async () => {
    if (bulkMode !== 'idle' || scanPending.length === 0) return
    setBulkMode('scan')
    setBulkError(null)
    setBulkProgress({ done: 0, total: scanPending.length, current: '' })
    for (let i = 0; i < scanPending.length; i++) {
      const g = scanPending[i]
      setBulkProgress({ done: i, total: scanPending.length, current: `${g.white_player} vs ${g.black_player}` })
      try {
        const detail = await getGameDetail(g.id)
        if (!detail.fen_positions || detail.fen_positions.length === 0) continue
        const positions = detail.fen_positions.map((fen: string) => ({ fen, notation: '' }))
        const controller = new AbortController()
        const { annotations } = await annotateGame(
          positions,
          200,
          () => {},
          controller.signal,
        )
        if (annotations && annotations.length > 0) {
          await saveGameAnnotations(g.id, annotations as unknown as Array<{ move_number: number }>)
        }
      } catch (err: unknown) {
        const msg = (err as { message?: string })?.message ?? String(err)
        setBulkError(`Échec partiel : ${g.id.slice(0, 8)}… (${msg})`)
      }
    }
    setBulkProgress({ done: scanPending.length, total: scanPending.length, current: '' })
    setBulkMode('idle')
    await loadGames()
  }

  const bulkRunning = bulkMode !== 'idle'

  return (
    <div className="flex flex-col gap-3">

      {/* ─── Bulk-analyze section ────────────────────────────────── */}
      <div className="panel">
        <h3 className="text-lg font-bold text-amber-600 mb-2">Analyser mes parties</h3>
        <p className="text-xs text-gray-400 mb-3">
          Analyse en lot des parties non encore analysées.
          dilf détecte les motifs tactiques ; Scan note chaque coup
          (Parfait / Imprécision / Erreur / Gaffe).
        </p>
        <div className="flex flex-col sm:flex-row gap-2 mb-3">
          <button
            onClick={runBulkDilf}
            disabled={bulkRunning || dilfPending.length === 0}
            className="flex-1 px-3 py-2 rounded font-semibold text-sm transition-colors bg-purple-700 hover:bg-purple-600 text-white disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed"
          >
            🎓 Analyser avec dilf
            {dilfPending.length > 0 && ` (${dilfPending.length})`}
          </button>
          <button
            onClick={runBulkScan}
            disabled={bulkRunning || scanPending.length === 0}
            className="flex-1 px-3 py-2 rounded font-semibold text-sm transition-colors bg-cyan-700 hover:bg-cyan-600 text-white disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed"
          >
            🤖 Analyser avec Scan
            {scanPending.length > 0 && ` (${scanPending.length})`}
          </button>
        </div>
        {bulkRunning && bulkProgress.total > 0 && (
          <div>
            <div className="flex justify-between text-xs text-gray-300 mb-1">
              <span>{bulkMode === 'dilf' ? '🎓 dilf' : '🤖 Scan'} — {bulkProgress.done}/{bulkProgress.total}</span>
              {bulkProgress.current && <span className="text-gray-500 truncate ml-2">{bulkProgress.current}</span>}
            </div>
            <div className="w-full h-2 bg-gray-700 rounded overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${bulkMode === 'dilf' ? 'bg-purple-500' : 'bg-cyan-500'}`}
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
                  {analysisSlot(game.has_scan_analysis, 'Scan')}
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

