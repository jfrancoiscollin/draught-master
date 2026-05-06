import axios from 'axios'
import type {
  GameStateResponse,
  MoveResponse,
  LegalMovesResponse,
  ExerciseResponse,
  ExerciseCheckResponse,
  AnalysisResponse,
  HistoryResponse,
  GameDetailResponse,
  MoveData,
} from '../types'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('auth_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export async function newGame(params: {
  white_player?: string
  black_player?: string
  ai_depth?: number
}): Promise<GameStateResponse> {
  const res = await api.post<GameStateResponse>('/game/new', params)
  return res.data
}

export async function getLegalMoves(
  gameId: string,
  fromSq?: number
): Promise<LegalMovesResponse> {
  const params = fromSq !== undefined ? { from_sq: fromSq } : {}
  const res = await api.get<LegalMovesResponse>(`/game/${gameId}/legal-moves`, { params })
  return res.data
}

export async function makeMove(
  gameId: string,
  move: MoveData,
  aiDepth: number = 6,
  bothSides: boolean = false
): Promise<MoveResponse> {
  const res = await api.post<MoveResponse>(`/game/${gameId}/move`, {
    path: move.path,
    captures: move.captures,
    ai_depth: aiDepth,
    both_sides: bothSides,
  })
  return res.data
}

export async function getAiMove(gameId: string, depth: number = 4): Promise<MoveData | null> {
  const res = await api.get<{ move: MoveData | null }>(`/game/${gameId}/ai-move`, {
    params: { depth },
  })
  return res.data.move
}

export async function analyzePosition(
  gameId: string,
  question?: string,
  language: string = 'fr',
  mode: string = 'position',
  aiDepth: number = 6,
): Promise<AnalysisResponse> {
  const res = await api.post<AnalysisResponse>(`/game/${gameId}/analyze`, {
    question: question || null,
    language,
    mode,
    ai_depth: aiDepth,
  }, { timeout: 90000 })
  return res.data
}

export async function getExercises(params?: {
  category?: string
  difficulty?: number
}): Promise<ExerciseResponse[]> {
  const res = await api.get<ExerciseResponse[]>('/exercises', { params })
  return res.data
}

export async function getExerciseCategories(): Promise<string[]> {
  const res = await api.get<string[]>('/exercises-categories')
  return res.data
}

export async function getExercise(id: number): Promise<ExerciseResponse> {
  const res = await api.get<ExerciseResponse>(`/exercises/${id}`)
  return res.data
}

export async function getExerciseLegalMoves(id: number): Promise<{ moves: MoveData[] }> {
  const res = await api.get<{ moves: MoveData[] }>(`/exercises/${id}/legal-moves`)
  return res.data
}

export async function getExerciseLegalMovesAtStep(id: number, step: number): Promise<{ moves: MoveData[] }> {
  const res = await api.get<{ moves: MoveData[] }>(`/exercises/${id}/legal-moves`, { params: { step } })
  return res.data
}

export async function checkExercise(
  id: number,
  moves: string[],
  step: number = 0
): Promise<ExerciseCheckResponse> {
  const res = await api.post<ExerciseCheckResponse>(`/exercises/${id}/check`, { moves, step })
  return res.data
}

export async function resignGame(gameId: string): Promise<{ result: string }> {
  const res = await api.post<{ result: string }>(`/game/${gameId}/resign`)
  return res.data
}

export async function undoMove(gameId: string): Promise<GameStateResponse> {
  const res = await api.post<GameStateResponse>(`/game/${gameId}/undo`)
  return res.data
}

export async function getHistory(page: number = 1, pageSize: number = 10): Promise<HistoryResponse> {
  const res = await api.get<HistoryResponse>('/history', {
    params: { page, page_size: pageSize },
  })
  return res.data
}

export async function getGameDetail(gameId: string): Promise<GameDetailResponse> {
  const res = await api.get<GameDetailResponse>(`/history/${gameId}`)
  return res.data
}

export async function getUserProgress(): Promise<number[]> {
  const res = await api.get<{ solved_exercise_ids: number[] }>('/auth/me/progress')
  return res.data.solved_exercise_ids
}

export async function getLessonTitles(): Promise<Record<string, { title: string; category: string }>> {
  const res = await api.get('/lessons')
  return res.data
}

export async function getLesson(chapter: number): Promise<{ title: string; text: string; category: string }> {
  const res = await api.get(`/lessons/${chapter}`)
  return res.data
}

export async function getReadLessons(): Promise<number[]> {
  const res = await api.get<{ read_chapters: number[] }>('/auth/me/lessons/read')
  return res.data.read_chapters
}

export async function markLessonRead(chapter: number): Promise<void> {
  await api.post(`/auth/me/lessons/${chapter}/read`)
}

export async function getPositionLegalMoves(fen: string): Promise<MoveData[]> {
  const res = await api.post<{ moves: MoveData[] }>('/position/legal-moves', { fen })
  return res.data.moves
}

export async function applyPositionMove(fen: string, path: number[]): Promise<{ fen: string; moves: MoveData[] }> {
  const res = await api.post<{ fen: string; moves: MoveData[] }>('/position/apply-move', { fen, path })
  return res.data
}

export interface PdnPosition {
  fen: string
  notation: string | null
  move_number: number
  color: string | null
}

export interface PdnImportResult {
  positions: PdnPosition[]
  metadata: Record<string, string>
  total_moves: number
}

export async function importPdn(pdn: string): Promise<PdnImportResult> {
  const res = await api.post<PdnImportResult>('/pdn/import', { pdn })
  return res.data
}

export async function analyzePositionFen(
  fen: string,
  question?: string,
  language: string = 'fr',
  mode: string = 'position',
  moveHistory?: string[],
): Promise<AnalysisResponse> {
  const res = await api.post<AnalysisResponse>(
    '/position/analyze',
    { fen, question: question || null, language, mode, move_history: moveHistory ?? [] },
    { timeout: 90000 },
  )
  return res.data
}

export async function getPositionBestMove(fen: string, depth: number = 6): Promise<string | null> {
  const res = await api.post<{ move: string | null }>('/position/best-move', { fen, depth })
  return res.data.move
}

export interface PositionEval {
  score: number
  bestMove: string | null
}

// Batch evaluation using the server's native Scan engine (fast, high depth).
// Returns null if the server doesn't have Scan installed.
export async function analyzePositionsBatch(
  positions: PdnPosition[],
  msPerMove: number = 200,
): Promise<PositionEval[] | null> {
  try {
    const res = await api.post<{ evaluations: PositionEval[] | null; available: boolean }>(
      '/pdn/annotate',
      { positions, ms_per_move: msPerMove },
      { timeout: 300000 },
    )
    if (!res.data.available || !res.data.evaluations) return null
    return res.data.evaluations
  } catch {
    return null
  }
}
