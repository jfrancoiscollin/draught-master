import React, { useState, useCallback } from 'react'
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
  makeMove,
  analyzePosition,
  checkExercise,
  undoMove,
  resignGame,
  getAiMove,
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
import { playMoveSound } from './utils/sound'

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

type Tab = 'home' | 'play' | 'exercises' | 'history'
type NavTab = Exclude<Tab, 'home'>

const TAB_ICONS: Record<NavTab, string> = {
  play: '♟',
  exercises: '✏️',
  history: '📋',
}

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
  const [spokenSquares, setSpokenSquares] = useState<number[]>([])
  const [showControls, setShowControls] = useState(false)
  const [analysisExpanded, setAnalysisExpanded] = useState(false)
  const [fullSpeaking, setFullSpeaking] = useState(false)

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
      setMoveHistory([])
      setAnalysis(null)
      setAnalysisExpanded(false)
    } catch {
      showToast(t('errorCreatingGame'))
    } finally {
      setIsAiThinking(false)
    }
  }, [aiDepth, t])

  const handleGoToPlay = useCallback(() => {
    setTab('play')
    if (!gameState) startNewGame()
  }, [gameState, startNewGame])

  const handleSelectSquare = useCallback((sq: number | null) => {
    if (!gameState || gameState.result) return
    if (gameState.turn !== 'white') return
    setSelectedSquare(sq)
  }, [gameState])

  const handleMove = useCallback(async (move: MoveData) => {
    if (!gameState || gameState.result || isAiThinking) return
    setSelectedSquare(null)
    setIsAiThinking(true)

    // Optimistic update: show player's move immediately
    playMoveSound()
    const optimisticBoard = applyMoveLocally(gameState.board, move)
    setGameState(prev => prev ? { ...prev, board: optimisticBoard, turn: 'black', last_move: move, legal_moves: [] } : prev)

    try {
      const response = await makeMove(gameState.game_id, move, aiDepth)
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
  }, [gameState, aiDepth, isAiThinking])

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

  const handleAnalyze = useCallback(async (question?: string): Promise<AnalysisResponse | null> => {
    if (!gameState) return null
    setAnalysisLoading(true)
    try {
      const result = await analyzePosition(gameState.game_id, question, language)
      setAnalysis(result)
      setAnalysisExpanded(true)
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

  const navTabs: [NavTab, string][] = [
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
            <h1 className="text-xl font-bold text-amber-600">♟ AI-Draught</h1>
            {tab !== 'home' && (
              <button
                onClick={() => setTab('home')}
                className="text-gray-400 hover:text-amber-500 text-lg w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-700 transition-colors"
                title={t('home')}
              >
                🏠
              </button>
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

      {/* Top tabs — desktop only, hidden on home screen */}
      {tab !== 'home' && (
        <div className="hidden lg:block bg-gray-800 border-b border-gray-700">
          <div className="max-w-7xl mx-auto px-4 flex gap-0">
            {navTabs.map(([key, label]) => (
              <button
                key={key}
                onClick={() => key === 'play' ? handleGoToPlay() : setTab(key)}
                className={`tab-btn ${tab === key ? 'tab-active' : 'tab-inactive'}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main content — mobile: no page scroll (each section scrolls itself); desktop: page scrolls */}
      <main className="flex-1 overflow-hidden lg:overflow-y-auto">

        {/* HOME SCREEN */}
        {tab === 'home' && (
          <div className="h-full flex flex-col items-center justify-center px-4 py-8 overflow-y-auto">
            <p className="text-gray-400 text-sm mb-10 text-center">{t('appSubtitle')}</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-2xl">
              {/* Play */}
              <button
                onClick={handleGoToPlay}
                className="group flex flex-col items-center gap-3 bg-gray-800 hover:bg-gray-750 border border-gray-700 hover:border-amber-600 rounded-xl p-8 transition-all duration-200 cursor-pointer"
              >
                <span className="text-5xl group-hover:scale-110 transition-transform duration-200">♟</span>
                <span className="text-lg font-bold text-white">{t('tabPlay')}</span>
                <span className="text-sm text-gray-400 text-center">{t('playDesc')}</span>
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
                      />
                    </div>
                    <div
                      style={{ gridColumn: '2', gridRow: '1', width: 'min(42vw, 200px)' }}
                      className="flex flex-col items-center"
                    >
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
                    </div>
                  </div>
                  {/* Bottom (scrollable): full analysis text + move list */}
                  <div className="flex-1 overflow-y-auto overscroll-contain pb-20 px-2 pt-2 flex flex-col gap-2">
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
                        <p className="text-gray-200 leading-relaxed whitespace-pre-wrap text-sm">{analysis.analysis}</p>
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
                  </div>
                  {/* Scrollable right panel */}
                  <div className="flex-1 overflow-y-auto overscroll-contain pb-20 min-w-0">
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
                    <p className="text-gray-200 leading-relaxed whitespace-pre-wrap text-sm">{analysis.analysis}</p>
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

      {/* Bottom navigation — mobile only, hidden on home screen */}
      {tab !== 'home' && (
        <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-gray-800 border-t border-gray-700 z-40">
          <div className="flex">
            {navTabs.map(([key, label]) => (
              <button
                key={key}
                onClick={() => key === 'play' ? handleGoToPlay() : setTab(key)}
                className={`flex-1 flex flex-col items-center justify-center py-3 gap-0.5 transition-colors ${
                  tab === key ? 'text-amber-600' : 'text-gray-400 active:text-gray-200'
                }`}
              >
                <span className="text-xl leading-none">{TAB_ICONS[key]}</span>
                <span className="text-xs font-medium">{label}</span>
                {tab === key && (
                  <span className="absolute bottom-0 w-1/3 h-0.5 bg-amber-600 rounded-t" />
                )}
              </button>
            ))}
          </div>
        </nav>
      )}
    </div>
  )
}
