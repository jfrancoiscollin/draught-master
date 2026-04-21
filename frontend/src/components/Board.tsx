import React, { useCallback } from 'react'
import { sqToRowCol, rcToSq, EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING } from '../types'
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

function PieceIcon({ piece }: { piece: number }) {
  if (piece === WHITE_MAN) {
    return <div className="piece piece-white w-full h-full" />
  }
  if (piece === WHITE_KING) {
    return (
      <div className="piece piece-white w-full h-full flex items-center justify-center">
        <span style={{ fontSize: '65%', lineHeight: 1, color: '#8B4513' }}>♛</span>
      </div>
    )
  }
  if (piece === BLACK_MAN) {
    return <div className="piece piece-black w-full h-full" />
  }
  if (piece === BLACK_KING) {
    return (
      <div className="piece piece-black w-full h-full flex items-center justify-center">
        <span style={{ fontSize: '65%', lineHeight: 1, color: '#D4A017' }}>♛</span>
      </div>
    )
  }
  return null
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
      if (m.path[0] === selectedSquare) {
        targets.add(m.path[m.path.length - 1])
      }
    }
    return targets
  }, [selectedSquare, legalMoves])

  const legalFromSquares = useCallback((): Set<number> => {
    const froms = new Set<number>()
    for (const m of legalMoves) {
      froms.add(m.path[0])
    }
    return froms
  }, [legalMoves])

  const handleCellClick = (sq: number) => {
    if (disabled) return
    const piece = board[sq]
    const targets = legalTargets()
    const froms = legalFromSquares()

    if (targets.has(sq) && selectedSquare !== null) {
      const possibleMoves = legalMoves.filter(
        m => m.path[0] === selectedSquare && m.path[m.path.length - 1] === sq
      )
      if (possibleMoves.length >= 1) {
        onMove(possibleMoves[0])
        onSelectSquare(null)
      }
      return
    }

    if (froms.has(sq) && piece !== EMPTY) {
      onSelectSquare(sq === selectedSquare ? null : sq)
      return
    }

    onSelectSquare(null)
  }

  const targets = legalTargets()
  const lastMovePath = lastMove ? new Set([...lastMove.path, ...lastMove.captures]) : new Set<number>()

  const cells: React.ReactNode[] = []

  for (let row = 0; row < 10; row++) {
    for (let col = 0; col < 10; col++) {
      const isDark = (row + col) % 2 === 1
      const sq = isDark ? rcToSq(row, col) : null
      const isSelected = sq !== null && sq === selectedSquare
      const isLegalTarget = sq !== null && targets.has(sq)
      const isMoveable = sq !== null && legalFromSquares().has(sq)
      const isSpoken = sq !== null && spokenSquares.includes(sq)
      const isLastMove = sq !== null && lastMovePath.has(sq)
      const isHighlighted = sq !== null && highlightSquares.includes(sq)
      const piece = sq !== null ? board[sq] : EMPTY

      let bgColor = isDark ? '#8B4513' : '#FFFFFF'
      if (isDark) {
        if (isSelected) bgColor = '#D4A017'
        else if (isLastMove) bgColor = '#A0522D'
        else if (isHighlighted) bgColor = '#6B3410'
        else bgColor = '#8B4513'
      }

      cells.push(
        <div
          key={`${row}-${col}`}
          onClick={() => sq !== null && isDark && handleCellClick(sq)}
          className={isSpoken ? 'spoken-square' : undefined}
          style={{
            backgroundColor: bgColor,
            aspectRatio: '1',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: isDark && sq !== null && !disabled ? 'pointer' : 'default',
            position: 'relative',
            transition: 'background-color 0.15s',
          }}
        >
          {isDark && sq !== null && (
            <>
              {piece !== EMPTY && (
                <div
                  style={{
                    width: '80%',
                    height: '80%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    position: 'relative',
                    zIndex: 1,
                    borderRadius: '50%',
                    outline: isMoveable && !isSelected ? '2px solid rgba(212,160,23,0.6)' : 'none',
                  }}
                >
                  <PieceIcon piece={piece} />
                </div>
              )}
              {isLegalTarget && piece === EMPTY && (
                <div
                  style={{
                    width: '30%',
                    height: '30%',
                    borderRadius: '50%',
                    backgroundColor: 'rgba(212, 160, 23, 0.85)',
                    position: 'absolute',
                    zIndex: 2,
                  }}
                />
              )}
              {isLegalTarget && piece !== EMPTY && (
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    border: '3px solid rgba(212, 160, 23, 0.85)',
                    zIndex: 3,
                    pointerEvents: 'none',
                  }}
                />
              )}
              <div
                style={{
                  position: 'absolute',
                  bottom: 1,
                  right: 2,
                  fontSize: '8px',
                  color: 'rgba(255,255,255,0.35)',
                  lineHeight: 1,
                  userSelect: 'none',
                }}
              >
                {sq}
              </div>
            </>
          )}
        </div>
      )
    }
  }

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(10, 1fr)',
        width: '100%',
        maxWidth: '560px',
        border: '3px solid #5a3010',
        borderRadius: '4px',
        overflow: 'hidden',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      }}
    >
      {cells}
    </div>
  )
}
