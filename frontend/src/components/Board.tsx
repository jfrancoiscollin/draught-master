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

  // Coin side edge — visible thickness like a real checker
  const rimBg = isWhite
    ? 'linear-gradient(180deg, #cfc0a0 0%, #b0a080 50%, #c0b090 100%)'
    : 'linear-gradient(180deg, #3c2010 0%, #1c0c06 50%, #2a1408 100%)'

  // Top face — lacquered wood, light from top-left
  const topBg = isWhite
    ? 'radial-gradient(ellipse 78% 72% at 38% 32%, #ffffff 0%, #f2e4cc 16%, #ddc8a8 42%, #c8b090 68%, #b4987a 88%, #a08868 100%)'
    : 'radial-gradient(ellipse 78% 72% at 38% 32%, #7a3e1e 0%, #4e2210 22%, #2e1208 48%, #1a0806 74%, #0e0402 90%, #080402 100%)'

  // Strong specular blob — clear 3D sheen
  const specular = isWhite
    ? 'radial-gradient(ellipse 50% 42% at 37% 30%, rgba(255,255,255,1) 0%, rgba(255,255,255,0.80) 20%, rgba(255,255,255,0.30) 50%, transparent 68%)'
    : 'radial-gradient(ellipse 50% 42% at 37% 30%, rgba(255,255,255,0.58) 0%, rgba(255,255,255,0.30) 22%, rgba(255,255,255,0.07) 52%, transparent 70%)'

  // Secondary bounce light on lower-right
  const rimSheen = isWhite
    ? 'radial-gradient(ellipse at 65% 76%, rgba(255,255,255,0.40) 0%, transparent 48%)'
    : 'radial-gradient(ellipse at 65% 76%, rgba(255,255,255,0.10) 0%, transparent 48%)'

  const selectionRing = selected
    ? '0 0 0 3px #d4a017, 0 0 10px rgba(212,160,23,0.55)'
    : moveable
      ? '0 0 0 2px rgba(212,160,23,0.72)'
      : undefined

  // Inner shadow on face gives dome curvature
  const faceInner = isWhite
    ? 'inset 0 -5px 12px rgba(0,0,0,0.20), inset 0 3px 7px rgba(255,255,255,0.45)'
    : 'inset 0 -5px 12px rgba(0,0,0,0.45), inset 0 3px 7px rgba(255,255,255,0.06)'

  const faceShadow = [selectionRing, faceInner].filter(Boolean).join(', ')

  return (
    <div style={{
      width: '86%',
      height: '86%',
      position: 'relative',
      flexShrink: 0,
      transform: `scale(${scale})`,
      transition: 'transform 0.12s ease',
    }}>
      {/* Drop shadow — asymmetric offset for lifted 3D look */}
      <div style={{
        position: 'absolute',
        bottom: '-14%',
        left: '10%',
        right: '6%',
        height: '26%',
        borderRadius: '50%',
        background: isWhite
          ? 'radial-gradient(ellipse, rgba(0,0,0,0.40) 0%, transparent 72%)'
          : 'radial-gradient(ellipse, rgba(0,0,0,0.70) 0%, transparent 72%)',
        filter: 'blur(5px)',
      }} />

      {/* RIM — visible side of the coin (20 % of height) */}
      <div style={{
        position: 'absolute',
        top: '80%',
        left: '2%',
        right: '2%',
        bottom: 0,
        borderRadius: '50%',
        background: rimBg,
        boxShadow: isWhite
          ? 'inset 0 3px 5px rgba(255,255,255,0.35), inset 0 -2px 6px rgba(0,0,0,0.28)'
          : 'inset 0 3px 5px rgba(80,40,10,0.35), inset 0 -2px 6px rgba(0,0,0,0.45)',
      }} />

      {/* TOP FACE — sits above the rim */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: '20%',
        borderRadius: '50%',
        background: topBg,
        boxShadow: faceShadow,
        overflow: 'hidden',
      }}>
        {/* Primary specular highlight */}
        <div style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          background: specular,
          pointerEvents: 'none',
        }} />

        {/* Secondary bounce light */}
        <div style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          background: rimSheen,
          pointerEvents: 'none',
        }} />

        {/* King crown ring */}
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
