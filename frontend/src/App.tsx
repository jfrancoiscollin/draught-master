import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import Board from './components/Board'
import AnalysisPanel from './components/AnalysisPanel'
import AnalysisText from './components/AnalysisText'
import GameControls from './components/GameControls'
import MoveList from './components/MoveList'
import ExercisePanel from './components/ExercisePanel'
import ExerciseLibraryPage from './components/ExerciseLibraryPage'
import LessonPanel from './components/LessonPanel'
import ImportGamePanel from './components/ImportGamePanel'
import Toast from './components/Toast'
import LanguageSelector from './components/LanguageSelector'
import Logo from './components/Logo'
import logoBothSrc from './assets/logo-both.png'
import logoPlaySrc from './assets/logo-play.png'
import BottomSheet from './components/BottomSheet'
import LoginPage from './components/LoginPage'
import { useAuth } from './contexts/AuthContext'
import {
  newGame,
  makeMove,
  analyzePosition,
  checkExercise,
  getExercise,
  getExerciseLegalMovesAtStep,
  undoMove,
  resignGame,
  getAiMove,
  getReadLessons,
} from './api/client'
import { getScanEngine, matchHubMove } from './lib/scanEngine'
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

type Tab = 'home' | 'play' | 'exercise-library' | 'exercises' | 'import-game'

export default function App() {
  const { t, language } = useLanguage()
  const { user, logout } = useAuth()
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
  const exerciseLoadGenRef = useRef(0)

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

  const [lessonOpen, setLessonOpen] = useState<{ chapter: number; fen: string } | null>(null)
  const [readChapters, setReadChapters] = useState<Set<number>>(new Set())

  useEffect(() => {
    if (!user) { setReadChapters(new Set()); return }
    getReadLessons().then(chapters => setReadChapters(new Set(chapters))).catch(() => {})
  }, [user])

  const handleLessonRead = useCallback((chapter: number) => {
    setReadChapters(prev => new Set([...prev, chapter]))
  }, [])

  const [replayBoard, setReplayBoard] = useState<number[] | null>(null)
  const [replayFenIndex, setReplayFenIndex] = useState(0)
  const [replayDetail, setReplayDetail] = useState<GameDetailResponse | null>(null)

  const showToast = (msg: string) => setToastMsg(msg)

  const resetExerciseState = useCallback(() => {
    setExerciseGameState(null)
    setExerciseSolved(false)
    setExerciseFeedback(null)
    setExerciseLegalMoves([])
    setExerciseSelectedSquare(null)
    setExerciseStep(0)
    setExerciseMovesLoading(false)
  }, [])

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
      if (bothSides) {
        // Both-sides mode: just apply the move, no AI
        const response = await makeMove(gameState.game_id, move, aiDepth, true)
        setGameState({
          game_id: response.game_id,
          board: response.board,
          turn: response.turn,
          half_move_clock: response.half_move_clock,
          move_count: response.move_count,
          result: response.result,
          fen: response.fen,
          last_move: response.player_move,
          legal_moves: response.legal_moves ?? [],
        })
        setMoveHistory(prev => [...prev, response.player_move])
      } else {
        // Play-alone mode: apply player's move then use WASM for AI
        const playerResp = await makeMove(gameState.game_id, move, aiDepth, true)
        setMoveHistory(prev => [...prev, playerResp.player_move])

        if (playerResp.result) {
          // Game already ended after player's move
          setGameState({
            game_id: playerResp.game_id,
            board: playerResp.board,
            turn: playerResp.turn,
            half_move_clock: playerResp.half_move_clock,
            move_count: playerResp.move_count,
            result: playerResp.result,
            fen: playerResp.fen,
            last_move: playerResp.player_move,
            legal_moves: [],
          })
        } else {
          // AI's turn — use WASM engine
          const wasmMs = Math.max(200, aiDepth * 250)  // 250–2000 ms depending on level
          const engine = getScanEngine()
          const hubMove = await engine.getMove(playerResp.fen, wasmMs)

          let aiMoveData: MoveData | null = null
          if (hubMove) {
            aiMoveData = matchHubMove(hubMove, playerResp.legal_moves)
          }

          const applyAiResp = (resp: typeof playerResp, aiMove: MoveData) => {
            playMoveSound()
            setGameState({
              game_id: resp.game_id,
              board: resp.board,
              turn: resp.turn,
              half_move_clock: resp.half_move_clock,
              move_count: resp.move_count,
              result: resp.result,
              fen: resp.fen,
              last_move: aiMove,
              legal_moves: resp.legal_moves ?? [],
            })
            setMoveHistory(prev => [...prev, aiMove])
          }

          if (aiMoveData) {
            // WASM gave a valid move — apply it
            const aiResp = await makeMove(gameState.game_id, aiMoveData, aiDepth, true)
            applyAiResp(aiResp, aiMoveData)
          } else {
            // WASM not ready yet — ask server Scan to compute AI move only
            // (player's move is already committed, so we only need the AI's response)
            const serverAiMove = await getAiMove(gameState.game_id, aiDepth)
            if (serverAiMove) {
              const aiResp = await makeMove(gameState.game_id, serverAiMove, aiDepth, true)
              applyAiResp(aiResp, serverAiMove)
            } else {
              // No AI move (game ended or error) — show current state
              setGameState({
                game_id: playerResp.game_id,
                board: playerResp.board,
                turn: playerResp.turn,
                half_move_clock: playerResp.half_move_clock,
                move_count: playerResp.move_count,
                result: playerResp.result,
                fen: playerResp.fen,
                last_move: playerResp.player_move,
                legal_moves: playerResp.legal_moves ?? [],
              })
            }
          }
        }
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      showToast(err?.response?.data?.detail || 'Coup illégal ou erreur serveur.')
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
    const gen = ++exerciseLoadGenRef.current
    setExerciseGameState({ board: fenToBoard(fen), fen, exerciseId })
    setExerciseLegalMoves([])
    setExerciseSelectedSquare(null)
    setExerciseFeedback(null)
    setExerciseSolved(false)
    setExerciseStep(0)
    setExerciseMovesLoading(true)
    try {
      const ex = await getExercise(exerciseId)
      if (exerciseLoadGenRef.current !== gen) return
      setExerciseLegalMoves(ex.legal_moves ?? [])
    } catch (e: unknown) {
      if (exerciseLoadGenRef.current !== gen) return
      const err = e as { message?: string }
      setToastMsg(`Erreur chargement des coups: ${err?.message || 'inconnue'}`)
    } finally {
      if (exerciseLoadGenRef.current === gen) setExerciseMovesLoading(false)
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

      // Not on the same diagonal → must be a complex capture (short PDN form)
      if (Math.abs(dr) !== Math.abs(dc)) {
        pdn = `${from}x${to}`
        fullMove = move
      } else if (Math.abs(dr) === 1) {
        // Single diagonal step → simple non-capture move
        pdn = `${from}-${to}`
        fullMove = move
      } else if (Math.abs(dr) === 2) {
        // Man single-capture check
        const midSq = rcToSq(r1 + dr / 2, c1 + dc / 2)
        let capturedSq: number | null = null
        if (midSq !== null) {
          const mid = board[midSq]
          const isEnemy = isUserWhite
            ? (mid === BLACK_MAN || mid === BLACK_KING)
            : (mid === WHITE_MAN || mid === WHITE_KING)
          if (isEnemy) capturedSq = midSq
        }
        if (capturedSq !== null) {
          pdn = `${from}x${to}`
          fullMove = { path: move.path, captures: [capturedSq] }
        } else {
          pdn = `${from}-${to}`
          fullMove = move
        }
      } else {
        // King long-range: check if any enemy lies along the diagonal
        const dirR = Math.sign(dr), dirC = Math.sign(dc)
        let r = r1 + dirR, c = c1 + dirC
        let hasEnemy = false
        while (r !== r2 || c !== c2) {
          const sq = rcToSq(r, c)
          if (sq !== null && board[sq] !== EMPTY) {
            const p = board[sq]
            const isEnemy = isUserWhite
              ? (p === BLACK_MAN || p === BLACK_KING)
              : (p === WHITE_MAN || p === WHITE_KING)
            if (isEnemy) { hasEnemy = true; break }
          }
          r += dirR; c += dirC
        }
        pdn = hasEnemy ? `${from}x${to}` : `${from}-${to}`
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
          const nextStep = exerciseStep + 1
          setExerciseStep(nextStep)
          setExerciseFeedback(null)
          // Seed with what the server already computed; then fetch authoritative moves
          setExerciseLegalMoves(result.next_legal_moves ?? [])
          if (exerciseGameState?.exerciseId) {
            const currentGen = exerciseLoadGenRef.current
            getExerciseLegalMovesAtStep(exerciseGameState.exerciseId, nextStep)
              .then(({ moves }) => {
                if (exerciseLoadGenRef.current === currentGen) setExerciseLegalMoves(moves)
              })
              .catch(() => {})
          }
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
            <h1 className="text-xl font-bold text-amber-600 whitespace-nowrap flex items-center gap-2">
              <Logo size={28} />
              Draught Master
            </h1>
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
              onClick={logout}
              className="text-gray-400 hover:text-red-400 w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-700 transition-colors"
              title={`${t('logout')} (${user.email})`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" width="18" height="18">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
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
                <img src={logoPlaySrc} alt="" className="w-16 h-16 group-hover:scale-110 transition-transform duration-200" style={{ objectFit: 'contain' }} />
                <span className="text-lg font-bold text-white">{t('tabPlay')}</span>
                <span className="text-sm text-gray-400 text-center">{t('playDesc')}</span>
              </button>
              {/* Play both sides */}
              <button
                onClick={() => handleGoToPlay(true)}
                className="group flex flex-col items-center gap-3 bg-gray-800 hover:bg-gray-750 border border-gray-700 hover:border-amber-600 rounded-xl p-8 transition-all duration-200 cursor-pointer"
              >
                <img src={logoBothSrc} alt="" className="w-16 h-16 group-hover:scale-110 transition-transform duration-200" style={{ objectFit: 'contain' }} />
                <span className="text-lg font-bold text-white">{t('playBothSides')}</span>
                <span className="text-sm text-gray-400 text-center">{t('playBothSidesDesc')}</span>
              </button>
              {/* Exercises */}
              <button
                onClick={() => setTab('exercise-library')}
                className="group flex flex-col items-center gap-3 bg-gray-800 hover:bg-gray-750 border border-gray-700 hover:border-amber-600 rounded-xl p-8 transition-all duration-200 cursor-pointer"
              >
                <span className="text-5xl group-hover:scale-110 transition-transform duration-200">📖</span>
                <span className="text-lg font-bold text-white">{t('tabExercises')}</span>
                <span className="text-sm text-gray-400 text-center">{t('exercisesDesc')}</span>
              </button>
              {/* Import & Analyze */}
              <button
                onClick={() => setTab('import-game')}
                className="group flex flex-col items-center gap-3 bg-gray-800 hover:bg-gray-750 border border-gray-700 hover:border-amber-600 rounded-xl p-8 transition-all duration-200 cursor-pointer"
              >
                <span className="text-5xl group-hover:scale-110 transition-transform duration-200">📂</span>
                <span className="text-lg font-bold text-white">{t('tabImport')}</span>
                <span className="text-sm text-gray-400 text-center">{t('importDesc')}</span>
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

        {/* EXERCISE LIBRARY TAB */}
        {tab === 'exercise-library' && (
          <ExerciseLibraryPage
            onSelectBook={() => { resetExerciseState(); setTab('exercises') }}
          />
        )}

        {/* EXERCISES TAB — list only when no exercise active, board shown on selection */}
        {tab === 'exercises' && !exerciseGameState && !lessonOpen && (
          <div className="h-full overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-6">
              <ExercisePanel
                onExerciseLoad={handleExerciseLoad}
                onLessonOpen={(chapter, fen) => setLessonOpen({ chapter, fen })}
                currentExerciseId={null}
                feedback={null}
                compact={false}
                readChapters={readChapters}
              />
            </div>
          </div>
        )}

        {tab === 'exercises' && !exerciseGameState && lessonOpen && (
          <div className="h-full">
            <LessonPanel
              chapter={lessonOpen.chapter}
              exampleFen={lessonOpen.fen}
              onClose={() => setLessonOpen(null)}
              onLessonRead={handleLessonRead}
              isRead={readChapters.has(lessonOpen.chapter)}
            />
          </div>
        )}

        {tab === 'exercises' && exerciseGameState && (
          <div className="h-full flex flex-col items-center px-2 pt-2 lg:px-4 lg:pt-4">
            {/* Board wrapper — overlay shown on success */}
            <div className="relative w-full" style={{ maxWidth: '560px' }}>
              <Board
                board={exerciseGameState.board}
                legalMoves={exerciseLegalMoves}
                onMove={handleExerciseMove}
                selectedSquare={exerciseSelectedSquare}
                onSelectSquare={handleExerciseSelectSquare}
                disabled={exerciseSolved}
                freeSelectSquares={exerciseFreeSelectSquares}
                flipped={exerciseGameState.fen.startsWith('B:')}
              />
              {exerciseSolved && (
                <div
                  className="absolute inset-0 flex flex-col items-center justify-center rounded"
                  style={{ background: 'rgba(0,0,0,0.55)', zIndex: 5 }}
                >
                  <span style={{ fontSize: '5rem', lineHeight: 1 }} className="text-green-400">✓</span>
                  <span className="text-white text-xl font-bold mt-2">{t('wellDone')}</span>
                </div>
              )}
            </div>

            {/* Below-board row: back arrow left, perspective center, loading right */}
            <div className="flex items-center w-full mt-2" style={{ maxWidth: '560px' }}>
              <button
                onClick={resetExerciseState}
                className="text-gray-400 hover:text-amber-500 text-2xl w-9 h-9 flex items-center justify-center rounded-lg hover:bg-gray-700 transition-colors flex-shrink-0"
                title={t('exercises')}
              >
                ←
              </button>
              <p className="flex-1 text-center text-xs text-gray-500">
                {exerciseGameState.fen.startsWith('B:') ? t('blackPerspective') : t('whitePerspective')}
              </p>
              {exerciseMovesLoading && !exerciseFeedback && (
                <div className="flex items-center gap-1 text-xs text-gray-400 flex-shrink-0">
                  <div className="spinner" style={{ width: 12, height: 12 }} />
                </div>
              )}
              {!exerciseMovesLoading && <div className="w-9 flex-shrink-0" />}
            </div>

            {/* Error feedback banner */}
            {exerciseFeedback && !exerciseFeedback.correct && (
              <div className="w-full mt-3 rounded-xl px-4 py-3 text-center bg-red-900 border border-red-600 text-red-200" style={{ maxWidth: '560px' }}>
                <p className="text-lg font-bold">{`✗ ${t('tryAgain')}`}</p>
                <button
                  onClick={() => {
                    setExerciseFeedback(null)
                    setExerciseSolved(false)
                    setExerciseStep(0)
                    setExerciseSelectedSquare(null)
                    setExerciseGameState(prev =>
                      prev ? { ...prev, board: fenToBoard(prev.fen) } : prev
                    )
                  }}
                  className="mt-2 px-4 py-1 rounded-lg bg-red-700 hover:bg-red-600 text-white text-sm font-semibold transition-colors"
                >
                  {t('tryAgain')}
                </button>
              </div>
            )}
          </div>
        )}

        {/* IMPORT & ANALYZE TAB */}
        {tab === 'import-game' && (
          <div className="h-full">
            <ImportGamePanel onClose={() => setTab('home')} />
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
