import React, { useState, useCallback } from 'react'
import Board from './Board'
import { fenToBoard, boardToFen } from '../utils/fen'
import { EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING } from '../types'

interface Props {
  source: string
  page: number
  number: number
  initialFen?: string
  onClose: () => void
  lang?: 'fr' | 'en'
}

const CYCLE = [EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING]

/**
 * Inline FEN editor for the strategy diagram modal.
 *
 * Click a dark square to cycle through ``empty → white man → white king
 * → black man → black king → empty``. Light squares are ignored (FMJD
 * draughts uses only the 50 dark squares).
 *
 * Output is a JSON entry the user pastes into
 * ``backend/strategy/pages/<source>/diagrams_fens.json``. No backend
 * write path — keeps the deploy filesystem read-only and routes
 * annotations through a normal PR for review.
 */
const FenAnnotator: React.FC<Props> = ({
  source,
  page,
  number,
  initialFen,
  onClose,
  lang = 'fr',
}) => {
  const [board, setBoard] = useState<number[]>(() =>
    initialFen ? fenToBoard(initialFen) : new Array(51).fill(EMPTY),
  )
  const [turn, setTurn] = useState<'W' | 'B'>('W')
  const [copied, setCopied] = useState<'fen' | 'json' | null>(null)

  const cyclePiece = useCallback((sq: number | null) => {
    if (sq === null || sq < 1 || sq > 50) return
    setBoard(prev => {
      const next = [...prev]
      const cur = prev[sq]
      const idx = CYCLE.indexOf(cur)
      next[sq] = CYCLE[(idx + 1) % CYCLE.length]
      return next
    })
  }, [])

  const clear = useCallback(() => {
    setBoard(new Array(51).fill(EMPTY))
  }, [])

  const fen = boardToFen(board, turn)
  const jsonEntry = JSON.stringify(
    {
      page,
      number,
      fen,
      _human_verified: true,
    },
    null,
    2,
  )

  const copy = (kind: 'fen' | 'json') => {
    const text = kind === 'fen' ? fen : jsonEntry
    navigator.clipboard.writeText(text).then(() => {
      setCopied(kind)
      setTimeout(() => setCopied(null), 1500)
    })
  }

  const whites = board.filter(p => p === WHITE_MAN || p === WHITE_KING).length
  const blacks = board.filter(p => p === BLACK_MAN || p === BLACK_KING).length

  return (
    <div className="space-y-3">
      <div className="text-[10px] uppercase tracking-wide text-gray-500 flex items-baseline justify-between">
        <span>
          {lang === 'fr' ? 'Éditeur FEN' : 'FEN editor'} · {source} p.{page} #{number}
        </span>
        <span className="text-gray-400 normal-case">
          {whites} {lang === 'fr' ? 'blancs' : 'white'} / {blacks}{' '}
          {lang === 'fr' ? 'noirs' : 'black'}
        </span>
      </div>
      <Board
        board={board}
        legalMoves={[]}
        onMove={() => {}}
        selectedSquare={null}
        onSelectSquare={cyclePiece}
        disabled={false}
      />
      <p className="text-[10px] text-gray-500">
        {lang === 'fr'
          ? 'Clic sur une case sombre : vide → pion blanc → dame blanche → pion noir → dame noire → vide'
          : 'Click a dark square: empty → white man → white king → black man → black king → empty'}
      </p>
      <div className="flex items-center gap-2 flex-wrap">
        <label className="text-xs text-gray-300 flex items-center gap-1">
          {lang === 'fr' ? 'Trait :' : 'Turn:'}
          <select
            value={turn}
            onChange={e => setTurn(e.target.value as 'W' | 'B')}
            className="bg-gray-800 text-gray-100 rounded px-2 py-1 border border-gray-700"
          >
            <option value="W">{lang === 'fr' ? 'Blancs' : 'White'}</option>
            <option value="B">{lang === 'fr' ? 'Noirs' : 'Black'}</option>
          </select>
        </label>
        <button
          onClick={clear}
          className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-white text-xs rounded"
        >
          {lang === 'fr' ? 'Tout effacer' : 'Clear'}
        </button>
        <button
          onClick={() => copy('fen')}
          className="px-2 py-1 bg-amber-700 hover:bg-amber-600 text-white text-xs rounded"
        >
          {copied === 'fen' ? '✓' : lang === 'fr' ? 'Copier FEN' : 'Copy FEN'}
        </button>
        <button
          onClick={() => copy('json')}
          className="px-2 py-1 bg-amber-700 hover:bg-amber-600 text-white text-xs rounded font-medium"
        >
          {copied === 'json'
            ? '✓'
            : lang === 'fr'
              ? 'Copier entrée JSON'
              : 'Copy JSON entry'}
        </button>
        <button
          onClick={onClose}
          className="ml-auto px-2 py-1 text-gray-400 hover:text-white text-xs"
        >
          {lang === 'fr' ? 'Fermer' : 'Close'}
        </button>
      </div>
      <pre className="text-[10px] text-gray-300 bg-black bg-opacity-40 p-2 rounded overflow-x-auto whitespace-pre-wrap break-all font-mono">
        {fen}
      </pre>
    </div>
  )
}

export default FenAnnotator
