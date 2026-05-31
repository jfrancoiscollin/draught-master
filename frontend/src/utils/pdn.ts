import { EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING, sqToRowCol, rcToSq } from '../types'
import type { MoveData } from '../api/client'

/**
 * Parse a PDN move string ("33-29" simple, "18x29" capture, "20x31x42"
 * multi-capture) into a ``MoveData`` against the current board state.
 *
 * Capture lookups walk the diagonal between consecutive hops and pick
 * the first occupied square — same logic the dilf engine uses.  Returns
 * ``null`` for malformed input (non-numeric or wrong separator count).
 */
export function pdnToMoveData(pdn: string, board: number[]): MoveData | null {
  if (pdn.includes('x')) {
    const path = pdn.split('x').map(Number)
    if (path.some(isNaN)) return null
    const captures: number[] = []
    for (let i = 0; i < path.length - 1; i++) {
      const [r1, c1] = sqToRowCol(path[i])
      const [r2, c2] = sqToRowCol(path[i + 1])
      const dr = Math.sign(r2 - r1)
      const dc = Math.sign(c2 - c1)
      let r = r1 + dr, c = c1 + dc
      while (r !== r2 || c !== c2) {
        const sq = rcToSq(r, c)
        if (sq !== null && board[sq] !== EMPTY) {
          captures.push(sq)
          break
        }
        r += dr
        c += dc
      }
    }
    return { path, captures }
  } else if (pdn.includes('-')) {
    const parts = pdn.split('-').map(Number)
    if (parts.length !== 2 || parts.some(isNaN)) return null
    return { path: parts, captures: [] }
  }
  return null
}

/**
 * Apply a single move to a board copy.  Handles promotion to king
 * on row 0 (white) and row 9 (black).
 */
export function applyMoveLocally(board: number[], move: MoveData): number[] {
  const newBoard = [...board]
  const piece = newBoard[move.path[0]]
  newBoard[move.path[0]] = EMPTY
  for (const cap of move.captures) newBoard[cap] = EMPTY
  const dest = move.path[move.path.length - 1]
  newBoard[dest] = piece
  if (piece === WHITE_MAN && dest <= 5) newBoard[dest] = WHITE_KING
  if (piece === BLACK_MAN && dest >= 46) newBoard[dest] = BLACK_KING
  return newBoard
}

/**
 * Replay a sequence of PDN strings starting from ``initialBoard``.
 * Stops at the first malformed token (returns the board reached so
 * far + the index that failed).  Used by the strategy lesson view
 * to surface the position after the operator's clicked move in the
 * passage prose.
 */
export function replayPdnSequence(
  initialBoard: number[],
  pdns: string[],
): { board: number[]; appliedUpTo: number } {
  let board = [...initialBoard]
  for (let i = 0; i < pdns.length; i++) {
    const md = pdnToMoveData(pdns[i], board)
    if (!md) return { board, appliedUpTo: i - 1 }
    board = applyMoveLocally(board, md)
  }
  return { board, appliedUpTo: pdns.length - 1 }
}

// Detects PDN move tokens like "33-29", "18x29", "20x31x42" in prose.
// Anchored on word boundaries to avoid matching parts of numbers or
// section markers ("1.", "2.", "4.").  The 1-2 digit / 1-2 digit
// constraint matches international draughts squares (1-50).
export const PDN_MOVE_RE = /\b\d{1,2}(?:[-x]\d{1,2})+\b/g
