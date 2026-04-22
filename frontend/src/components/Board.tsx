import React, { useCallback } from 'react'
import { rcToSq, EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING } from '../types'
import type { MoveData } from '../types'

interface BoardProps {
  board: number[]
  legalMoves: MoveData[]
  onMove: (move: MoveData) => void
  selectedSquare: number | null
  onSelectSquare: (sq: number | null) => void
  disabled?: boolean
  lastMove?: MoveData | null
  highlightSquares?: number[]
  spokenSquares?: number[]
}

const PIECE_WHITE: React.CSSProperties = {
  width: '76%',
  height: '76%',
  borderRadius: '50%',
  background: 'radial-gradient(circle at 38% 32%, #ffffff 0%, #f2f2f2 28%, #d6d6d6 58%, #bbb 82%, #aaa 100%)',
  border: '2px solid #999',
  boxShadow: '0 3px 7px rgba(0,0,0,0.50), 0 1px 2px rgba(0,0,0,0.25), inset 0 2px 4px rgba(255,255,255,0.85)',
  flexShrink: 0,
  cursor: 'pointer',
}

const PIECE_BLACK: React.CSSProperties = {
  width: '76%',
  height: '76%',
  borderRadius: '50%',
  background: 'radial-gradient(circle at 38% 32%, #505050 0%, #1e1e1e 32%, #0a0a0a 65%, #000 100%)',
  border: '2px solid #050505',
  boxShadow: '0 3px 7px rgba(0,0,0,0.75), 0 1px 2px rgba(0,0,0,0.50), inset 0 2px 3px rgba(255,255,255,0.10)',
  flexShrink: 0,
  cursor: 'pointer',
}

const KING_RING_WHITE: React.CSSProperties = {
  position: 'absolute',
  width: '42%',
  height: '42%',
  borderRadius: '50%',
  border: '2px solid rgba(160,100,0,0.75)',
  boxShadow: 'inset 0 0 4px rgba(160,100,0,0.4)',
  pointerEvents: 'none',
}

const KING_RING_BLACK: React.CSSProperties = {
  position: 'absolute',
  width: '42%',
  height: '42%',
  borderRadius: '50%',
  border: '2px solid rgba(210,165,0,0.85)',
  boxShadow: 'inset 0 0 5px rgba(210,165,0,0.5)',
  pointerEvents: 'none',
}

function PieceDisc({ piece, moveable, selected }: { piece: number; moveable: boolean; selected: boolean }) {
  const isWhite = piece === WHITE_MAN || piece === WHITE_KING
  const isKing  = piece === WHITE_KING || piece === BLACK_KING
  const base    = isWhite ? PIECE_WHITE : PIECE_BLACK

  const style: React.CSSProperties = {
    ...base,
    transform: selected ? 'scale(1.08)' : moveable ? 'scale(1.03)' : 'scale(1)',
    transition: 'transform 0.1s',
    outline: moveable && !selected ? '2px solid rgba(212,160,23,0.55)' : 'none',
    outlineOffset: '1px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  }

  return (
    <div style={style}>
      {isKing && <div style={isWhite ? KING_RING_WHITE : KING_RING_BLACK} />}
    </div>
  )
}

export default function Board({
  board,
  legalMoves,
  onMove,
  selectedSquare,
  onSelectSquare,
  disabled = false,
  lastMove = null,
  highlightSquares = [],
  spokenSquares = [],
}: BoardProps) {
  const legalTargets = useCallback((): Set<number> => {
    if (selectedSquare === null) return new Set()
    const targets = new Set<number>()
    for (const m of legalMoves) {
      if (m.path[0] === selectedSquare) targets.add(m.path[m.path.length - 1])
    }
    return targets
  }, [selectedSquare, legalMoves])

  const legalFromSquares = useCallback((): Set<number> => {
    const froms = new Set<number>()
    for (const m of legalMoves) froms.add(m.path[0])
    return froms
  }, [legalMoves])

  const handleCellClick = (sq: number) => {
    if (disabled) return
    const piece = board[sq]
    const targets = legalTargets()
    const froms = legalFromSquares()

    if (targets.has(sq) && selectedSquare !== null) {
      const moves = legalMoves.filter(
        m => m.path[0] === selectedSquare && m.path[m.path.length - 1] === sq
      )
      if (moves.length >= 1) { onMove(moves[0]); onSelectSquare(null) }
      return
    }
    if (froms.has(sq) && piece !== EMPTY) {
      onSelectSquare(sq === selectedSquare ? null : sq)
      return
    }
    onSelectSquare(null)
  }

  const targets   = legalTargets()
  const froms     = legalFromSquares()
  const lastMovePath = lastMove
    ? new Set([...lastMove.path, ...lastMove.captures])
    : new Set<number>()

  const cells: React.ReactNode[] = []

  for (let row = 0; row < 10; row++) {
    for (let col = 0; col < 10; col++) {
      const isDark = (row + col) % 2 === 1
      const sq     = isDark ? rcToSq(row, col) : null
      const piece  = sq !== null ? board[sq] : EMPTY

      const isSelected    = sq !== null && sq === selectedSquare
      const isLegalTarget = sq !== null && targets.has(sq)
      const isMoveable    = sq !== null && froms.has(sq)
      const isLastMove    = sq !== null && lastMovePath.has(sq)
      const isHighlighted = sq !== null && highlightSquares.includes(sq)
      const isSpoken      = sq !== null && spokenSquares.includes(sq)

      // Square background color
      let bg = isDark ? '#9B6B4A' : '#F0CFA0'
      if (isDark) {
        if (isSelected)    bg = '#C8A400'
        else if (isLastMove)    bg = '#B8832A'
        else if (isHighlighted) bg = '#7A4020'
        else                    bg = '#9B6B4A'
      }

      cells.push(
        <div
          key={`${row}-${col}`}
          onClick={() => sq !== null && isDark && handleCellClick(sq)}
          className={isSpoken ? 'spoken-square' : undefined}
          style={{
            backgroundColor: bg,
            aspectRatio: '1',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: isDark && sq !== null && !disabled ? 'pointer' : 'default',
            position: 'relative',
            transition: 'background-color 0.12s',
          }}
        >
          {/* Square number — top right */}
          {isDark && sq !== null && (
            <div style={{
              position: 'absolute',
              top: 2,
              right: 3,
              fontSize: '9px',
              fontWeight: 600,
              color: isSelected ? 'rgba(0,0,0,0.45)' : 'rgba(255,255,255,0.45)',
              lineHeight: 1,
              userSelect: 'none',
              pointerEvents: 'none',
            }}>
              {sq}
            </div>
          )}

          {/* Piece */}
          {isDark && sq !== null && piece !== EMPTY && (
            <PieceDisc piece={piece} moveable={isMoveable} selected={isSelected} />
          )}

          {/* Legal move dot */}
          {isDark && sq !== null && isLegalTarget && piece === EMPTY && (
            <div style={{
              width: '28%',
              height: '28%',
              borderRadius: '50%',
              backgroundColor: 'rgba(0,0,0,0.28)',
              position: 'absolute',
              pointerEvents: 'none',
            }} />
          )}

          {/* Legal capture highlight (over enemy piece) */}
          {isDark && sq !== null && isLegalTarget && piece !== EMPTY && (
            <div style={{
              position: 'absolute',
              inset: 0,
              border: '3px solid rgba(200,164,0,0.85)',
              pointerEvents: 'none',
            }} />
          )}
        </div>
      )
    }
  }

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(10, 1fr)',
      width: '100%',
      maxWidth: '560px',
      border: '3px solid #5C3317',
      borderRadius: '4px',
      overflow: 'hidden',
      boxShadow: '0 8px 32px rgba(0,0,0,0.55)',
    }}>
      {cells}
    </div>
  )
}
