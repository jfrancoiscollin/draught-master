import React, { useCallback } from 'react'
import { rcToSq, EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING } from '../types'
import type { MoveData } from '../types'

export interface Arrow {
  from: number
  to: number
}

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
  arrows?: Arrow[]
  // When provided, these squares can be selected even if not in legalMoves,
  // and any subsequent dark-square click triggers onMove (free-move mode).
  freeSelectSquares?: Set<number>
  flipped?: boolean
}

function PieceDisc({ piece, moveable, selected }: { piece: number; moveable: boolean; selected: boolean }) {
  const isWhite = piece === WHITE_MAN || piece === WHITE_KING
  const isKing  = piece === WHITE_KING || piece === BLACK_KING

  const scale = selected ? 1.10 : moveable ? 1.03 : 1

  // Warm wooden tones, flat rim (only 8% height)
  const rimBg = isWhite
    ? 'linear-gradient(to bottom, #c8b898 0%, #a89070 100%)'
    : 'linear-gradient(to bottom, #2a1a0e 0%, #140a04 100%)'

  // Top face — warm wood gradient, light from top-left
  const topBg = isWhite
    ? 'radial-gradient(ellipse at 36% 28%, #fff8f0 0%, #ede0cc 28%, #d8c8a8 58%, #c4b090 85%, #b8a080 100%)'
    : 'radial-gradient(ellipse at 36% 28%, #6a3e22 0%, #3e2010 32%, #1e0e06 64%, #0e0604 85%, #080402 100%)'

  // Specular highlight — simulates top-lit lacquered wood
  const specular = isWhite
    ? 'radial-gradient(ellipse at 35% 25%, rgba(255,255,255,0.92) 0%, rgba(255,255,255,0.35) 28%, transparent 58%)'
    : 'radial-gradient(ellipse at 35% 25%, rgba(255,255,255,0.32) 0%, rgba(255,255,255,0.08) 30%, transparent 58%)'

  // Subtle sheen on lower-right (rim reflection)
  const rimSheen = isWhite
    ? 'radial-gradient(ellipse at 62% 78%, rgba(255,255,255,0.45) 0%, transparent 50%)'
    : 'radial-gradient(ellipse at 62% 78%, rgba(255,255,255,0.12) 0%, transparent 50%)'

  const faceGlow = selected
    ? '0 0 0 3px rgba(212,160,23,0.95)'
    : moveable
      ? '0 0 0 2px rgba(212,160,23,0.5)'
      : 'none'

  return (
    // perspective + rotateX gives the "coin viewed from above" flat inclined look
    <div style={{
      width: '86%',
      height: '86%',
      position: 'relative',
      flexShrink: 0,
      transform: `perspective(280px) rotateX(16deg) scale(${scale})`,
      transition: 'transform 0.12s ease',
    }}>
      {/* Drop shadow — elliptical, offset downward for depth */}
      <div style={{
        position: 'absolute',
        bottom: '-10%',
        left: '8%',
        right: '8%',
        height: '22%',
        borderRadius: '50%',
        background: `radial-gradient(ellipse, ${isWhite ? 'rgba(0,0,0,0.32)' : 'rgba(0,0,0,0.58)'} 0%, transparent 78%)`,
        filter: 'blur(3px)',
      }} />

      {/* Thin rim — only 8% of height, warm wood side */}
      <div style={{
        position: 'absolute',
        top: '92%',
        left: '3%',
        right: '3%',
        bottom: 0,
        borderRadius: '50%',
        background: rimBg,
      }} />

      {/* Top face */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: '8%',
        borderRadius: '50%',
        background: topBg,
        boxShadow: faceGlow,
        overflow: 'hidden',
      }}>
        {/* Primary specular */}
        <div style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          background: specular,
          pointerEvents: 'none',
        }} />

        {/* Secondary rim sheen */}
        <div style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          background: rimSheen,
          pointerEvents: 'none',
        }} />

        {/* King marker */}
        {isKing && (
          <div style={{
            position: 'absolute',
            top: '24%',
            left: '24%',
            right: '24%',
            bottom: '24%',
            borderRadius: '50%',
            border: `2px solid ${isWhite ? 'rgba(180,120,0,0.9)' : 'rgba(215,165,0,0.9)'}`,
            boxShadow: isWhite
              ? 'inset 0 0 5px rgba(185,125,0,0.45), 0 0 4px rgba(185,125,0,0.3)'
              : 'inset 0 0 5px rgba(220,170,0,0.5), 0 0 4px rgba(220,170,0,0.35)',
            pointerEvents: 'none',
          }} />
        )}
      </div>
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
  arrows = [],
  freeSelectSquares,
  flipped = false,
}: BoardProps) {
  // Convert square number to center % coordinates in the 100×100 SVG viewBox
  function sqCenter(sq: number): { x: number; y: number } {
    const row = Math.floor((sq - 1) / 5)
    const colInRow = (sq - 1) % 5
    const col = colInRow * 2 + (row % 2 === 0 ? 1 : 0)
    const r = flipped ? 9 - row : row
    const c = flipped ? 9 - col : col
    return { x: (c + 0.5) * 10, y: (r + 0.5) * 10 }
  }
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

    // Free-move mode: no server-provided legal moves, use freeSelectSquares
    if (freeSelectSquares && freeSelectSquares.size > 0) {
      if (selectedSquare !== null && sq !== selectedSquare) {
        // Re-select another friendly piece without submitting
        if (freeSelectSquares.has(sq) && piece !== EMPTY) {
          onSelectSquare(sq)
          return
        }
        // Otherwise treat as destination
        onMove({ path: [selectedSquare, sq], captures: [] })
        onSelectSquare(null)
        return
      }
      if (freeSelectSquares.has(sq) && piece !== EMPTY) {
        onSelectSquare(sq === selectedSquare ? null : sq)
        return
      }
      onSelectSquare(null)
      return
    }

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

  for (let r = 0; r < 10; r++) {
    for (let c = 0; c < 10; c++) {
      const row = flipped ? 9 - r : r
      const col = flipped ? 9 - c : c
      const isDark = (row + col) % 2 === 1
      const sq     = isDark ? rcToSq(row, col) : null
      const piece  = sq !== null ? board[sq] : EMPTY

      const isSelected    = sq !== null && sq === selectedSquare
      const isLegalTarget = sq !== null && targets.has(sq)
      const isMoveable    = sq !== null && (froms.has(sq) || (freeSelectSquares ? freeSelectSquares.has(sq) : false))
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
          key={`${r}-${c}`}
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
      position: 'relative',
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

      {/* Arrow overlay */}
      {arrows.length > 0 && (
        <svg
          viewBox="0 0 100 100"
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            zIndex: 10,
          }}
        >
          <defs>
            <marker id="bm-arrow" markerWidth="3.5" markerHeight="3" refX="3.2" refY="1.5" orient="auto">
              <polygon points="0 0, 3.5 1.5, 0 3" fill="#9CA3AF" />
            </marker>
          </defs>
          {arrows.map((arrow, i) => {
            const f = sqCenter(arrow.from)
            const t = sqCenter(arrow.to)
            const dx = t.x - f.x
            const dy = t.y - f.y
            const len = Math.sqrt(dx * dx + dy * dy)
            if (len < 1) return null
            const ux = dx / len
            const uy = dy / len
            const x1 = f.x + ux * 3.8
            const y1 = f.y + uy * 3.8
            const x2 = t.x - ux * 4.2
            const y2 = t.y - uy * 4.2
            return (
              <line
                key={i}
                x1={x1} y1={y1} x2={x2} y2={y2}
                stroke="#9CA3AF"
                strokeWidth="2.2"
                strokeLinecap="round"
                opacity="0.85"
                markerEnd="url(#bm-arrow)"
              />
            )
          })}
        </svg>
      )}
    </div>
  )
}
