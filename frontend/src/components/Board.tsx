import React, { useCallback } from 'react'
import { rcToSq, EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING } from '../types'
import type { MoveData } from '../types'

export interface Arrow {
  from: number
  to: number
  color?: string     // CSS color, default '#9CA3AF'
  opacity?: number   // 0-1, default 0.85
  width?: number     // strokeWidth, default 2.2
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
  const scale   = selected ? 1.08 : moveable ? 1.02 : 1

  // Gradient IDs shared across pieces of the same colour — identical defs,
  // browser uses the first occurrence in document order, which is fine.
  const gid = isWhite ? 'pcw' : 'pcb'
  const ringColor = selected ? '#d4a017' : moveable ? 'rgba(212,160,23,0.65)' : null

  return (
    <div style={{ width: '88%', height: '88%', transform: `scale(${scale})`, transition: 'transform 0.12s ease' }}>
      <svg viewBox="0 0 100 100" width="100%" height="100%"
           style={{ display: 'block', overflow: 'visible' }}>
        <defs>
          {/* Sphere body: radial gradient simulating top-left lighting */}
          <radialGradient id={gid} cx="38%" cy="30%" r="70%">
            {isWhite ? <>
              <stop offset="0%"   stopColor="#f8f0dc"/>
              <stop offset="35%"  stopColor="#e0cda8"/>
              <stop offset="72%"  stopColor="#bfa878"/>
              <stop offset="100%" stopColor="#9c8458"/>
            </> : <>
              <stop offset="0%"   stopColor="#6b3820"/>
              <stop offset="30%"  stopColor="#3c1a08"/>
              <stop offset="68%"  stopColor="#1e0d04"/>
              <stop offset="100%" stopColor="#0e0602"/>
            </>}
          </radialGradient>

          {/* Specular highlight — small bright spot top-left */}
          <radialGradient id={`${gid}s`} cx="32%" cy="26%" r="34%">
            <stop offset="0%"   stopColor={isWhite ? 'rgba(255,255,255,0.82)' : 'rgba(255,255,255,0.28)'}/>
            <stop offset="55%"  stopColor={isWhite ? 'rgba(255,255,255,0.22)' : 'rgba(255,255,255,0.05)'}/>
            <stop offset="100%" stopColor="rgba(255,255,255,0)"/>
          </radialGradient>
        </defs>

        {/* Cast shadow — ellipse below the sphere, slightly offset right */}
        <ellipse cx="53" cy="92" rx="34" ry="6.5"
          fill={isWhite ? 'rgba(0,0,0,0.38)' : 'rgba(0,0,0,0.55)'}/>

        {/* Main sphere */}
        <circle cx="50" cy="46" r="42" fill={`url(#${gid})`}/>

        {/* Thick outer stroke — darkens the edge and fakes spherical roundness,
            no separate rim element needed (eliminates the "flat line" artefact) */}
        <circle cx="50" cy="46" r="42" fill="none"
          stroke={isWhite ? 'rgba(0,0,0,0.20)' : 'rgba(0,0,0,0.55)'}
          strokeWidth="9"/>

        {/* Specular highlight layer */}
        <circle cx="50" cy="46" r="42" fill={`url(#${gid}s)`}/>

        {/* Selection / moveable ring */}
        {ringColor && (
          <circle cx="50" cy="46" r="44" fill="none"
            stroke={ringColor} strokeWidth={selected ? 3.5 : 2.5}/>
        )}

        {/* King crown ring */}
        {isKing && (
          <circle cx="50" cy="46" r="18" fill="none"
            stroke={isWhite ? 'rgba(140,85,0,0.85)' : 'rgba(210,155,0,0.88)'}
            strokeWidth="3.5"/>
        )}
      </svg>
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
            {/* context-stroke makes the arrowhead inherit the line colour */}
            <marker id="bm-arrow" markerWidth="3.5" markerHeight="3" refX="3.2" refY="1.5" orient="auto">
              <polygon points="0 0, 3.5 1.5, 0 3" fill="context-stroke" />
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
            const color   = arrow.color   ?? '#9CA3AF'
            const opacity = arrow.opacity ?? 0.85
            const width   = arrow.width   ?? 2.2
            return (
              <line
                key={i}
                x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={color}
                strokeWidth={width}
                strokeLinecap="round"
                opacity={opacity}
                markerEnd="url(#bm-arrow)"
              />
            )
          })}
        </svg>
      )}
    </div>
  )
}
