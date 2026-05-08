import React from 'react'
import { useLanguage } from '../i18n/LanguageContext'

interface GameControlsProps {
  result: string | null
  turn: 'white' | 'black'
  moveCount: number
  aiDepth: number
  onNewGame: () => void
  onAiDepthChange: (depth: number) => void
  disabled?: boolean
  showExplorer: boolean
  onShowExplorerChange: (v: boolean) => void
  explorerMaxMoves: number
  onExplorerMaxMovesChange: (n: number) => void
}

export default function GameControls({
  result,
  turn,
  moveCount,
  aiDepth,
  onNewGame,
  onAiDepthChange,
  disabled = false,
  showExplorer,
  onShowExplorerChange,
  explorerMaxMoves,
  onExplorerMaxMovesChange,
}: GameControlsProps) {
  const { t } = useLanguage()

  const getResultLabel = (res: string | null): string => {
    if (res === 'white') return t('resultWhiteWins')
    if (res === 'black') return t('resultBlackWins')
    if (res === 'draw') return t('resultDraw')
    return ''
  }

  return (
    <div className="panel flex flex-col gap-3">
      <h3 className="text-lg font-bold text-amber-600">{t('controls')}</h3>

      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-400">{t('turn')}</span>
        <span className={`font-semibold px-2 py-0.5 rounded ${turn === 'white' ? 'bg-gray-200 text-gray-900' : 'bg-gray-800 text-gray-200 border border-gray-600'}`}>
          {turn === 'white' ? `⚪ ${t('white')}` : `⚫ ${t('black')}`}
        </span>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-400">{t('movesPlayed')}</span>
        <span className="text-gray-200 font-mono">{moveCount}</span>
      </div>

      {result && (
        <div className="bg-yellow-900 border border-yellow-600 rounded-lg px-3 py-2 text-center">
          <span className="text-yellow-300 font-bold">{getResultLabel(result)}</span>
        </div>
      )}

      <div className="flex flex-col gap-1">
        <label className="text-sm text-gray-400">
          {t('aiLevel')} <span className="text-white font-semibold">{aiDepth}</span>
        </label>
        <input
          type="range"
          min={1}
          max={8}
          value={aiDepth}
          onChange={e => onAiDepthChange(Number(e.target.value))}
          className="w-full accent-amber-600"
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>{t('easy')}</span>
          <span>{t('expert')}</span>
        </div>
      </div>

      {/* Explorateur d'ouvertures */}
      <div className="border-t border-gray-700 pt-3 flex flex-col gap-2">
        <h4 className="text-sm font-semibold text-gray-300">Explorateur d'ouvertures</h4>

        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Afficher les flèches</span>
          <button
            onClick={() => onShowExplorerChange(!showExplorer)}
            className="flex items-center gap-1.5 transition-colors"
            style={{ color: showExplorer ? '#f59e0b' : '#6b7280' }}
          >
            <span style={{
              width: 32, height: 16, borderRadius: 8,
              background: showExplorer ? '#d97706' : '#4b5563',
              position: 'relative', display: 'inline-block', flexShrink: 0,
              transition: 'background 0.2s',
            }}>
              <span style={{
                position: 'absolute', top: 3, width: 10, height: 10,
                borderRadius: '50%', background: '#fff',
                left: showExplorer ? 18 : 3,
                transition: 'left 0.2s',
              }} />
            </span>
            <span className="text-xs">{showExplorer ? 'Activé' : 'Désactivé'}</span>
          </button>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Coups max</span>
          <select
            value={explorerMaxMoves}
            onChange={e => onExplorerMaxMovesChange(Number(e.target.value))}
            className="bg-gray-700 text-white text-sm rounded px-2 py-0.5 border border-gray-600"
          >
            {[8, 10, 12, 15, 20].map(n => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
      </div>

      <button
        onClick={onNewGame}
        disabled={disabled}
        className="btn-primary w-full"
      >
        {t('newGame')}
      </button>
    </div>
  )
}
