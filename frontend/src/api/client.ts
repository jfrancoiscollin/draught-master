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
  aiDepth: number = 6
): Promise<MoveResponse> {
  const res = await api.post<MoveResponse>(`/game/${gameId}/move`, {
    path: move.path,
    captures: move.captures,
    ai_depth: aiDepth,
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
  language: string = 'fr'
): Promise<AnalysisResponse> {
  const res = await api.post<AnalysisResponse>(`/game/${gameId}/analyze`, {
    question: question || null,
    language,
  })
  return res.data
}

export async function getExercises(params?: {
  category?: string
  difficulty?: number
}): Promise<ExerciseResponse[]> {
  const res = await api.get<ExerciseResponse[]>('/exercises', { params })
  return res.data
}

export async function getExercise(id: number): Promise<ExerciseResponse> {
  const res = await api.get<ExerciseResponse>(`/exercises/${id}`)
  return res.data
}

export async function checkExercise(
  id: number,
  moves: string[]
): Promise<ExerciseCheckResponse> {
  const res = await api.post<ExerciseCheckResponse>(`/exercises/${id}/check`, { moves })
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
