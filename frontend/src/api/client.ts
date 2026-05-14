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
  book_id?: string
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

export async function resignGame(gameId: string, userSide: 'white' | 'black'): Promise<{ result: string }> {
  const res = await api.post<{ result: string }>(`/game/${gameId}/resign`, { user_side: userSide })
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

export async function getLessonTitles(book?: string): Promise<Record<string, { title: string; category: string }>> {
  const res = await api.get('/lessons', { params: book ? { book } : undefined })
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

export interface UserStats {
  total_games: number
  total_moves: number
  blunders: number
  mistakes: number
  inaccuracies: number
  accuracy_pct: number
  recent_games: Array<{
    id: string
    date: string
    white_player: string
    black_player: string
    result: string | null
    move_count: number
    blunders: number
    mistakes: number
    inaccuracies: number
  }>
}

export async function getUserStats(): Promise<UserStats> {
  const res = await api.get<UserStats>('/auth/me/stats')
  return res.data
}

export async function saveGameAnnotations(
  gameId: string,
  annotations: Array<{ move_number: number; color?: string; classification?: string; comment?: string }>,
): Promise<void> {
  await api.post(`/history/${gameId}/annotations`, { annotations })
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

export async function startReeval(msPerPosition: number): Promise<{ started: boolean; message: string; pending?: number }> {
  const res = await api.post('/opening-book/reeval', { ms_per_position: msPerPosition }, { timeout: 10000 })
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

// ── Exercise verification ─────────────────────────────────────────────────────

export interface ExerciseIssue {
  name: string
  fen: string
  stored_move: string
  status: 'ILLEGAL' | 'SCAN_MISMATCH'
  reason: string
  legal_moves: string[]
  scan_move: string | null
  heuristic_fix: boolean
}

export interface ExerciseResult {
  name: string
  fen: string
  stored_move: string
  scan_move: string | null
  status: 'OK' | 'ILLEGAL' | 'SCAN_MISMATCH'
  heuristic_fix: boolean
}

export interface ExerciseVerificationStatus {
  status: 'idle' | 'running' | 'done'
  total: number
  done: number
  ok: number
  illegal: number
  scan_mismatch: number
  heuristic_count: number
  issues: ExerciseIssue[]
  all_results: ExerciseResult[]
  scan_available: boolean
  error: string | null
}

export async function startExerciseVerification(
  useScan = false,
  movetime = 0.3,
  dataset: 'all' | 'initial' | 'sens_du_jeu' = 'all',
): Promise<{ started: boolean }> {
  const res = await api.post('/admin/verify-exercises', { use_scan: useScan, movetime, dataset })
  return res.data
}

export async function getExerciseVerificationStatus(): Promise<ExerciseVerificationStatus> {
  const res = await api.get('/admin/verify-exercises/status')
  return res.data
}

// ---------------------------------------------------------------------------
// Pedagogy (dilf) API
// ---------------------------------------------------------------------------

export interface MotifOut {
  motif: string
  role: string
  squares: number[]
  pv: string[]
  severity: number
}

export interface VerdictOut {
  move_number: number
  side: 'white' | 'black'
  move_notation: string
  fen_before: string
  fen_after: string
  score_before: number
  score_after: number
  delta_winchance: number
  verdict: 'brilliant' | 'best' | 'excellent' | 'good' | 'inaccuracy' | 'mistake' | 'blunder' | 'forced' | 'book'
  is_forced: boolean
  phase: 'opening' | 'middlegame' | 'endgame'
  motifs: MotifOut[]
}

export interface PedagogyAnalysis {
  game_id: string
  verdicts: VerdictOut[]
  summary: {
    total_half_moves: number
    blunders: number
    mistakes: number
    average_accuracy: number
    user_side: string
  }
}

export async function analyzeGamePedagogy(
  gameId: string,
  userSide: 'white' | 'black',
  lang: string = 'fr',
): Promise<PedagogyAnalysis> {
  const res = await api.post<PedagogyAnalysis>(
    '/pedagogy/analyze-game',
    { game_id: gameId, user_side: userSide, lang },
    { timeout: 90000 },
  )
  return res.data
}

export async function explainMovePedagogy(
  gameId: string,
  moveNumber: number,
  mode: 'template' | 'template+book' | 'claude' = 'template',
  lang: string = 'fr',
): Promise<string | null> {
  try {
    const res = await api.post<{ text: string; mode: string; lang: string; cached: boolean }>(
      '/pedagogy/explain-move',
      { game_id: gameId, move_number: moveNumber, mode, lang },
      { timeout: 15000 },
    )
    return res.data.text
  } catch {
    return null
  }
}
