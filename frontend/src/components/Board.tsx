import React, { useCallback, useState, useLayoutEffect, useRef } from 'react'
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
  const scale   = selected ? 1.05 : moveable ? 1.01 : 1
  const pfx     = isWhite ? 'pw' : 'pb'

  // rx=96 → piece spans x:4–196, filling 96% of the 200-unit viewBox
  // Combined with SVG at 100% of cell this puts the lateral edges nearly flush
  const ry       = 40
  const sideEndY = 130
  const sidePath = `M 4,90 A 96,${ry} 0 0,0 196,90 L 196,${sideEndY} A 96,${ry} 0 0,1 4,${sideEndY} Z`

  const sideStops  = isWhite
    ? ['#a8a8a8', '#dcdcdc', '#f0f0f0']
    : ['#000000', '#2a2a2a', '#4a4a4a']
  const topStops   = isWhite
    ? ['#ffffff', '#f0f0f0', '#d0d0d0']
    : ['#5a5a5a', '#2a2a2a', '#0a0a0a']
  const shdOpacity = isWhite ? 0.25 : 0.30
  const sideStroke = isWhite ? '#9a9a9a' : '#000000'
  const topStroke  = isWhite ? '#b0b0b0' : '#000000'
  const hlRy       = isWhite ? 12 : 11
  const hlOpacity  = isWhite ? 0.55 : 0.40
  const hlColor    = isWhite ? '#ffffff' : '#888888'
  const kingColor  = isWhite ? 'rgba(100,60,0,0.85)' : 'rgba(200,140,0,0.85)'

  return (
    <svg
      viewBox="0 0 200 200"
      style={{ width: '100%', height: '100%', transform: `scale(${scale})`, transition: 'transform 0.12s ease' }}
    >
      <defs>
        <linearGradient id={`${pfx}-side`} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   stopColor={sideStops[0]}/>
          <stop offset="40%"  stopColor={sideStops[1]}/>
          <stop offset="100%" stopColor={sideStops[2]}/>
        </linearGradient>
        <radialGradient id={`${pfx}-top`} cx="65%" cy="40%" r="70%">
          <stop offset="0%"   stopColor={topStops[0]}/>
          <stop offset="70%"  stopColor={topStops[1]}/>
          <stop offset="100%" stopColor={topStops[2]}/>
        </radialGradient>
        <radialGradient id={`${pfx}-shd`} cx="50%" cy="50%" r="50%">
          <stop offset="0%"   stopColor="#000000" stopOpacity={shdOpacity}/>
          <stop offset="100%" stopColor="#000000" stopOpacity="0"/>
        </radialGradient>
      </defs>

      {/* Ombre portée */}
      <ellipse cx="100" cy="170" rx="90" ry="9" fill={`url(#${pfx}-shd)`}/>

      {/* Tranche */}
      <path d={sidePath} fill={`url(#${pfx}-side)`} stroke={sideStroke} strokeWidth="0.5"/>

      {/* Face du dessus */}
      <ellipse cx="100" cy="90" rx="96" ry={ry}
        fill={`url(#${pfx}-top)`} stroke={topStroke} strokeWidth="0.5"/>

      {/* Reflet */}
      <ellipse cx="118" cy="75" rx="42" ry={hlRy} fill={hlColor} opacity={hlOpacity}/>

      {/* Anneau sélection */}
      {selected && (
        <ellipse cx="100" cy="90" rx="96" ry={ry}
          fill="none" stroke="#D4A017" strokeWidth="8"/>
      )}
      {/* Anneau jouable — très discret */}
      {!selected && moveable && (
        <ellipse cx="100" cy="90" rx="96" ry={ry}
          fill="none"
          stroke={isWhite ? 'rgba(80,80,80,0.30)' : 'rgba(212,160,23,0.30)'}
          strokeWidth="3"
        />
      )}

      {/* Anneau dame */}
      {isKing && (
        <ellipse cx="100" cy="90" rx="60" ry={Math.round(ry * 0.55)}
          fill="none" stroke={kingColor} strokeWidth="5"/>
      )}
    </svg>
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
  // ── Smooth piece movement overlay ───────────────────────────────────────
  const [animPiece,   setAnimPiece]   = useState<number>(EMPTY)
  const [animX,       setAnimX]       = useState(0)
  const [animY,       setAnimY]       = useState(0)
  const [animVisible, setAnimVisible] = useState(false)
  const [animHideSq,  setAnimHideSq]  = useState<number | null>(null)
  const [animMoving,  setAnimMoving]  = useState(false)
  const prevLastMoveRef               = useRef<MoveData | null | undefined>(undefined)
  const animTimerRef                  = useRef<ReturnType<typeof setTimeout> | null>(null)

  // useLayoutEffect fires synchronously before the browser paints.
  // This prevents the one-frame flash where the piece appears at the destination
  // before being hidden — which caused the "B→A→B" reversal on white moves.
  useLayoutEffect(() => {
    if (lastMove === prevLastMoveRef.current) return
    prevLastMoveRef.current = lastMove
    if (!lastMove) { setAnimVisible(false); return }

    const from  = lastMove.path[0]
    const to    = lastMove.path[lastMove.path.length - 1]
    const piece = board[to]
    if (piece === EMPTY) { setAnimVisible(false); return }

    const src = sqCenter(from)
    const dst = sqCenter(to)

    if (animTimerRef.current) clearTimeout(animTimerRef.current)

    // Place overlay at source with no transition (synchronously, before paint)
    setAnimPiece(piece)
    setAnimX(src.x)
    setAnimY(src.y)
    setAnimHideSq(to)
    setAnimMoving(false)
    setAnimVisible(true)

    // Two rAFs ensure the browser paints the initial position before transitioning
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setAnimX(dst.x)
        setAnimY(dst.y)
        setAnimMoving(true)
      })
    })

    animTimerRef.current = setTimeout(() => {
      setAnimVisible(false)
      setAnimHideSq(null)
    }, 380)
  }, [lastMove]) // eslint-disable-line react-hooks/exhaustive-deps
  // ────────────────────────────────────────────────────────────────────────

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

          {/* Piece — hidden at animation destination while overlay is in flight */}
          {isDark && sq !== null && piece !== EMPTY && sq !== animHideSq && (
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

      {/* Moving piece overlay */}
      {animVisible && (
        <div
          style={{
            position: 'absolute',
            left:   `${animX - 5}%`,
            top:    `${animY - 5}%`,
            width:  '10%',
            height: '10%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
            zIndex: 20,
            transition: animMoving
              ? 'left 0.28s cubic-bezier(0.25,0,0.35,1), top 0.28s cubic-bezier(0.25,0,0.35,1)'
              : 'none',
          }}
        >
          <PieceDisc piece={animPiece} moveable={false} selected={false} />
        </div>
      )}

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
