import React, { useState, useEffect } from 'react'
import type { HistoryItem, GameDetailResponse } from '../types'
import { getHistory, getGameDetail } from '../api/client'
import { resultLabel } from '../types'

interface GameHistoryProps {
  onReplay: (detail: GameDetailResponse) => void
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleDateString('fr-FR', {
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

export default function GameHistory({ onReplay }: GameHistoryProps) {
  const [games, setGames] = useState<HistoryItem[]>([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<GameDetailResponse | null>(null)

  useEffect(() => {
    loadGames()
  }, [page])

  const loadGames = async () => {
    setLoading(true)
    try {
      const data = await getHistory(page, 10)
      setGames(data.games)
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = async (id: string) => {
    const detail = await getGameDetail(id)
    setSelected(detail)
    onReplay(detail)
  }

  const resultBadge = (result: string | null) => {
    if (!result) return <span className="text-gray-500 text-xs">En cours</span>
    const colors: Record<string, string> = {
      white: 'bg-gray-200 text-gray-900',
      black: 'bg-gray-800 text-gray-200 border border-gray-600',
      draw: 'bg-yellow-800 text-yellow-200',
    }
    return (
      <span className={`text-xs px-2 py-0.5 rounded ${colors[result] || 'bg-gray-700 text-gray-300'}`}>
        {resultLabel(result)}
      </span>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="panel">
        <h3 className="text-lg font-bold text-green-400 mb-3">Historique des parties</h3>

        {loading ? (
          <div className="flex justify-center py-4">
            <div className="spinner" />
          </div>
        ) : games.length === 0 ? (
          <p className="text-gray-500 italic text-sm">Aucune partie enregistrée.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {games.map(game => (
              <button
                key={game.id}
                onClick={() => handleSelect(game.id)}
                className={`text-left p-3 rounded-lg transition-colors ${
                  selected?.id === game.id
                    ? 'bg-green-800 border border-green-600'
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-sm font-medium text-white">
                      {game.white_player} vs {game.black_player}
                    </span>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {formatDate(game.date)} · {game.move_count} coups
                    </div>
                  </div>
                  {resultBadge(game.result)}
                </div>
              </button>
            ))}
          </div>
        )}

        <div className="flex justify-between mt-3">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-secondary text-sm"
          >
            ← Précédent
          </button>
          <span className="text-gray-400 text-sm self-center">Page {page}</span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={games.length < 10}
            className="btn-secondary text-sm"
          >
            Suivant →
          </button>
        </div>
      </div>

      {selected && (
        <div className="panel">
          <h4 className="font-bold text-white mb-2">
            {selected.white_player} vs {selected.black_player}
          </h4>
          <div className="flex gap-2 items-center mb-2">
            {resultBadge(selected.result)}
            <span className="text-xs text-gray-400">{selected.move_count} coups</span>
          </div>
          {selected.pdn && (
            <div className="bg-gray-900 rounded p-2 font-mono text-xs text-gray-300 max-h-32 overflow-y-auto">
              {selected.pdn}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
