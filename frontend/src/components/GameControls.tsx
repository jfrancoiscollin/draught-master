import React from 'react'
import { resultLabel } from '../types'

interface GameControlsProps {
  result: string | null
  turn: 'white' | 'black'
  moveCount: number
  aiDepth: number
  onNewGame: () => void
  onAiDepthChange: (depth: number) => void
  disabled?: boolean
}

export default function GameControls({
  result,
  turn,
  moveCount,
  aiDepth,
  onNewGame,
  onAiDepthChange,
  disabled = false,
}: GameControlsProps) {
  return (
    <div className="panel flex flex-col gap-3">
      <h3 className="text-lg font-bold text-green-400">Contrôles</h3>

      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-400">Trait :</span>
        <span className={`font-semibold px-2 py-0.5 rounded ${turn === 'white' ? 'bg-gray-200 text-gray-900' : 'bg-gray-800 text-gray-200 border border-gray-600'}`}>
          {turn === 'white' ? '⚪ Blancs' : '⚫ Noirs'}
        </span>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-400">Coups joués :</span>
        <span className="text-gray-200 font-mono">{moveCount}</span>
      </div>

      {result && (
        <div className="bg-yellow-900 border border-yellow-600 rounded-lg px-3 py-2 text-center">
          <span className="text-yellow-300 font-bold">{resultLabel(result)}</span>
        </div>
      )}

      <div className="flex flex-col gap-1">
        <label className="text-sm text-gray-400">
          Niveau IA (profondeur) : <span className="text-white font-semibold">{aiDepth}</span>
        </label>
        <input
          type="range"
          min={1}
          max={8}
          value={aiDepth}
          onChange={e => onAiDepthChange(Number(e.target.value))}
          className="w-full accent-green-500"
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>Facile</span>
          <span>Expert</span>
        </div>
      </div>

      <button
        onClick={onNewGame}
        disabled={disabled}
        className="btn-primary w-full"
      >
        Nouvelle partie
      </button>
    </div>
  )
}
