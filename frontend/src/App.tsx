import React, { useState, useCallback, useMemo } from 'react'
import Board from './components/Board'
import AnalysisPanel from './components/AnalysisPanel'
import AnalysisText from './components/AnalysisText'
import GameControls from './components/GameControls'
import MoveList from './components/MoveList'
import ExercisePanel from './components/ExercisePanel'
import GameHistory from './components/GameHistory'
import Toast from './components/Toast'
import LanguageSelector from './components/LanguageSelector'
import BottomSheet from './components/BottomSheet'
import {
  newGame,
  makeMove,
  analyzePosition,
  checkExercise,
  getExercise,
  undoMove,
  resignGame,
  getAiMove,
} from './api/client'
import {
  EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING,
  sqToRowCol, rcToSq,
} from './types'
import type {
  GameStateResponse,
  MoveData,
  AnalysisResponse,
  ExerciseCheckResponse,
  GameDetailResponse,
} from './types'
import { useLanguage } from './i18n/LanguageContext'
import { playMoveSound } from './utils/sound'

function getInitialBoard(): number[] {
  const board = new Array(51).fill(0) // EMPTY = 0
  for (let sq = 1; sq <= 20; sq++) board[sq] = 3  // BLACK_MAN
  for (let sq = 31; sq <= 50; sq++) board[sq] = 1  // WHITE_MAN
  return board
}

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

function pdnToMoveData(pdn: string, board: number[]): MoveData | null {
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

type Tab = 'home' | 'play' | 'exercises' | 'history'

export default function App() {
  const { t, language } = useLanguage()
  const [tab, setTab] = useState<Tab>('home')

  const [gameState, setGameState] = useState<GameStateResponse | null>(null)
  const [selectedSquare, setSelectedSquare] = useState<number | null>(null)
  const [moveHistory, setMoveHistory] = useState<MoveData[]>([])
  const [aiDepth, setAiDepth] = useState(6)
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [toastMsg, setToastMsg] = useState<string | null>(null)
  const [isAiThinking, setIsAiThinking] = useState(false)
  const [bothSides, setBothSides] = useState(false)
  const [spokenSquares, setSpokenSquares] = useState<number[]>([])
  const [showControls, setShowControls] = useState(false)
  const [analysisExpanded, setAnalysisExpanded] = useState(false)
  const [fullSpeaking, setFullSpeaking] = useState(false)
  const [replayingPosition, setReplayingPosition] = useState<{ board: number[], label: string } | null>(null)

  const [exerciseGameState, setExerciseGameState] = useState<{
    board: number[]
    fen: string
    exerciseId: number | null
  } | null>(null)
  const [exerciseLegalMoves, setExerciseLegalMoves] = useState<MoveData[]>([])
  const [exerciseSelectedSquare, setExerciseSelectedSquare] = useState<number | null>(null)
  const [exerciseFeedback, setExerciseFeedback] = useState<ExerciseCheckResponse | null>(null)
  const [exerciseSolved, setExerciseSolved] = useState(false)
  const [exerciseStep, setExerciseStep] = useState(0)
  const [exerciseMovesLoading, setExerciseMovesLoading] = useState(false)

  // When server doesn't provide legal moves, let the user click any piece of the
  // current side and any dark square as destination (server validates on submit).
  // Always use the initial FEN turn indicator — the user always plays the same side.
  const exerciseFreeSelectSquares = useMemo((): Set<number> | undefined => {
    if (!exerciseGameState || exerciseSolved || exerciseLegalMoves.length > 0) return undefined
    const isUserWhite = exerciseGameState.fen.startsWith('W:')
    const board = exerciseGameState.board
    const sels = new Set<number>()
    for (let sq = 1; sq <= 50; sq++) {
      const p = board[sq]
      if (isUserWhite && (p === WHITE_MAN || p === WHITE_KING)) sels.add(sq)
      if (!isUserWhite && (p === BLACK_MAN || p === BLACK_KING)) sels.add(sq)
    }
    return sels.size > 0 ? sels : undefined
  }, [exerciseGameState, exerciseSolved, exerciseLegalMoves])

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
      setMoveHistory([])
      setAnalysis(null)
      setAnalysisExpanded(false)
      setReplayingPosition(null)
    } catch {
      showToast(t('errorCreatingGame'))
    } finally {
      setIsAiThinking(false)
    }
  }, [aiDepth, t])

  const handleGoToPlay = useCallback((bothSidesMode = false) => {
    setBothSides(bothSidesMode)
    setTab('play')
    startNewGame()
  }, [startNewGame])

  const handleSelectSquare = useCallback((sq: number | null) => {
    if (!gameState || gameState.result) return
    if (gameState.turn !== 'white' && !bothSides) return
    setSelectedSquare(sq)
  }, [gameState, bothSides])

  const handleMove = useCallback(async (move: MoveData) => {
    if (!gameState || gameState.result || isAiThinking) return
    setSelectedSquare(null)
    setIsAiThinking(true)

    // Optimistic update: show player's move immediately
    playMoveSound()
    const optimisticBoard = applyMoveLocally(gameState.board, move)
    const nextTurn = gameState.turn === 'white' ? 'black' : 'white'
    setGameState(prev => prev ? { ...prev, board: optimisticBoard, turn: nextTurn, last_move: move, legal_moves: [] } : prev)

    try {
      const response = await makeMove(gameState.game_id, move, aiDepth, bothSides)
      if (response.ai_move) playMoveSound()
      setGameState({
        game_id: response.game_id,
        board: response.board,
        turn: response.turn,
        half_move_clock: response.half_move_clock,
        move_count: response.move_count,
        result: response.result,
        fen: response.fen,
        last_move: response.ai_move || response.player_move,
        legal_moves: response.legal_moves ?? [],
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
      setGameState(prev => prev ? { ...prev, board: gameState.board, turn: 'white', last_move: gameState.last_move, legal_moves: gameState.legal_moves } : prev)
    } finally {
      setIsAiThinking(false)
    }
  }, [gameState, aiDepth, isAiThinking, bothSides])

  const handleResign = useCallback(async () => {
    if (!gameState || isAiThinking || gameState.result) return
    if (!window.confirm(t('resignConfirm'))) return
    try {
      await resignGame(gameState.game_id)
      setGameState(prev => prev ? { ...prev, result: 'black' } : prev)
    } catch {
      showToast('Erreur lors de l\'abandon.')
    }
  }, [gameState, isAiThinking, t])

  const handleUndo = useCallback(async () => {
    if (!gameState || isAiThinking) return
    try {
      setIsAiThinking(true)
      const state = await undoMove(gameState.game_id)
      setGameState(state)
      setMoveHistory(prev => prev.slice(0, state.move_count))
      setSelectedSquare(null)
      setAnalysis(null)
      setAnalysisExpanded(false)
    } catch {
      showToast('Impossible d\'annuler le coup.')
    } finally {
      setIsAiThinking(false)
    }
  }, [gameState, isAiThinking])

  const handleBestMoveQuick = useCallback(async (): Promise<string[] | null> => {
    if (!gameState) return null
    try {
      const move = await getAiMove(gameState.game_id, aiDepth)
      if (!move) return []
      const notation = move.captures.length > 0
        ? move.path.join('x')
        : `${move.path[0]}-${move.path[move.path.length - 1]}`
      return [notation]
    } catch {
      return null
    }
  }, [gameState, aiDepth])

  const handleFullTextSpeak = useCallback(() => {
    if (!analysis) return
    if (fullSpeaking) {
      window.speechSynthesis?.cancel()
      setFullSpeaking(false)
      return
    }
    window.speechSynthesis?.cancel()
    const utt = new SpeechSynthesisUtterance(analysis.analysis)
    utt.lang = language === 'en' ? 'en-GB' : 'fr-FR'
    utt.rate = 0.9
    utt.onend = () => setFullSpeaking(false)
    utt.onerror = () => setFullSpeaking(false)
    setFullSpeaking(true)
    window.speechSynthesis?.speak(utt)
  }, [analysis, language, fullSpeaking])

  const handleAnalyze = useCallback(async (question?: string, mode?: string): Promise<AnalysisResponse | null> => {
    if (!gameState) return null
    setAnalysisLoading(true)
    try {
      const result = await analyzePosition(gameState.game_id, question, language, mode || 'position', aiDepth)
      setAnalysis(result)
      setAnalysisExpanded(true)
      setReplayingPosition(null)
      return result
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      showToast(`${t('errorAnalysis')}${err?.response?.data?.detail || 'Erreur inconnue'}`)
      return null
    } finally {
      setAnalysisLoading(false)
    }
  }, [gameState, language, aiDepth, t])

  const handleExerciseLoad = useCallback(async (fen: string, exerciseId: number) => {
    setExerciseGameState({ board: fenToBoard(fen), fen, exerciseId })
    setExerciseLegalMoves([])
    setExerciseSelectedSquare(null)
    setExerciseFeedback(null)
    setExerciseSolved(false)
    setExerciseStep(0)
    setExerciseMovesLoading(true)
    try {
      const ex = await getExercise(exerciseId)
      setExerciseLegalMoves(ex.legal_moves ?? [])
    } catch (e: unknown) {
      const err = e as { message?: string }
      setToastMsg(`Erreur chargement des coups: ${err?.message || 'inconnue'}`)
    } finally {
      setExerciseMovesLoading(false)
    }
  }, [])

  const handleExerciseMove = useCallback(async (move: MoveData) => {
    if (!exerciseGameState?.exerciseId || exerciseSolved) return
    setExerciseSelectedSquare(null)

    let pdn: string
    let fullMove: MoveData = move

    if (move.captures.length > 0) {
      pdn = move.path.join('x')
      fullMove = move
    } else if (move.path.length === 2) {
      const [from, to] = move.path
      const [r1, c1] = sqToRowCol(from)
      const [r2, c2] = sqToRowCol(to)
      const dr = r2 - r1
      const dc = c2 - c1
      const board = exerciseGameState.board
      const fen = exerciseGameState.fen
      const isUserWhite = fen.startsWith('W:')
      let capturedSq: number | null = null
      if (Math.abs(dr) === 2 && Math.abs(dc) === 2) {
        const midSq = rcToSq(r1 + dr / 2, c1 + dc / 2)
        if (midSq !== null) {
          const mid = board[midSq]
          const isEnemy = isUserWhite
            ? (mid === BLACK_MAN || mid === BLACK_KING)
            : (mid === WHITE_MAN || mid === WHITE_KING)
          if (isEnemy) capturedSq = midSq
        }
      }
      if (capturedSq !== null) {
        pdn = `${from}x${to}`
        fullMove = { path: move.path, captures: [capturedSq] }
      } else {
        pdn = `${from}-${to}`
        fullMove = move
      }
    } else {
      pdn = move.path.join('x')
    }

    try {
      const result = await checkExercise(exerciseGameState.exerciseId, [pdn], exerciseStep)

      if (result.correct) {
        // Apply user's move to board
        const boardAfterUser = applyMoveLocally(exerciseGameState.board, fullMove)

        // Apply opponent's auto-move if provided
        let finalBoard = boardAfterUser
        if (result.auto_move_path && result.auto_move_path.length > 0) {
          const autoData: MoveData = {
            path: result.auto_move_path,
            captures: result.auto_move_captures ?? [],
          }
          finalBoard = applyMoveLocally(boardAfterUser, autoData)
        } else if (result.auto_move) {
          const autoData = pdnToMoveData(result.auto_move, boardAfterUser)
          if (autoData) {
            finalBoard = applyMoveLocally(boardAfterUser, autoData)
          }
        }

        setExerciseGameState(prev => prev ? { ...prev, board: finalBoard } : prev)

        if (result.in_progress) {
          // More user moves remain — advance step, clear feedback, keep playing
          setExerciseStep(s => s + 1)
          setExerciseFeedback(null)
          setExerciseLegalMoves([])
        } else {
          // Exercise complete
          setExerciseSolved(true)
          setExerciseLegalMoves([])
          setExerciseFeedback(result)
        }
      } else {
        setExerciseFeedback(result)
      }
    } catch {
      showToast(t('errorVerification'))
    }
  }, [exerciseGameState, exerciseSolved, exerciseStep, t])

  const handleExerciseSelectSquare = useCallback((sq: number | null) => {
    if (exerciseSolved) return
    setExerciseSelectedSquare(sq)
  }, [exerciseSolved])

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

  // Reconstruct all board positions from move history for replay
  const boardPositions = useMemo(() => {
    const positions: number[][] = [getInitialBoard()]
    for (const move of moveHistory) {
      positions.push(applyMoveLocally(positions[positions.length - 1], move))
    }
    return positions
  }, [moveHistory])

  const moveMap = useMemo(() => {
    const map = new Map<string, number>()
    moveHistory.forEach((move, i) => {
      const isCapture = move.captures.length > 0
      const fullPdn = isCapture ? move.path.join('x') : `${move.path[0]}-${move.path[move.path.length - 1]}`
      const shortPdn = `${move.path[0]}${isCapture ? 'x' : '-'}${move.path[move.path.length - 1]}`
      if (!map.has(fullPdn)) map.set(fullPdn, i)
      if (!map.has(shortPdn)) map.set(shortPdn, i)
    })
    return map
  }, [moveHistory])

  const handleAnalysisMoveClick = useCallback((pdn: string) => {
    const idx = moveMap.get(pdn)
    if (idx !== undefined) {
      setReplayingPosition({ board: boardPositions[idx + 1], label: pdn })
    }
  }, [moveMap, boardPositions])

  const currentBoard = gameState?.board || new Array(51).fill(EMPTY)
  const displayBoard = replayingPosition?.board ?? currentBoard
  const isWhiteTurn = gameState?.turn === 'white'
  const boardDisabled = !!replayingPosition || !gameState || !!gameState.result || isAiThinking || (!isWhiteTurn && !bothSides)
  const legalMoves = boardDisabled ? [] : (gameState?.legal_moves ?? [])

  const pieceDiff = (() => {
    if (!gameState) return 0
    let w = 0, b = 0
    for (let sq = 1; sq <= 50; sq++) {
      const p = gameState.board[sq]
      if (p === WHITE_MAN || p === WHITE_KING) w++
      else if (p === BLACK_MAN || p === BLACK_KING) b++
    }
    return w - b
  })()



  return (
    <div className="bg-gray-900 text-gray-100 flex flex-col h-full">
      {toastMsg && <Toast message={toastMsg} onClose={() => setToastMsg(null)} />}

      {/* Header — compact on mobile */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex-shrink-0">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-amber-600 whitespace-nowrap">♟ AI-Draught</h1>
            {tab !== 'home' && (
              <button
                onClick={() => setTab('home')}
                className="text-gray-400 hover:text-amber-500 text-lg w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-700 transition-colors"
                title={t('home')}
              >
                🏠
              </button>
            )}
            {tab === 'play' && bothSides && (
              <span className="text-lg" title={t('playBothSides')}>⚔</span>
            )}
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


      {/* Main content — mobile: no page scroll (each section scrolls itself); desktop: page scrolls */}
      <main className="flex-1 overflow-hidden lg:overflow-y-auto">

        {/* HOME SCREEN */}
        {tab === 'home' && (
          <div className="h-full flex flex-col items-center justify-center px-4 py-8 overflow-y-auto">
            <p className="text-gray-400 text-sm mb-10 text-center">{t('appSubtitle')}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-2xl">
              {/* Play */}
              <button
                onClick={() => handleGoToPlay(false)}
                className="group flex flex-col items-center gap-3 bg-gray-800 hover:bg-gray-750 border border-gray-700 hover:border-amber-600 rounded-xl p-8 transition-all duration-200 cursor-pointer"
              >
                <span className="text-5xl group-hover:scale-110 transition-transform duration-200">♟</span>
                <span className="text-lg font-bold text-white">{t('tabPlay')}</span>
                <span className="text-sm text-gray-400 text-center">{t('playDesc')}</span>
              </button>
              {/* Play both sides */}
              <button
                onClick={() => handleGoToPlay(true)}
                className="group flex flex-col items-center gap-3 bg-gray-800 hover:bg-gray-750 border border-gray-700 hover:border-amber-600 rounded-xl p-8 transition-all duration-200 cursor-pointer"
              >
                <span className="text-5xl group-hover:scale-110 transition-transform duration-200">⚔</span>
                <span className="text-lg font-bold text-white">{t('playBothSides')}</span>
                <span className="text-sm text-gray-400 text-center">{t('playBothSidesDesc')}</span>
              </button>
              {/* Exercises */}
              <button
                onClick={() => setTab('exercises')}
                className="group flex flex-col items-center gap-3 bg-gray-800 hover:bg-gray-750 border border-gray-700 hover:border-amber-600 rounded-xl p-8 transition-all duration-200 cursor-pointer"
              >
                <span className="text-5xl group-hover:scale-110 transition-transform duration-200">✏️</span>
                <span className="text-lg font-bold text-white">{t('tabExercises')}</span>
                <span className="text-sm text-gray-400 text-center">{t('exercisesDesc')}</span>
              </button>
              {/* History */}
              <button
                onClick={() => setTab('history')}
                className="group flex flex-col items-center gap-3 bg-gray-800 hover:bg-gray-750 border border-gray-700 hover:border-amber-600 rounded-xl p-8 transition-all duration-200 cursor-pointer"
              >
                <span className="text-5xl group-hover:scale-110 transition-transform duration-200">📋</span>
                <span className="text-lg font-bold text-white">{t('tabHistory')}</span>
                <span className="text-sm text-gray-400 text-center">{t('historyDesc')}</span>
              </button>
            </div>
          </div>
        )}

        {/* PLAY TAB */}
        {tab === 'play' && (
          <>
            {/* ── MOBILE (hidden on lg+) ── */}
            <div className="lg:hidden h-full flex flex-col">
              {analysisExpanded ? (
                <>
                  {/* Top (fixed): small board right + compact panel left */}
                  <div
                    className="flex-shrink-0 grid gap-2 px-2 pt-2"
                    style={{ gridTemplateColumns: 'minmax(0,1fr) min(42vw, 200px)' }}
                  >
                    <div style={{ gridColumn: '1', gridRow: '1' }} className="min-w-0">
                      <AnalysisPanel
                        gameId={gameState?.game_id || null}
                        onAnalyze={handleAnalyze}
                        onBestMove={handleBestMoveQuick}
                        analysis={analysis}
                        loading={analysisLoading}
                        onHighlightSquare={setSpokenSquares}
                        expanded={true}
                        onCollapse={() => setAnalysisExpanded(false)}
                        aiThinking={isAiThinking}
                        onMoveClick={handleAnalysisMoveClick}
                      />
                    </div>
                    <div
                      style={{ gridColumn: '2', gridRow: '1', width: 'min(42vw, 200px)' }}
                      className="flex flex-col items-center"
                    >
                      <Board
                        board={displayBoard}
                        legalMoves={legalMoves}
                        onMove={handleMove}
                        selectedSquare={selectedSquare}
                        onSelectSquare={handleSelectSquare}
                        disabled={boardDisabled}
                        lastMove={gameState?.last_move}
                        spokenSquares={spokenSquares}
                      />
                      {gameState && (
                        <div style={{ alignSelf: 'stretch', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <button onClick={handleUndo} disabled={isAiThinking || !moveHistory.length || !!gameState.result}
                            title={t('undoMove')}
                            className="flex-1 font-semibold bg-amber-700 hover:bg-amber-600 text-white disabled:opacity-30 disabled:cursor-not-allowed px-2 py-1 rounded-lg transition-colors text-base"
                          >←</button>
                          <button onClick={handleResign} disabled={isAiThinking || !!gameState.result}
                            title={t('resign')}
                            className="flex-1 font-semibold bg-gray-700 hover:bg-gray-600 text-white disabled:opacity-30 disabled:cursor-not-allowed px-2 py-1 rounded-lg transition-colors text-base"
                          >🏳️</button>
                          {moveHistory.length > 0 && (
                            <span style={{ fontWeight: 600, fontSize: '0.8rem' }}
                              className={pieceDiff > 0 ? 'text-green-400' : pieceDiff < 0 ? 'text-red-400' : 'text-gray-400'}>
                              {pieceDiff > 0 ? `+${pieceDiff}` : pieceDiff === 0 ? '=' : `${pieceDiff}`}
                            </span>
                          )}
                        </div>
                      )}
                      {replayingPosition && (
                        <div className="flex items-center gap-2 mt-1 bg-amber-900/40 border border-amber-700/60 rounded px-2 py-1 text-xs">
                          <span className="text-amber-300 font-mono font-semibold">📍 {replayingPosition.label}</span>
                          <button onClick={() => setReplayingPosition(null)} className="ml-auto text-gray-400 hover:text-white">✕</button>
                        </div>
                      )}
                    </div>
                  </div>
                  {/* Bottom (scrollable): full analysis text + move list */}
                  <div className="flex-1 overflow-y-auto overscroll-contain pb-4 px-2 pt-2 flex flex-col gap-2">
                    {analysis && (
                      <div className="panel">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-gray-400 uppercase font-semibold">{t('fullAnalysis')}</span>
                          <button onClick={handleFullTextSpeak}
                            className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-colors ${fullSpeaking ? 'bg-red-700 hover:bg-red-600 text-white' : 'bg-gray-700 hover:bg-gray-600 text-gray-300'}`}>
                            <span>{fullSpeaking ? '⏹' : '🔊'}</span>
                            <span>{fullSpeaking ? t('stopReading') : t('readAloud')}</span>
                          </button>
                        </div>
                        <AnalysisText
                          text={analysis.analysis}
                          onMoveClick={handleAnalysisMoveClick}
                          className="text-gray-200 leading-relaxed text-sm whitespace-pre-wrap"
                        />
                      </div>
                    )}
                    <MoveList moves={moveHistory} currentMoveIndex={moveHistory.length - 1} />
                  </div>
                </>
              ) : (
                <>
                  {/* Board full width */}
                  <div className="flex-shrink-0 flex flex-col items-center px-2 pt-2" style={{ width: '100%', maxWidth: '560px', alignSelf: 'center' }}>
                    <Board
                      board={displayBoard}
                      legalMoves={legalMoves}
                      onMove={handleMove}
                      selectedSquare={selectedSquare}
                      onSelectSquare={handleSelectSquare}
                      disabled={boardDisabled}
                      lastMove={gameState?.last_move}
                      spokenSquares={spokenSquares}
                    />
                    {gameState && (
                      <div style={{ alignSelf: 'stretch', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <button onClick={handleUndo} disabled={isAiThinking || !moveHistory.length || !!gameState.result}
                          title={t('undoMove')} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                          className="text-sm font-semibold bg-amber-700 hover:bg-amber-600 text-white disabled:opacity-30 disabled:cursor-not-allowed px-3 py-1.5 rounded-lg transition-colors">
                          <span>←</span><span>{t('undoMove')}</span>
                        </button>
                        <button onClick={handleResign} disabled={isAiThinking || !!gameState.result}
                          title={t('resign')} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                          className="text-sm font-semibold bg-gray-700 hover:bg-gray-600 text-white disabled:opacity-30 disabled:cursor-not-allowed px-3 py-1.5 rounded-lg transition-colors">
                          <span>🏳️</span><span>{t('resign')}</span>
                        </button>
                        {moveHistory.length > 0 && (
                          <span style={{ marginLeft: 'auto', fontWeight: 600, fontSize: '0.9rem' }}
                            className={pieceDiff > 0 ? 'text-green-400' : pieceDiff < 0 ? 'text-red-400' : 'text-gray-400'}>
                            {pieceDiff > 0 ? `+${pieceDiff}` : pieceDiff === 0 ? '=' : `${pieceDiff}`}
                          </span>
                        )}
                      </div>
                    )}
                    {gameState && <p style={{ alignSelf: 'flex-start' }} className="mt-1 text-xs text-gray-500">{t('whitePerspective')}</p>}
                    {replayingPosition && (
                      <div className="flex items-center gap-2 mt-1 w-full bg-amber-900/40 border border-amber-700/60 rounded px-2 py-1 text-xs">
                        <span className="text-amber-300 font-mono font-semibold">📍 {replayingPosition.label}</span>
                        <button onClick={() => setReplayingPosition(null)} className="ml-auto text-gray-400 hover:text-white">✕</button>
                      </div>
                    )}
                  </div>
                  {/* Scrollable right panel */}
                  <div className="flex-1 overflow-y-auto overscroll-contain pb-4 min-w-0">
                    <div className="flex flex-col gap-3 px-2 py-3">
                      <AnalysisPanel
                        gameId={gameState?.game_id || null}
                        onAnalyze={handleAnalyze}
                        onBestMove={handleBestMoveQuick}
                        analysis={analysis}
                        loading={analysisLoading}
                        onHighlightSquare={setSpokenSquares}
                        expanded={false}
                        onCollapse={() => setAnalysisExpanded(false)}
                        aiThinking={isAiThinking}
                        onMoveClick={handleAnalysisMoveClick}
                      />
                      <MoveList moves={moveHistory} currentMoveIndex={moveHistory.length - 1} />
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* ── DESKTOP (hidden below lg) ── */}
            <div
              className={analysisExpanded
                ? 'hidden lg:grid gap-3 max-w-7xl mx-auto px-4 py-4 pb-6'
                : 'hidden lg:flex lg:flex-row lg:gap-6 lg:max-w-7xl lg:mx-auto lg:px-4 lg:py-4'
              }
              style={analysisExpanded ? { gridTemplateColumns: '1fr min(46%, 280px)' } : {}}
            >
              {/* Board */}
              <div
                className={analysisExpanded ? 'self-start sticky top-0 flex flex-col items-center' : 'flex-shrink-0 flex flex-col items-center'}
                style={analysisExpanded ? { gridColumn: '2', gridRow: '1 / span 10' } : { width: '100%', maxWidth: '560px' }}
              >
                <Board
                  board={displayBoard}
                  legalMoves={legalMoves}
                  onMove={handleMove}
                  selectedSquare={selectedSquare}
                  onSelectSquare={handleSelectSquare}
                  disabled={boardDisabled}
                  lastMove={gameState?.last_move}
                  spokenSquares={spokenSquares}
                />
                {gameState && (
                  <div style={{ alignSelf: 'stretch', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button onClick={handleUndo} disabled={isAiThinking || !moveHistory.length || !!gameState.result}
                      title={t('undoMove')} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                      className="text-sm font-semibold bg-amber-700 hover:bg-amber-600 text-white disabled:opacity-30 disabled:cursor-not-allowed px-3 py-1.5 rounded-lg transition-colors">
                      <span>←</span><span>{t('undoMove')}</span>
                    </button>
                    <button onClick={handleResign} disabled={isAiThinking || !!gameState.result}
                      title={t('resign')} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                      className="text-sm font-semibold bg-gray-700 hover:bg-gray-600 text-white disabled:opacity-30 disabled:cursor-not-allowed px-3 py-1.5 rounded-lg transition-colors">
                      <span>🏳️</span><span>{t('resign')}</span>
                    </button>
                    {moveHistory.length > 0 && (
                      <span style={{ marginLeft: 'auto', fontWeight: 600, fontSize: '0.9rem' }}
                        className={pieceDiff > 0 ? 'text-green-400' : pieceDiff < 0 ? 'text-red-400' : 'text-gray-400'}>
                        {pieceDiff > 0 ? `+${pieceDiff}` : pieceDiff === 0 ? '=' : `${pieceDiff}`}
                      </span>
                    )}
                  </div>
                )}
                {gameState && <p style={{ alignSelf: 'flex-start' }} className="mt-1 text-xs text-gray-500">{t('whitePerspective')}</p>}
                    {replayingPosition && (
                      <div className="flex items-center gap-2 mt-1 w-full bg-amber-900/40 border border-amber-700/60 rounded px-2 py-1 text-xs">
                        <span className="text-amber-300 font-mono font-semibold">📍 {replayingPosition.label}</span>
                        <button onClick={() => setReplayingPosition(null)} className="ml-auto text-gray-400 hover:text-white">✕</button>
                      </div>
                    )}
              </div>

              {/* Analysis panel */}
              {analysisExpanded ? (
                <div style={{ gridColumn: '1', gridRow: '1' }} className="min-w-0">
                  <AnalysisPanel
                    gameId={gameState?.game_id || null}
                    onAnalyze={handleAnalyze}
                    onBestMove={handleBestMoveQuick}
                    analysis={analysis}
                    loading={analysisLoading}
                    onHighlightSquare={setSpokenSquares}
                    expanded={true}
                    onCollapse={() => setAnalysisExpanded(false)}
                    aiThinking={isAiThinking}
                    onMoveClick={handleAnalysisMoveClick}
                  />
                </div>
              ) : (
                <div className="flex-1 overflow-y-auto overscroll-contain pb-4 min-w-0">
                  <div className="flex flex-col gap-3">
                    <AnalysisPanel
                      gameId={gameState?.game_id || null}
                      onAnalyze={handleAnalyze}
                      onBestMove={handleBestMoveQuick}
                      analysis={analysis}
                      loading={analysisLoading}
                      onHighlightSquare={setSpokenSquares}
                      expanded={false}
                      onCollapse={() => setAnalysisExpanded(false)}
                      aiThinking={isAiThinking}
                      onMoveClick={handleAnalysisMoveClick}
                    />
                    <GameControls
                      result={gameState?.result || null}
                      turn={gameState?.turn || 'white'}
                      moveCount={gameState?.move_count || 0}
                      aiDepth={aiDepth}
                      onNewGame={startNewGame}
                      onAiDepthChange={setAiDepth}
                      disabled={isAiThinking}
                    />
                    <MoveList moves={moveHistory} currentMoveIndex={moveHistory.length - 1} />
                  </div>
                </div>
              )}

              {/* Full analysis text (expanded only) */}
              {analysisExpanded && analysis && (
                <div style={{ gridColumn: '1', gridRow: '2' }} className="min-w-0">
                  <div className="panel">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-gray-400 uppercase font-semibold">{t('fullAnalysis')}</span>
                      <button onClick={handleFullTextSpeak}
                        className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-colors ${fullSpeaking ? 'bg-red-700 hover:bg-red-600 text-white' : 'bg-gray-700 hover:bg-gray-600 text-gray-300'}`}>
                        <span>{fullSpeaking ? '⏹' : '🔊'}</span>
                        <span>{fullSpeaking ? t('stopReading') : t('readAloud')}</span>
                      </button>
                    </div>
                    <AnalysisText text={analysis.analysis} onMoveClick={handleAnalysisMoveClick} className="text-gray-200 leading-relaxed text-sm whitespace-pre-wrap" />
                  </div>
                </div>
              )}

              {/* Move list */}
              {analysisExpanded && (
                <div style={{ gridColumn: '1', gridRow: '3' }} className="min-w-0">
                  <MoveList moves={moveHistory} currentMoveIndex={moveHistory.length - 1} />
                </div>
              )}

              {/* Game controls (expanded only) */}
              {analysisExpanded && (
                <div style={{ gridColumn: '1', gridRow: '4' }} className="min-w-0">
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
              )}
            </div>
          </>
        )}

        {/* EXERCISES TAB */}
        {tab === 'exercises' && (
          <div className="h-full flex flex-col lg:h-auto lg:flex-row lg:gap-6 lg:max-w-7xl lg:mx-auto lg:px-4 lg:py-4">
            <div className="flex-shrink-0 flex flex-col items-center px-2 pt-2 lg:px-0 lg:pt-0" style={{ width: '100%', maxWidth: '560px', alignSelf: 'center' }}>
              <Board
                board={exerciseGameState?.board || new Array(51).fill(EMPTY)}
                legalMoves={exerciseLegalMoves}
                onMove={handleExerciseMove}
                selectedSquare={exerciseSelectedSquare}
                onSelectSquare={handleExerciseSelectSquare}
                disabled={exerciseSolved || !exerciseGameState}
                freeSelectSquares={exerciseFreeSelectSquares}
              />
              {/* Feedback banner — shown immediately under the board */}
              {exerciseFeedback && exerciseGameState && (
                <div
                  className={`w-full mt-3 rounded-xl px-4 py-3 text-center ${
                    exerciseFeedback.correct
                      ? 'bg-amber-900 border border-amber-600 text-amber-100'
                      : 'bg-red-900 border border-red-600 text-red-200'
                  }`}
                >
                  <p className="text-lg font-bold">
                    {exerciseFeedback.correct ? `✓ ${t('wellDone')}` : `✗ ${t('tryAgain')}`}
                  </p>
                  {exerciseFeedback.solution && (
                    <p className="text-sm mt-1 opacity-80">
                      Solution : {exerciseFeedback.solution.join(', ')}
                    </p>
                  )}
                  {!exerciseFeedback.correct && (
                    <button
                      onClick={() => {
                        if (exerciseGameState) {
                          setExerciseFeedback(null)
                          setExerciseSolved(false)
                          setExerciseStep(0)
                          setExerciseSelectedSquare(null)
                          // Reset board to initial FEN position
                          setExerciseGameState(prev =>
                            prev ? { ...prev, board: fenToBoard(prev.fen) } : prev
                          )
                        }
                      }}
                      className="mt-2 px-4 py-1 rounded-lg bg-red-700 hover:bg-red-600 text-white text-sm font-semibold transition-colors"
                    >
                      {t('tryAgain')}
                    </button>
                  )}
                </div>
              )}
              {exerciseMovesLoading && !exerciseFeedback && (
                <div className="flex items-center gap-2 mt-2 text-xs text-gray-400">
                  <div className="spinner" style={{ width: 12, height: 12 }} />
                  <span>{t('loading')}</span>
                </div>
              )}
            </div>
            <div className="flex-1 overflow-y-auto overscroll-contain pb-4 min-w-0">
              <div className="px-2 py-3 lg:px-0">
                <ExercisePanel
                  onExerciseLoad={handleExerciseLoad}
                  currentExerciseId={exerciseGameState?.exerciseId || null}
                  feedback={exerciseFeedback}
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
            <div className="flex-1 overflow-y-auto overscroll-contain pb-4 min-w-0">
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

    </div>
  )
}
