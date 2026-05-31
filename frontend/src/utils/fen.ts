import { EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING } from '../types'

export function fenToBoard(fen: string): number[] {
  const board = new Array(51).fill(EMPTY)
  const parts = fen.split(':')
  for (const section of parts.slice(1)) {
    if (!section) continue
    const color = section[0]
    const tokens = section.slice(1).split(',')
    for (const token of tokens) {
      if (!token) continue
      const isKing = token.startsWith('K')
      const num = parseInt(isKing ? token.slice(1) : token, 10)
      if (isNaN(num) || num < 1 || num > 50) continue
      if (color === 'W') board[num] = isKing ? WHITE_KING : WHITE_MAN
      else board[num] = isKing ? BLACK_KING : BLACK_MAN
    }
  }
  return board
}

/**
 * Inverse of {@link fenToBoard}. Returns FMJD draughts FEN
 * (e.g. ``"W:W31,32,K42:B1,2,K3"``) from a 51-element board array.
 *
 * Index 0 is unused (cases are 1-50). Pieces are sorted ascending per
 * color, kings prefixed with ``K``. Used by the FEN annotator
 * (``FenAnnotator.tsx``) to materialise the edited position as a
 * one-line string the user can paste into ``diagrams_fens.json``.
 */
export function boardToFen(board: number[], turn: 'W' | 'B' = 'W'): string {
  const whites: string[] = []
  const blacks: string[] = []
  for (let sq = 1; sq <= 50; sq++) {
    const p = board[sq]
    if (p === WHITE_MAN) whites.push(String(sq))
    else if (p === WHITE_KING) whites.push(`K${sq}`)
    else if (p === BLACK_MAN) blacks.push(String(sq))
    else if (p === BLACK_KING) blacks.push(`K${sq}`)
  }
  return `${turn}:W${whites.join(',')}:B${blacks.join(',')}`
}

