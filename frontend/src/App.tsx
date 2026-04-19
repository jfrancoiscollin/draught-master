import React, { useState, useCallback, useEffect } from 'react'
import Board from './components/Board'
import AnalysisPanel from './components/AnalysisPanel'
import GameControls from './components/GameControls'
import MoveList from './components/MoveList'
import ExercisePanel from './components/ExercisePanel'
import GameHistory from './components/GameHistory'
import Toast from './components/Toast'
import {
  newGame,
  getLegalMoves,
  makeMove,
  analyzePosition,
  checkExercise,
} from './api/client'
import {
  EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING,
  sqToRowCol, resultLabel,
} from './types'
import type {
  GameStateResponse,
  MoveData,
  LegalMovesResponse,
  AnalysisResponse,
  ExerciseCheckResponse,
  GameDetailResponse,
} from './types'

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

export default function App() {
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
    } catch (e) {
      showToast('Erreur lors de la création de la partie.')
    } finally {
      setIsAiThinking(false)
    }
  }, [aiDepth])

  useEffect(() => {
    startNewGame()
  }, [])

  // Pre-fetch all legal moves whenever it becomes white's turn
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

    try {
      const response = await makeMove(gameState.game_id, move, aiDepth)
      const newState: GameStateResponse = {
        game_id: response.game_id,
        board: response.board,
        turn: response.turn,
        half_move_clock: response.half_move_clock,
        move_count: response.move_count,
        result: response.result,
        fen: response.fen,
        last_move: response.ai_move || response.player_move,
      }
      setGameState(newState)
      setMoveHistory(prev => {
        const updated = [...prev, response.player_move]
        if (response.ai_move) updated.push(response.ai_move)
        return updated
      })
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      showToast(err?.response?.data?.detail || 'Coup illégal ou erreur serveur.')
    } finally {
      setIsAiThinking(false)
    }
  }, [gameState, aiDepth, isAiThinking])

  const handleAnalyze = useCallback(async (question?: string): Promise<AnalysisResponse | null> => {
    if (!gameState) return null
    setAnalysisLoading(true)
    try {
      const result = await analyzePosition(gameState.game_id, question)
      setAnalysis(result)
      return result
    } catch {
      showToast("Erreur lors de l'analyse. Vérifiez votre clé API Anthropic.")
      return null
    } finally {
      setAnalysisLoading(false)
    }
  }, [gameState])

  const handleExerciseLoad = useCallback((fen: string, exerciseId: number) => {
    const board = fenToBoard(fen)
    setExerciseGameState({ board, fen, exerciseId })
  }, [])

  const handleExerciseMoveSubmit = useCallback(async (moves: string[]): Promise<ExerciseCheckResponse | null> => {
    if (!exerciseGameState?.exerciseId) return null
    try {
      return await checkExercise(exerciseGameState.exerciseId, moves)
    } catch {
      showToast("Erreur lors de la vérification.")
      return null
    }
  }, [exerciseGameState])

  const handleReplay = useCallback((detail: GameDetailResponse) => {
    setReplayDetail(detail)
    setReplayFenIndex(0)
    if (detail.fen_positions.length > 0) {
      setReplayBoard(fenToBoard(detail.fen_positions[0]))
    }
  }, [])

  const replayStep = (delta: number) => {
    if (!replayDetail) return
    const newIdx = Math.max(0, Math.min(replayDetail.fen_positions.length - 1, replayFenIndex + delta))
    setReplayFenIndex(newIdx)
    setReplayBoard(fenToBoard(replayDetail.fen_positions[newIdx]))
  }

  const currentBoard = gameState?.board || new Array(51).fill(EMPTY)
  const isWhiteTurn = gameState?.turn === 'white'
  const boardDisabled = !gameState || !!gameState.result || !isWhiteTurn || isAiThinking

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      {toastMsg && (
        <Toast message={toastMsg} onClose={() => setToastMsg(null)} />
      )}

      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-green-400">
              ♟ AI-Draught
            </h1>
            <p className="text-xs text-gray-400">Entraînement au jeu de dames international (100 cases)</p>
          </div>
          {gameState && (
            <div className="text-sm text-gray-400">
              {isAiThinking && (
                <span className="flex items-center gap-2 text-yellow-400">
                  <div className="spinner" style={{ width: 16, height: 16 }} />
                  L'IA réfléchit...
                </span>
              )}
              {!isAiThinking && gameState.result && (
                <span className="text-yellow-300 font-semibold">{resultLabel(gameState.result)}</span>
              )}
            </div>
          )}
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 pt-4">
        <div className="flex gap-0 border-b border-gray-700">
          {([['play', 'Jouer'], ['exercises', 'Exercices'], ['history', 'Historique']] as [Tab, string][]).map(
            ([key, label]) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`tab-btn ${tab === key ? 'tab-active' : 'tab-inactive'}`}
              >
                {label}
              </button>
            )
          )}
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {tab === 'play' && (
          <div className="flex gap-6 flex-wrap lg:flex-nowrap">
            <div className="flex-shrink-0">
              <Board
                board={currentBoard}
                legalMoves={legalMoves}
                onMove={handleMove}
                selectedSquare={selectedSquare}
                onSelectSquare={handleSelectSquare}
                disabled={boardDisabled}
                lastMove={gameState?.last_move}
              />
              {gameState && (
                <div className="mt-2 flex justify-between text-xs text-gray-500 px-1">
                  <span>Blancs (vous) : bas du plateau</span>
                  <span>FEN: {gameState.fen.substring(0, 30)}...</span>
                </div>
              )}
            </div>

            <div className="flex-1 flex flex-col gap-4 min-w-64">
              <GameControls
                result={gameState?.result || null}
                turn={gameState?.turn || 'white'}
                moveCount={gameState?.move_count || 0}
                aiDepth={aiDepth}
                onNewGame={startNewGame}
                onAiDepthChange={setAiDepth}
                disabled={isAiThinking}
              />

              <MoveList
                moves={moveHistory}
                currentMoveIndex={moveHistory.length - 1}
              />

              <AnalysisPanel
                gameId={gameState?.game_id || null}
                onAnalyze={handleAnalyze}
                analysis={analysis}
                loading={analysisLoading}
              />
            </div>
          </div>
        )}

        {tab === 'exercises' && (
          <div className="flex gap-6 flex-wrap lg:flex-nowrap">
            <div className="flex-shrink-0">
              <Board
                board={exerciseGameState?.board || new Array(51).fill(EMPTY)}
                legalMoves={[]}
                onMove={() => {}}
                selectedSquare={null}
                onSelectSquare={() => {}}
                disabled={true}
              />
              <p className="mt-2 text-xs text-gray-500 text-center">
                Plateau de l'exercice (lecture seule)
              </p>
            </div>

            <div className="flex-1 min-w-64">
              <ExercisePanel
                onExerciseLoad={handleExerciseLoad}
                currentExerciseId={exerciseGameState?.exerciseId || null}
                onMoveSubmit={handleExerciseMoveSubmit}
              />
            </div>
          </div>
        )}

        {tab === 'history' && (
          <div className="flex gap-6 flex-wrap lg:flex-nowrap">
            <div className="flex-shrink-0">
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
                    <div className="mt-2 flex items-center justify-center gap-3">
                      <button
                        onClick={() => replayStep(-1)}
                        disabled={replayFenIndex === 0}
                        className="btn-secondary text-sm"
                      >
                        ← Précédent
                      </button>
                      <span className="text-gray-400 text-sm">
                        {replayFenIndex + 1} / {replayDetail.fen_positions.length}
                      </span>
                      <button
                        onClick={() => replayStep(1)}
                        disabled={replayFenIndex >= (replayDetail.fen_positions.length - 1)}
                        className="btn-secondary text-sm"
                      >
                        Suivant →
                      </button>
                    </div>
                  )}
                </>
              ) : (
                <div
                  style={{
                    width: 560,
                    height: 560,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: '#1f2937',
                    borderRadius: 8,
                    border: '1px dashed #374151',
                  }}
                >
                  <p className="text-gray-600 text-sm">Sélectionnez une partie pour la rejouer</p>
                </div>
              )}
            </div>

            <div className="flex-1 min-w-64">
              <GameHistory onReplay={handleReplay} />
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
