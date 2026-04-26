export const EMPTY = 0
export const WHITE_MAN = 1
export const WHITE_KING = 2
export const BLACK_MAN = 3
export const BLACK_KING = 4

export interface MoveData {
  path: number[]
  captures: number[]
}

export interface GameStateResponse {
  game_id: string
  board: number[]
  turn: 'white' | 'black'
  half_move_clock: number
  move_count: number
  result: string | null
  fen: string
  last_move: MoveData | null
  legal_moves: MoveData[]
}

export interface MoveResponse {
  game_id: string
  player_move: MoveData
  ai_move: MoveData | null
  board: number[]
  turn: 'white' | 'black'
  half_move_clock: number
  move_count: number
  result: string | null
  fen: string
  legal_moves: MoveData[]
}

export interface LegalMovesResponse {
  game_id: string
  from_square: number | null
  moves: MoveData[]
}

export interface ExerciseResponse {
  id: number
  name: string
  description: string | null
  initial_fen: string
  difficulty: number
  category: string
  hint: string | null
  solution_moves: string[]
  legal_moves?: MoveData[]
}

export interface ExerciseCheckResponse {
  correct: boolean
  message: string
  solution: string[] | null
  in_progress?: boolean
  auto_move?: string | null
}

export interface AnalysisResponse {
  analysis: string
  best_moves: string[]
  key_squares: number[]
  strategic_advice: string
}

export interface HistoryItem {
  id: string
  date: string
  white_player: string
  black_player: string
  result: string | null
  move_count: number
}

export interface HistoryResponse {
  games: HistoryItem[]
  total: number
  page: number
  page_size: number
}

export interface GameDetailResponse {
  id: string
  date: string
  white_player: string
  black_player: string
  result: string | null
  pdn: string
  fen_positions: string[]
  move_count: number
}

export function sqToRowCol(sq: number): [number, number] {
  const idx = sq - 1
  const row = Math.floor(idx / 5)
  const colInRow = idx % 5
  const col = colInRow * 2 + (row % 2 === 0 ? 1 : 0)
  return [row, col]
}

export function rcToSq(row: number, col: number): number | null {
  if (row < 0 || row > 9 || col < 0 || col > 9) return null
  if ((row + col) % 2 === 0) return null
  const colInRow = Math.floor(col / 2)
  const sq = row * 5 + colInRow + 1
  if (sq < 1 || sq > 50) return null
  return sq
}

export function resultLabel(result: string | null): string {
  if (result === 'white') return 'Blancs gagnent'
  if (result === 'black') return 'Noirs gagnent'
  if (result === 'draw') return 'Match nul'
  return ''
}
