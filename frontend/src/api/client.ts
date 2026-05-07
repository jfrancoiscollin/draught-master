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

export async function findPlayersByRating(
  ratingMin: number,
  ratingMax: number,
  count: number,
): Promise<{ players: { username: string; rating: number }[]; found: number }> {
  const res = await api.get('/opening-book/players', {
    params: { rating_min: ratingMin, rating_max: ratingMax, count },
  })
  return res.data
}

export async function startOpeningCacheBuild(params: {
  usernames?: string[]
  pdn_texts?: string[]
  max_games_per_user?: number
  max_moves?: number
  ms_per_position?: number
}): Promise<{ started: boolean; message: string }> {
  const res = await api.post('/opening-book/build', params, { timeout: 120000 })
  return res.data
}

export async function getOpeningCacheBuildStatus(): Promise<{
  status: string
  message: string
  fetched_games: number
  unique_positions: number
  computed: number
  skipped: number
  total_to_compute: number
  errors: number
  cache_size: number
}> {
  const res = await api.get('/opening-book/build/status')
  return res.data
}

export async function ingestPdn(raw: string, maxMoves: number): Promise<{ games: number; fens_added: number; format: string }> {
  const res = await api.post('/opening-book/ingest', { raw, max_moves: maxMoves }, { timeout: 30000 })
  return res.data
}

export async function startEval(msPerPosition: number): Promise<{ started: boolean; message: string }> {
  const res = await api.post('/opening-book/start-eval', { ms_per_position: msPerPosition }, { timeout: 10000 })
  return res.data
}

// Pre-compute deep evaluations for a game's positions and store them in the
// server-side opening eval cache. Subsequent annotation calls will use the cache.
export async function precomputePositions(
  positions: PdnPosition[],
): Promise<{ success: boolean; computed?: number; cache_size?: number; evaluations?: PositionEval[] }> {
  try {
    const res = await api.post(
      '/opening-book/precompute',
      { positions },
      { timeout: 600000 },
    )
    return res.data
  } catch {
    return { success: false }
  }
}

// Batch evaluation using the server's native Scan engine (fast, high depth).
// Returns null if the server doesn't have Scan installed.
export async function analyzePositionsBatch(
  positions: PdnPosition[],
  msPerMove: number = 200,
): Promise<{ evals: PositionEval[]; cacheHits: number } | null> {
  try {
    const res = await api.post<{ evaluations: PositionEval[] | null; available: boolean; cache_hits?: number }>(
      '/pdn/annotate',
      { positions, ms_per_move: msPerMove },
      { timeout: 300000 },
    )
    if (!res.data.available || !res.data.evaluations) return null
    return { evals: res.data.evaluations, cacheHits: res.data.cache_hits ?? 0 }
  } catch {
    return null
  }
}

export interface OpeningContinuation {
  move: string
  frequency: number
  pct: number
  score: number | null
}

export interface OpeningExplorerData {
  fen: string
  total_games: number
  continuations: OpeningContinuation[]
  engine_best: string | null
  engine_score: number
}

export async function getContinuations(fen: string): Promise<OpeningExplorerData | null> {
  try {
    const res = await api.get('/opening-book/continuations', { params: { fen } })
    return res.data as OpeningExplorerData
  } catch {
    return null
  }
}
