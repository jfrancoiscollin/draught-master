import React, { useState, useCallback, useEffect } from 'react'
import Board from './components/Board'
import AnalysisPanel from './components/AnalysisPanel'
import GameControls from './components/GameControls'
import MoveList from './components/MoveList'
import ExercisePanel from './components/ExercisePanel'
import GameHistory from './components/GameHistory'
import Toast from './components/Toast'
import LanguageSelector from './components/LanguageSelector'
import BottomSheet from './components/BottomSheet'
import {
  newGame,
  getLegalMoves,
  makeMove,
  analyzePosition,
  checkExercise,
} from './api/client'
import {
  EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING,
} from './types'
import type {
  GameStateResponse,
  MoveData,
  AnalysisResponse,
  ExerciseCheckResponse,
  GameDetailResponse,
} from './types'
import { useLanguage } from './i18n/LanguageContext'

function applyMoveLocally(board: number[], move: MoveData): number[] {
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

function fenToBoard(fen: string): number[] {
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

type Tab = 'play' | 'exercises' | 'history'

const TAB_ICONS: Record<Tab, string> = {
  play: '♟',
  exercises: '✏️',
  history: '📋',
}

export default function App() {
  const { t, language } = useLanguage()
  const [tab, setTab] = useState<Tab>('play')

  const [gameState, setGameState] = useState<GameStateResponse | null>(null)
  const [selectedSquare, setSelectedSquare] = useState<number | null>(null)
  const [legalMoves, setLegalMoves] = useState<MoveData[]>([])
  const [moveHistory, setMoveHistory] = useState<MoveData[]>([])
  const [aiDepth, setAiDepth] = useState(6)
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [toastMsg, setToastMsg] = useState<string | null>(null)
  const [isAiThinking, setIsAiThinking] = useState(false)
  const [spokenSquares, setSpokenSquares] = useState<number[]>([])
  const [showControls, setShowControls] = useState(false)

  const [exerciseGameState, setExerciseGameState] = useState<{
    board: number[]
    fen: string
    exerciseId: number | null
  } | null>(null)

  const [replayBoard, setReplayBoard] = useState<number[] | null>(null)
  const [replayFenIndex, setReplayFenIndex] = useState(0)
  const [replayDetail, setReplayDetail] = useState<GameDetailResponse | null>(null)

  const showToast = (msg: string) => setToastMsg(msg)

  const startNewGame = useCallback(async () => {
    try {
      setIsAiThinking(true)
      const state = await newGame({ white_player: 'Joueur', black_player: 'IA', ai_depth: aiDepth })
      setGameState(state)
      setSelectedSquare(null)
      setLegalMoves([])
      setMoveHistory([])
      setAnalysis(null)
    } catch {
      showToast(t('errorCreatingGame'))
    } finally {
      setIsAiThinking(false)
    }
  }, [aiDepth, t])

  useEffect(() => { startNewGame() }, [])

  useEffect(() => {
    if (!gameState?.game_id || gameState.result || gameState.turn !== 'white') {
      setLegalMoves([])
      return
    }
    getLegalMoves(gameState.game_id)
      .then(data => setLegalMoves(data.moves))
      .catch(() => setLegalMoves([]))
  }, [gameState?.game_id, gameState?.turn, gameState?.move_count])

  const handleSelectSquare = useCallback((sq: number | null) => {
    if (!gameState || gameState.result) return
    if (gameState.turn !== 'white') return
    setSelectedSquare(sq)
  }, [gameState])

  const handleMove = useCallback(async (move: MoveData) => {
    if (!gameState || gameState.result || isAiThinking) return
    setSelectedSquare(null)
    setLegalMoves([])
    setIsAiThinking(true)

    // Optimistic update: show player's move immediately, no waiting for server
    const optimisticBoard = applyMoveLocally(gameState.board, move)
    setGameState(prev => prev ? { ...prev, board: optimisticBoard, turn: 'black', last_move: move } : prev)

    try {
      const response = await makeMove(gameState.game_id, move, aiDepth)
      setGameState({
        game_id: response.game_id,
        board: response.board,
        turn: response.turn,
        half_move_clock: response.half_move_clock,
        move_count: response.move_count,
        result: response.result,
        fen: response.fen,
        last_move: response.ai_move || response.player_move,
      })
      setMoveHistory(prev => {
        const updated = [...prev, response.player_move]
        if (response.ai_move) updated.push(response.ai_move)
        return updated
      })
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      showToast(err?.response?.data?.detail || 'Coup illégal ou erreur serveur.')
      // Revert to original state on error
      setGameState(prev => prev ? { ...prev, board: gameState.board, turn: 'white', last_move: gameState.last_move } : prev)
    } finally {
      setIsAiThinking(false)
    }
  }, [gameState, aiDepth, isAiThinking])

  const handleAnalyze = useCallback(async (question?: string): Promise<AnalysisResponse | null> => {
    if (!gameState) return null
    setAnalysisLoading(true)
    try {
      const result = await analyzePosition(gameState.game_id, question, language)
      setAnalysis(result)
      return result
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      showToast(`${t('errorAnalysis')}${err?.response?.data?.detail || 'Erreur inconnue'}`)
      return null
    } finally {
      setAnalysisLoading(false)
    }
  }, [gameState, language, t])

  const handleExerciseLoad = useCallback((fen: string, exerciseId: number) => {
    setExerciseGameState({ board: fenToBoard(fen), fen, exerciseId })
  }, [])

  const handleExerciseMoveSubmit = useCallback(async (moves: string[]): Promise<ExerciseCheckResponse | null> => {
    if (!exerciseGameState?.exerciseId) return null
    try {
      return await checkExercise(exerciseGameState.exerciseId, moves)
    } catch {
      showToast(t('errorVerification'))
      return null
    }
  }, [exerciseGameState, t])

  const handleReplay = useCallback((detail: GameDetailResponse) => {
    setReplayDetail(detail)
    setReplayFenIndex(0)
    if (detail.fen_positions.length > 0) setReplayBoard(fenToBoard(detail.fen_positions[0]))
  }, [])

  const replayStep = (delta: number) => {
    if (!replayDetail) return
    const newIdx = Math.max(0, Math.min(replayDetail.fen_positions.length - 1, replayFenIndex + delta))
    setReplayFenIndex(newIdx)
    setReplayBoard(fenToBoard(replayDetail.fen_positions[newIdx]))
  }

  const getResultLabel = (result: string | null) => {
    if (result === 'white') return t('resultWhiteWins')
    if (result === 'black') return t('resultBlackWins')
    if (result === 'draw') return t('resultDraw')
    return ''
  }

  const currentBoard = gameState?.board || new Array(51).fill(EMPTY)
  const isWhiteTurn = gameState?.turn === 'white'
  const boardDisabled = !gameState || !!gameState.result || !isWhiteTurn || isAiThinking

  const tabs: [Tab, string][] = [
    ['play', t('tabPlay')],
    ['exercises', t('tabExercises')],
    ['history', t('tabHistory')],
  ]

  return (
    <div className="bg-gray-900 text-gray-100 flex flex-col h-full">
      {toastMsg && <Toast message={toastMsg} onClose={() => setToastMsg(null)} />}

      {/* Header — compact on mobile */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex-shrink-0">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-green-400">♟ AI-Draught</h1>
            {isAiThinking && (
              <span className="flex items-center gap-1 text-yellow-400 text-xs">
                <div className="spinner" style={{ width: 12, height: 12 }} />
                <span className="hidden sm:inline">{t('aiThinking')}</span>
              </span>
            )}
            {!isAiThinking && gameState?.result && (
              <span className="text-yellow-300 font-semibold text-sm">
                {getResultLabel(gameState.result)}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <LanguageSelector />
            <button
              onClick={() => setShowControls(true)}
              className="lg:hidden text-gray-400 hover:text-white text-xl w-10 h-10 flex items-center justify-center rounded-lg hover:bg-gray-700"
              title={t('controls')}
            >
              ⚙️
            </button>
          </div>
        </div>
      </header>

      {/* Top tabs — desktop only */}
      <div className="hidden lg:block bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 flex gap-0">
          {tabs.map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`tab-btn ${tab === key ? 'tab-active' : 'tab-inactive'}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Main content — overflow:hidden on mobile so only panels scroll, not the page */}
      <main className="flex-1 overflow-hidden lg:overflow-y-auto">

        {/* PLAY TAB */}
        {tab === 'play' && (
          <div className="h-full flex flex-col lg:h-auto lg:flex-row lg:gap-6 lg:max-w-7xl lg:mx-auto lg:px-4 lg:py-4">

            {/* Board — never scrolls, stays locked at top on mobile */}
            <div className="flex-shrink-0 flex flex-col items-center px-2 pt-2 lg:px-0 lg:pt-0">
              <Board
                board={currentBoard}
                legalMoves={legalMoves}
                onMove={handleMove}
                selectedSquare={selectedSquare}
                onSelectSquare={handleSelectSquare}
                disabled={boardDisabled}
                lastMove={gameState?.last_move}
                spokenSquares={spokenSquares}
              />
              {gameState && (
                <p className="mt-1 text-xs text-gray-500 self-start">{t('whitePerspective')}</p>
              )}
            </div>

            {/* Panels — scrollable zone on mobile */}
            <div className="flex-1 overflow-y-auto overscroll-contain pb-20 lg:pb-4 min-w-0">
              <div className="flex flex-col gap-3 px-2 py-3 lg:px-0">
                <AnalysisPanel
                  gameId={gameState?.game_id || null}
                  onAnalyze={handleAnalyze}
                  analysis={analysis}
                  loading={analysisLoading}
                  onHighlightSquare={setSpokenSquares}
                />
                {/* Controls: desktop inline, mobile via bottom sheet */}
                <div className="hidden lg:block">
                  <GameControls
                    result={gameState?.result || null}
                    turn={gameState?.turn || 'white'}
                    moveCount={gameState?.move_count || 0}
                    aiDepth={aiDepth}
                    onNewGame={startNewGame}
                    onAiDepthChange={setAiDepth}
                    disabled={isAiThinking}
                  />
                </div>
                <MoveList
                  moves={moveHistory}
                  currentMoveIndex={moveHistory.length - 1}
                />
              </div>
            </div>
          </div>
        )}

        {/* EXERCISES TAB */}
        {tab === 'exercises' && (
          <div className="h-full flex flex-col lg:h-auto lg:flex-row lg:gap-6 lg:max-w-7xl lg:mx-auto lg:px-4 lg:py-4">
            <div className="flex-shrink-0 flex flex-col items-center px-2 pt-2 lg:px-0 lg:pt-0">
              <Board
                board={exerciseGameState?.board || new Array(51).fill(EMPTY)}
                legalMoves={[]}
                onMove={() => {}}
                selectedSquare={null}
                onSelectSquare={() => {}}
                disabled={true}
              />
              <p className="mt-1 text-xs text-gray-500">{t('exerciseReadOnly')}</p>
            </div>
            <div className="flex-1 overflow-y-auto overscroll-contain pb-20 lg:pb-4 min-w-0">
              <div className="px-2 py-3 lg:px-0">
                <ExercisePanel
                  onExerciseLoad={handleExerciseLoad}
                  currentExerciseId={exerciseGameState?.exerciseId || null}
                  onMoveSubmit={handleExerciseMoveSubmit}
                />
              </div>
            </div>
          </div>
        )}

        {/* HISTORY TAB */}
        {tab === 'history' && (
          <div className="h-full flex flex-col lg:h-auto lg:flex-row lg:gap-6 lg:max-w-7xl lg:mx-auto lg:px-4 lg:py-4">
            <div className="flex-shrink-0 flex flex-col items-center px-2 pt-2 lg:px-0 lg:pt-0">
              {replayBoard ? (
                <>
                  <Board
                    board={replayBoard}
                    legalMoves={[]}
                    onMove={() => {}}
                    selectedSquare={null}
                    onSelectSquare={() => {}}
                    disabled={true}
                  />
                  {replayDetail && (
                    <div className="mt-2 flex items-center gap-3 w-full">
                      <button onClick={() => replayStep(-1)} disabled={replayFenIndex === 0} className="btn-secondary text-sm flex-1">
                        {t('previous')}
                      </button>
                      <span className="text-gray-400 text-sm whitespace-nowrap">
                        {replayFenIndex + 1} / {replayDetail.fen_positions.length}
                      </span>
                      <button onClick={() => replayStep(1)} disabled={replayFenIndex >= replayDetail.fen_positions.length - 1} className="btn-secondary text-sm flex-1">
                        {t('next')}
                      </button>
                    </div>
                  )}
                </>
              ) : (
                <div className="w-full aspect-square max-w-sm flex items-center justify-center bg-gray-800 rounded-lg border border-dashed border-gray-700">
                  <p className="text-gray-600 text-sm text-center px-4">{t('selectGame')}</p>
                </div>
              )}
            </div>
            <div className="flex-1 overflow-y-auto overscroll-contain pb-20 lg:pb-4 min-w-0">
              <div className="px-2 py-3 lg:px-0">
                <GameHistory onReplay={handleReplay} />
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Controls bottom sheet — mobile only */}
      <BottomSheet
        open={showControls}
        onClose={() => setShowControls(false)}
        title={t('controls')}
      >
        <GameControls
          result={gameState?.result || null}
          turn={gameState?.turn || 'white'}
          moveCount={gameState?.move_count || 0}
          aiDepth={aiDepth}
          onNewGame={() => { startNewGame(); setShowControls(false) }}
          onAiDepthChange={setAiDepth}
          disabled={isAiThinking}
        />
      </BottomSheet>

      {/* Bottom navigation — mobile only */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-gray-800 border-t border-gray-700 z-40">
        <div className="flex">
          {tabs.map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex-1 flex flex-col items-center justify-center py-3 gap-0.5 transition-colors ${
                tab === key ? 'text-green-400' : 'text-gray-400 active:text-gray-200'
              }`}
            >
              <span className="text-xl leading-none">{TAB_ICONS[key]}</span>
              <span className="text-xs font-medium">{label}</span>
              {tab === key && (
                <span className="absolute bottom-0 w-1/3 h-0.5 bg-green-400 rounded-t" />
              )}
            </button>
          ))}
        </div>
      </nav>
    </div>
  )
}
