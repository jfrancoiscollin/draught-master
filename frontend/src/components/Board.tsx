import React, { useCallback, useState, useLayoutEffect, useRef, useId } from 'react'
import { rcToSq, EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING } from '../types'
import type { MoveData } from '../types'

export interface Arrow {
  from: number
  to: number
  color?: string     // CSS color, default '#9CA3AF'
  opacity?: number   // 0-1, default 0.85
  width?: number     // strokeWidth, default 2.2
}

export type BoardTheme = 'classic' | 'wood' | 'wood2'

// SVG with feTurbulence wood-grain filter encoded as a CSS background data URI.
// Using base64 avoids URL-encoding issues with '#' in color values.
// Appending "0 0/100% 100%" to the url() sets position + size in the background shorthand.
function _woodBg(svgContent: string): string {
  return `url("data:image/svg+xml;base64,${btoa(svgContent)}") 0 0/100% 100%`
}
const _W2_LIGHT = _woodBg(
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">` +
  `<defs>` +
  `<linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">` +
  `<stop offset="0" stop-color="#fff3d6"/>` +
  `<stop offset=".5" stop-color="#fae8c2"/>` +
  `<stop offset="1" stop-color="#f0dcaa"/>` +
  `</linearGradient>` +
  `<filter id="g">` +
  `<feTurbulence type="fractalNoise" baseFrequency="0.04 0.6" numOctaves="2" seed="3"/>` +
  `<feColorMatrix values="0 0 0 0 0.7 0 0 0 0 0.55 0 0 0 0 0.32 0 0 0 0.1 0"/>` +
  `<feComposite in2="SourceGraphic" operator="in"/>` +
  `<feComposite in="SourceGraphic" operator="over"/>` +
  `</filter>` +
  `</defs>` +
  `<rect width="100" height="100" fill="url(#lg)" filter="url(#g)"/>` +
  `</svg>`
)
const _W2_DARK = _woodBg(
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">` +
  `<defs>` +
  `<linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">` +
  `<stop offset="0" stop-color="#a87148"/>` +
  `<stop offset=".5" stop-color="#8e5a30"/>` +
  `<stop offset="1" stop-color="#74471f"/>` +
  `</linearGradient>` +
  `<filter id="g">` +
  `<feTurbulence type="fractalNoise" baseFrequency="0.04 0.6" numOctaves="2" seed="7"/>` +
  `<feColorMatrix values="0 0 0 0 0.25 0 0 0 0 0.15 0 0 0 0 0.06 0 0 0 0.2 0"/>` +
  `<feComposite in2="SourceGraphic" operator="in"/>` +
  `<feComposite in="SourceGraphic" operator="over"/>` +
  `</filter>` +
  `</defs>` +
  `<rect width="100" height="100" fill="url(#lg)" filter="url(#g)"/>` +
  `</svg>`
)

const THEMES: Record<BoardTheme, {
  light: string
  dark: string
  border: string
  selectedBg: string
  lastMoveBg: string
  highlightBg: string
}> = {
  classic: {
    light:       '#F0CFA0',
    dark:        '#9B6B4A',
    border:      '#5C3317',
    selectedBg:  'rgba(186,220,255,0.42)',
    lastMoveBg:  'rgba(186,220,255,0.26)',
    highlightBg: 'rgba(186,220,255,0.16)',
  },
  wood: {
    light:       'linear-gradient(135deg,#fbecce 0%,#f3e1b8 50%,#e8d2a0 100%)',
    dark:        'linear-gradient(135deg,#dab084 0%,#c89868 50%,#b07f4a 100%)',
    border:      '#74471f',
    selectedBg:  'rgba(255,255,255,0.48)',
    lastMoveBg:  'rgba(255,255,255,0.28)',
    highlightBg: 'rgba(255,255,255,0.16)',
  },
  wood2: {
    light:       _W2_LIGHT,
    dark:        _W2_DARK,
    border:      '#3e1f08',
    selectedBg:  'rgba(255,255,255,0.48)',
    lastMoveBg:  'rgba(255,255,255,0.28)',
    highlightBg: 'rgba(255,255,255,0.16)',
  },
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
  /** Pieces visually marked "in danger" (e.g. hanging, can be captured
   *  next turn). Rendered as a red ring so it's distinguishable from
   *  generic highlightSquares (which are used for hover/motif hints). */
  warningSquares?: number[]
  /** Persistent overlay flagging geometric weaknesses (and outposts).
   *  Each entry is rendered as a small colored dot in a fixed corner
   *  of the square — different corner per category, so up to four dots
   *  can stack without occluding. Distinct from highlightSquares (one
   *  amber tint, used for focus/click) and warningSquares (red ring,
   *  used for hanging-piece danger). */
  flagSquares?: {
    isolated?: number[]
    backward?: number[]
    holes?: number[]
    outposts?: number[]
  }
  spokenSquares?: number[]
  arrows?: Arrow[]
  // When provided, these squares can be selected even if not in legalMoves,
  // and any subsequent dark-square click triggers onMove (free-move mode).
  freeSelectSquares?: Set<number>
  flipped?: boolean
  theme?: BoardTheme
}

function sqRowCol(sq: number): { row: number; col: number } {
  const row = Math.floor((sq - 1) / 5)
  const colInRow = (sq - 1) % 5
  const col = colInRow * 2 + (row % 2 === 0 ? 1 : 0)
  return { row, col }
}

// Returns the capture square (if any) that lies strictly between sq1 and sq2 on a diagonal
function captureBetween(sq1: number, sq2: number, caps: number[]): number | null {
  const { row: r1, col: c1 } = sqRowCol(sq1)
  const { row: r2, col: c2 } = sqRowCol(sq2)
  for (const cap of caps) {
    const { row: rc, col: cc } = sqRowCol(cap)
    const inRow = r1 < r2 ? rc > r1 && rc < r2 : rc > r2 && rc < r1
    const inCol = c1 < c2 ? cc > c1 && cc < c2 : cc > c2 && cc < c1
    if (inRow && inCol && Math.abs(rc - r1) === Math.abs(cc - c1)) return cap
  }
  return null
}

function PieceDisc({ piece, moveable, selected }: { piece: number; moveable: boolean; selected: boolean }) {
  const isWhite = piece === WHITE_MAN || piece === WHITE_KING
  const isKing  = piece === WHITE_KING || piece === BLACK_KING
  const scale   = selected ? 1.05 : moveable ? 1.01 : 1
  // Make every `<defs>` id unique on the page. Inline SVGs share the
  // global document scope, so reusing 'pw-side' / 'pb-side' for the
  // 40 pieces on the board lets some browsers (notably Edge / Chromium
  // on Windows) resolve every `url(#pw-side)` to the wrong gradient
  // and render the pieces as almost-invisible outlines.
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  const pfx = `${isWhite ? 'pw' : 'pb'}-${uid}`

  return (
    <svg
      viewBox="0 0 200 200"
      style={{ width: '100%', height: '100%', transform: `scale(${scale})`, transition: 'transform 0.12s ease' }}
    >
      <defs>
        {isWhite ? (
          <>
            <linearGradient id={`${pfx}-side`} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%"   stopColor="#9a9a9a"/>
              <stop offset="15%"  stopColor="#c8c8c8"/>
              <stop offset="35%"  stopColor="#ececec"/>
              <stop offset="60%"  stopColor="#fafafa"/>
              <stop offset="100%" stopColor="#ffffff"/>
            </linearGradient>
            <linearGradient id={`${pfx}-top`} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%"   stopColor="#f5f5f5"/>
              <stop offset="100%" stopColor="#ffffff"/>
            </linearGradient>
            <radialGradient id={`${pfx}-shd`} cx="50%" cy="50%" r="50%">
              <stop offset="0%"   stopColor="#000000" stopOpacity="0.2"/>
              <stop offset="100%" stopColor="#000000" stopOpacity="0"/>
            </radialGradient>
          </>
        ) : (
          <>
            <linearGradient id={`${pfx}-side`} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%"   stopColor="#000000"/>
              <stop offset="45%"  stopColor="#2a2a2a"/>
              <stop offset="78%"  stopColor="#6a6a6a"/>
              <stop offset="92%"  stopColor="#a8a8a8"/>
              <stop offset="98%"  stopColor="#c8c8c8"/>
              <stop offset="100%" stopColor="#5a5a5a"/>
            </linearGradient>
            <linearGradient id={`${pfx}-top`} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%"   stopColor="#1a1a1a"/>
              <stop offset="100%" stopColor="#2a2a2a"/>
            </linearGradient>
            <radialGradient id={`${pfx}-shd`} cx="50%" cy="50%" r="50%">
              <stop offset="0%"   stopColor="#000000" stopOpacity="0.3"/>
              <stop offset="100%" stopColor="#000000" stopOpacity="0"/>
            </radialGradient>
          </>
        )}
        {isKing && (
          <radialGradient id={`${pfx}-gold`} cx="40%" cy="35%" r="65%">
            <stop offset="0%"   stopColor="#fff4b8"/>
            <stop offset="50%"  stopColor="#e8c547"/>
            <stop offset="100%" stopColor="#a87f1a"/>
          </radialGradient>
        )}
      </defs>

      {isKing ? (
        <>
          {/* Ombre portée */}
          <ellipse cx="90" cy="180" rx="75" ry={isWhite ? 6 : 7} fill={`url(#${pfx}-shd)`}/>

          {/* Pion du bas : tranche */}
          <path
            d="M 20,115 A 80,40 0 0,0 180,115 L 180,150 A 80,40 0 0,1 20,150 Z"
            fill={`url(#${pfx}-side)`}
            stroke={isWhite ? '#a0a0a0' : '#000000'}
            strokeWidth="1.5"
          />
          {/* Pion du bas : dessus */}
          <ellipse cx="100" cy="115" rx="80" ry="40"
            fill={`url(#${pfx}-top)`}
            stroke={isWhite ? '#a8a8a8' : '#000000'}
            strokeWidth="1.5"
          />

          {/* Pion du haut : tranche */}
          <path
            d="M 20,75 A 80,40 0 0,0 180,75 L 180,110 A 80,40 0 0,1 20,110 Z"
            fill={`url(#${pfx}-side)`}
            stroke={isWhite ? '#a0a0a0' : '#000000'}
            strokeWidth="1.5"
          />
          {/* Pion du haut : dessus */}
          <ellipse cx="100" cy="75" rx="80" ry="40"
            fill={`url(#${pfx}-top)`}
            stroke={isWhite ? '#a8a8a8' : '#000000'}
            strokeWidth="1.5"
          />

          {/* Anneau sélection */}
          {selected && (
            <ellipse cx="100" cy="75" rx="80" ry="40"
              fill="none" stroke="#D4A017" strokeWidth="8"/>
          )}
          {/* Anneau jouable */}
          {!selected && moveable && (
            <ellipse cx="100" cy="75" rx="80" ry="40"
              fill="none"
              stroke={isWhite ? 'rgba(80,80,80,0.35)' : 'rgba(212,160,23,0.35)'}
              strokeWidth="4"
            />
          )}

          {/* Médaillon doré */}
          <ellipse cx="100" cy="73" rx="22" ry="11"
            fill={`url(#${pfx}-gold)`}
            stroke="#7a5a10"
            strokeWidth="1"
          />
        </>
      ) : (
        <>
          {/* Ombre portée */}
          <ellipse cx="90" cy="170" rx="75" ry={isWhite ? 6 : 7} fill={`url(#${pfx}-shd)`}/>

          {/* Tranche */}
          <path
            d="M 20,90 A 80,40 0 0,0 180,90 L 180,130 A 80,40 0 0,1 20,130 Z"
            fill={`url(#${pfx}-side)`}
            stroke={isWhite ? '#a0a0a0' : '#000000'}
            strokeWidth="1.5"
          />

          {/* Face du dessus */}
          <ellipse cx="100" cy="90" rx="80" ry="40"
            fill={`url(#${pfx}-top)`}
            stroke={isWhite ? '#a8a8a8' : '#000000'}
            strokeWidth="1.5"
          />

          {/* Anneau sélection */}
          {selected && (
            <ellipse cx="100" cy="90" rx="80" ry="40"
              fill="none" stroke="#D4A017" strokeWidth="8"/>
          )}
          {/* Anneau jouable */}
          {!selected && moveable && (
            <ellipse cx="100" cy="90" rx="80" ry="40"
              fill="none"
              stroke={isWhite ? 'rgba(80,80,80,0.35)' : 'rgba(212,160,23,0.35)'}
              strokeWidth="4"
            />
          )}
        </>
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
  warningSquares = [],
  flagSquares,
  spokenSquares = [],
  arrows = [],
  freeSelectSquares,
  flipped = false,
  theme = 'classic',
}: BoardProps) {
  const th = THEMES[theme]
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
  const [animCaptureSq, setAnimCaptureSq] = useState<Set<number>>(new Set())
  const prevLastMoveRef               = useRef<MoveData | null | undefined>(undefined)
  const animTimerRef                  = useRef<ReturnType<typeof setTimeout> | null>(null)
  const segTimersRef                  = useRef<ReturnType<typeof setTimeout>[]>([])

  // useLayoutEffect fires synchronously before the browser paints.
  // This prevents the one-frame flash where the piece appears at the destination
  // before being hidden — which caused the "B→A→B" reversal on white moves.
  // For multi-capture paths, each segment is animated sequentially.
  useLayoutEffect(() => {
    if (lastMove === prevLastMoveRef.current) return
    prevLastMoveRef.current = lastMove
    if (!lastMove) { setAnimVisible(false); setAnimCaptureSq(new Set()); return }

    const path = lastMove.path
    if (path.length < 2) { setAnimVisible(false); setAnimCaptureSq(new Set()); return }

    const to    = path[path.length - 1]
    const piece = board[to]
    if (piece === EMPTY) { setAnimVisible(false); setAnimCaptureSq(new Set()); return }

    const nSegments = path.length - 1
    const segMs     = nSegments === 1 ? 280 : 180

    if (animTimerRef.current) clearTimeout(animTimerRef.current)
    segTimersRef.current.forEach(t => clearTimeout(t))
    segTimersRef.current = []

    // Pre-compute all positions using current sqCenter (captures current flipped)
    const positions = path.map(sq => sqCenter(sq))

    // Show all captured pieces as ghosts; they'll vanish as the overlay passes over them
    setAnimCaptureSq(new Set(lastMove.captures))

    // Place overlay at source with no transition (synchronously, before paint)
    setAnimPiece(piece)
    setAnimX(positions[0].x)
    setAnimY(positions[0].y)
    setAnimHideSq(to)
    setAnimMoving(false)
    setAnimVisible(true)

    // Two rAFs ensure the browser paints the initial position before transitioning
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        // Start first segment immediately
        setAnimX(positions[1].x)
        setAnimY(positions[1].y)
        setAnimMoving(true)

        // Schedule each subsequent segment after the previous one completes
        for (let i = 2; i < path.length; i++) {
          const pos = positions[i]
          const t = setTimeout(() => {
            setAnimX(pos.x)
            setAnimY(pos.y)
          }, (i - 1) * segMs)
          segTimersRef.current.push(t)
        }

        // Remove each captured piece as the overlay crosses it (midpoint of its segment)
        for (let i = 0; i < nSegments; i++) {
          const cap = captureBetween(path[i], path[i + 1], lastMove.captures)
          if (cap !== null) {
            const t = setTimeout(() => {
              setAnimCaptureSq(prev => {
                const next = new Set(prev)
                next.delete(cap)
                return next
              })
            }, Math.round((i + 0.5) * segMs))
            segTimersRef.current.push(t)
          }
        }

        animTimerRef.current = setTimeout(() => {
          setAnimVisible(false)
          setAnimHideSq(null)
          setAnimCaptureSq(new Set())
        }, nSegments * segMs + 80)
      })
    })
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

  // Pre-compute the four flag sets so the inner loop just does a
  // Set.has() per category. Keep the FLAGS table in the same order as
  // the legend rendered by callers so colours stay in sync.
  const flagIso = new Set(flagSquares?.isolated ?? [])
  const flagRet = new Set(flagSquares?.backward ?? [])
  const flagTro = new Set(flagSquares?.holes    ?? [])
  const flagPos = new Set(flagSquares?.outposts ?? [])

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
      const isLastMove    = sq !== null && lastMovePath.has(sq) && !animVisible
      const isHighlighted = sq !== null && highlightSquares.includes(sq)
      const isWarning     = sq !== null && warningSquares.includes(sq)
      const isSpoken      = sq !== null && spokenSquares.includes(sq)

      // Square background color
      let bg = isDark ? th.dark : th.light
      if (isDark) {
        if (isSelected)         bg = th.selectedBg
        else if (isLastMove)    bg = th.lastMoveBg
        else if (isHighlighted) bg = th.highlightBg
      }

      cells.push(
        <div
          key={`${r}-${c}`}
          onClick={() => sq !== null && isDark && handleCellClick(sq)}
          className={isSpoken ? 'spoken-square' : undefined}
          style={{
            background: bg,
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

          {/* Ghost captured piece — visible until overlay crosses it */}
          {isDark && sq !== null && animVisible && animCaptureSq.has(sq) && (
            <PieceDisc
              piece={(animPiece === WHITE_MAN || animPiece === WHITE_KING) ? BLACK_MAN : WHITE_MAN}
              moveable={false}
              selected={false}
            />
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
              border: '3px solid rgba(186,220,255,0.55)',
              pointerEvents: 'none',
            }} />
          )}

          {/* Geometric-weakness flags — small corner dots, one corner
              per category. Stackable: a square can show up to 4. */}
          {isDark && sq !== null && flagIso.has(sq) && (
            <div style={{
              position: 'absolute', top: 2, left: 2,
              width: 7, height: 7, borderRadius: '50%',
              background: '#06b6d4', boxShadow: '0 0 2px rgba(0,0,0,0.5)',
              pointerEvents: 'none',
            }} title="Pion isolé" />
          )}
          {isDark && sq !== null && flagRet.has(sq) && (
            <div style={{
              position: 'absolute', top: 2, left: 13,
              width: 7, height: 7, borderRadius: '50%',
              background: '#f59e0b', boxShadow: '0 0 2px rgba(0,0,0,0.5)',
              pointerEvents: 'none',
            }} title="Pion retardé" />
          )}
          {isDark && sq !== null && flagTro.has(sq) && (
            <div style={{
              position: 'absolute', bottom: 2, left: 2,
              width: 7, height: 7, borderRadius: '50%',
              background: '#a855f7', boxShadow: '0 0 2px rgba(0,0,0,0.5)',
              pointerEvents: 'none',
            }} title="Trou" />
          )}
          {isDark && sq !== null && flagPos.has(sq) && (
            <div style={{
              position: 'absolute', bottom: 2, left: 13,
              width: 7, height: 7, borderRadius: '50%',
              background: '#22c55e', boxShadow: '0 0 2px rgba(0,0,0,0.5)',
              pointerEvents: 'none',
            }} title="Poste" />
          )}

          {/* Warning ring — piece is hanging / capturable next turn */}
          {isDark && sq !== null && isWarning && piece !== EMPTY && !isLegalTarget && (
            <div style={{
              position: 'absolute',
              inset: 0,
              border: '3px solid rgba(239,68,68,0.85)',
              pointerEvents: 'none',
              boxShadow: 'inset 0 0 10px rgba(239,68,68,0.45)',
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
      border: `3px solid ${th.border}`,
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
              ? `left ${(lastMove?.path.length ?? 2) > 2 ? 180 : 280}ms cubic-bezier(0.25,0,0.35,1), top ${(lastMove?.path.length ?? 2) > 2 ? 180 : 280}ms cubic-bezier(0.25,0,0.35,1)`
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
          {arrows.map((arrow, i) => {
            const f = sqCenter(arrow.from)
            const t = sqCenter(arrow.to)
            const dx = t.x - f.x
            const dy = t.y - f.y
            const len = Math.sqrt(dx * dx + dy * dy)
            if (len < 1) return null

            const angleDeg = Math.atan2(dy, dx) * 180 / Math.PI
            const scale     = (arrow.width ?? 2.2) / 2.2

            // Arrow path pointing rightward from origin: shaft + chevron head
            const start    = 2.5              // gap from source center
            const headLen  = 4.0 * scale
            const headHalf = 3.2 * scale
            const shaftH   = 1.1 * scale
            const xh       = len - headLen

            const d = [
              `M ${start} ${-shaftH}`,
              `L ${xh}    ${-shaftH}`,
              `L ${xh}    ${-headHalf}`,
              `L ${len}   0`,
              `L ${xh}    ${headHalf}`,
              `L ${xh}    ${shaftH}`,
              `L ${start} ${shaftH}`,
              'Z',
            ].join(' ')

            const color   = arrow.color   ?? '#9CA3AF'
            const opacity = arrow.opacity ?? 0.85

            return (
              <path
                key={i}
                d={d}
                fill={color}
                stroke="rgba(0,0,0,0.28)"
                strokeWidth={0.5}
                strokeLinejoin="round"
                opacity={opacity}
                transform={`translate(${f.x},${f.y}) rotate(${angleDeg})`}
              />
            )
          })}
        </svg>
      )}
    </div>
  )
}
