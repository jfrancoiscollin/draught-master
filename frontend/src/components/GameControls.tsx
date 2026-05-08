import React from 'react'
import { useLanguage } from '../i18n/LanguageContext'

export type PlayerSide = 'white' | 'random' | 'black'

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
  playerSide: PlayerSide
  onPlayerSideChange: (side: PlayerSide) => void
}

// Mini disc SVGs matching the board piece style
function DiscWhite() {
  return (
    <svg viewBox="0 0 40 28" width="36" height="25">
      <defs>
        <linearGradient id="cw-side" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   stopColor="#9a9a9a"/>
          <stop offset="35%"  stopColor="#d8d8d8"/>
          <stop offset="60%"  stopColor="#f4f4f4"/>
          <stop offset="100%" stopColor="#ffffff"/>
        </linearGradient>
        <linearGradient id="cw-top" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%"   stopColor="#f5f5f5"/>
          <stop offset="100%" stopColor="#ffffff"/>
        </linearGradient>
      </defs>
      {/* side */}
      <path d="M 4,18 A 16,8 0 0,0 36,18 L 36,22 A 16,8 0 0,1 4,22 Z" fill="url(#cw-side)" stroke="#888" strokeWidth="0.5"/>
      {/* top */}
      <ellipse cx="20" cy="18" rx="16" ry="8" fill="url(#cw-top)" stroke="#888" strokeWidth="0.5"/>
    </svg>
  )
}

function DiscBlack() {
  return (
    <svg viewBox="0 0 40 28" width="36" height="25">
      <defs>
        <linearGradient id="cb-side" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   stopColor="#111"/>
          <stop offset="30%"  stopColor="#2a2a2a"/>
          <stop offset="60%"  stopColor="#444"/>
          <stop offset="100%" stopColor="#222"/>
        </linearGradient>
        <linearGradient id="cb-top" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%"   stopColor="#1a1a1a"/>
          <stop offset="100%" stopColor="#2a2a2a"/>
        </linearGradient>
      </defs>
      <path d="M 4,18 A 16,8 0 0,0 36,18 L 36,22 A 16,8 0 0,1 4,22 Z" fill="url(#cb-side)" stroke="#555" strokeWidth="0.5"/>
      <ellipse cx="20" cy="18" rx="16" ry="8" fill="url(#cb-top)" stroke="#555" strokeWidth="0.5"/>
    </svg>
  )
}

function DiscRandom() {
  return (
    <svg viewBox="0 0 40 34" width="36" height="30">
      <defs>
        <linearGradient id="cr-wside" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   stopColor="#9a9a9a"/>
          <stop offset="60%"  stopColor="#f4f4f4"/>
          <stop offset="100%" stopColor="#ffffff"/>
        </linearGradient>
        <linearGradient id="cr-wtop" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%"   stopColor="#f5f5f5"/>
          <stop offset="100%" stopColor="#ffffff"/>
        </linearGradient>
        <linearGradient id="cr-bside" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   stopColor="#111"/>
          <stop offset="60%"  stopColor="#444"/>
          <stop offset="100%" stopColor="#222"/>
        </linearGradient>
        <linearGradient id="cr-btop" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%"   stopColor="#1a1a1a"/>
          <stop offset="100%" stopColor="#2a2a2a"/>
        </linearGradient>
      </defs>
      {/* white disc (bottom) */}
      <path d="M 4,22 A 16,8 0 0,0 36,22 L 36,26 A 16,8 0 0,1 4,26 Z" fill="url(#cr-wside)" stroke="#888" strokeWidth="0.5"/>
      <ellipse cx="20" cy="22" rx="16" ry="8" fill="url(#cr-wtop)" stroke="#888" strokeWidth="0.5"/>
      {/* black disc (top) */}
      <path d="M 4,13 A 16,8 0 0,0 36,13 L 36,17 A 16,8 0 0,1 4,17 Z" fill="url(#cr-bside)" stroke="#555" strokeWidth="0.5"/>
      <ellipse cx="20" cy="13" rx="16" ry="8" fill="url(#cr-btop)" stroke="#555" strokeWidth="0.5"/>
    </svg>
  )
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
  playerSide,
  onPlayerSideChange,
}: GameControlsProps) {
  const { t } = useLanguage()

  const getResultLabel = (res: string | null): string => {
    if (res === 'white') return t('resultWhiteWins')
    if (res === 'black') return t('resultBlackWins')
    if (res === 'draw') return t('resultDraw')
    return ''
  }

  const sides: { value: PlayerSide; label: string; disc: React.ReactNode }[] = [
    { value: 'black',  label: 'Noirs',    disc: <DiscBlack /> },
    { value: 'random', label: 'Aléatoire', disc: <DiscRandom /> },
    { value: 'white',  label: 'Blancs',   disc: <DiscWhite /> },
  ]

  return (
    <div className="panel flex flex-col gap-3">
      <h3 className="text-lg font-bold text-amber-600">{t('controls')}</h3>

      {/* Player side picker */}
      <div className="flex flex-col gap-1.5">
        <span className="text-sm text-gray-400">Jouer avec les</span>
        <div className="flex gap-2">
          {sides.map(({ value, label, disc }) => {
            const active = playerSide === value
            return (
              <button
                key={value}
                onClick={() => onPlayerSideChange(value)}
                title={label}
                className="flex-1 flex flex-col items-center gap-1 py-2 rounded-xl border transition-all"
                style={{
                  background: active ? 'rgba(217,119,6,0.15)' : '#1f2937',
                  borderColor: active ? '#d97706' : '#374151',
                }}
              >
                {disc}
                <span className="text-xs" style={{ color: active ? '#fbbf24' : '#6b7280' }}>{label}</span>
              </button>
            )
          })}
        </div>
      </div>

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
