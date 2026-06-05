import React, { useEffect, useState, useCallback, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Board from './Board'
import { getLesson, getExercises, markLessonRead, getPositionLegalMoves, applyPositionMove, getManualLesson } from '../api/client'
import { fenToBoard } from '../utils/fen'
import { useAuth } from '../contexts/AuthContext'
import type { MoveData, ExerciseResponse } from '../types'

interface LessonPanelProps {
  chapter: number
  exampleFen: string
  onClose: () => void
  onLessonRead?: (chapter: number) => void
  isRead?: boolean
  // When set, the lesson content comes from a strategic manual
  // (/strategy/manual-lesson?source=…&chapter=…) instead of the Débutant
  // /lessons/{chapter} endpoint. The view is otherwise identical.
  manualSource?: string
  // Optional chapter navigation (strategic manuals): the chapter list passes
  // these to wire ‹ Précédent / Suivant ›.
  onPrev?: () => void
  onNext?: () => void
  navLabel?: string
  // Opens the diagram annotator on the active diagram (exercise books): lets
  // the operator correct a mis-detected position and copy the JSON entry.
  onAnnotateDiagram?: (source: string, page: number, number: number) => void
}

type Token =
  | { kind: 'text'; value: string }
  | { kind: 'square'; sq: number; value: string }
  | { kind: 'diag'; n: number; value: string }
  | { kind: 'movenum'; value: string }

function tokenize(text: string): Token[] {
  const tokens: Token[] = []
  // Order matters: "(diag. N)" / "diag. N" first, then a move number ("12.")
  // — a digit run followed by a dot and whitespace/end, so each numbered move
  // can start on its own line — then a bare playable square (1-50).
  const re = /\(diag\.\s*(\d+)\)|diag\.\s*(\d+)|\b(\d{1,3})\.(?=\s|$)|\b([1-4]?\d|50)\b/g
  let last = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) tokens.push({ kind: 'text', value: text.slice(last, m.index) })
    if (m[1] !== undefined) {
      tokens.push({ kind: 'diag', n: parseInt(m[1]), value: m[0] })
    } else if (m[2] !== undefined) {
      tokens.push({ kind: 'diag', n: parseInt(m[2]), value: m[0] })
    } else if (m[3] !== undefined) {
      tokens.push({ kind: 'movenum', value: m[0] })
    } else {
      const sq = parseInt(m[4])
      if (sq >= 1 && sq <= 50) tokens.push({ kind: 'square', sq, value: m[0] })
      else tokens.push({ kind: 'text', value: m[0] })
    }
    last = m.index + m[0].length
  }
  if (last < text.length) tokens.push({ kind: 'text', value: text.slice(last) })
  return tokens
}

function LessonText({
  text,
  onSquareClick,
  onDiagramClick,
  highlighted,
  onRefClick,
  activeRef,
}: {
  text: string
  onSquareClick: (sq: number) => void
  onDiagramClick: (n: number) => void
  highlighted: number[]
  onRefClick?: (ref: string) => void
  activeRef?: string | null
}) {
  // The legacy plain-text path with clickable square / diagram tokens is kept
  // around for any future content that doesn't use markdown. For manuel
  // chapters (markdown source) we render via react-markdown.
  // Heuristic : treat anything containing a markdown header (## / ### …) or
  // a bold marker as markdown.
  const isMarkdown = /(^|\n)#{1,6}\s|\*\*[^*]+\*\*/.test(text)

  if (isMarkdown) {
    return (
      <div className="lesson-md" style={{ fontSize: '0.92rem', lineHeight: 1.6 }}>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#fbbf24', marginTop: '0.8rem', marginBottom: '0.5rem' }}>{children}</h1>,
            h2: ({ children }) => <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fbbf24', marginTop: '0.8rem', marginBottom: '0.4rem' }}>{children}</h2>,
            h3: ({ children }) => <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fcd34d', marginTop: '0.7rem', marginBottom: '0.3rem' }}>{children}</h3>,
            h4: ({ children }) => <h4 style={{ fontSize: '0.98rem', fontWeight: 700, color: '#fde68a', marginTop: '0.6rem', marginBottom: '0.25rem' }}>{children}</h4>,
            p: ({ children }) => <p style={{ marginBottom: '0.6rem' }}>{children}</p>,
            strong: ({ children }) => <strong style={{ fontWeight: 700, color: '#fbbf24' }}>{children}</strong>,
            em: ({ children }) => <em style={{ fontStyle: 'italic', color: '#e5e7eb' }}>{children}</em>,
            blockquote: ({ children }) => (
              <blockquote style={{ borderLeft: '3px solid #d97706', paddingLeft: '0.75rem', marginLeft: 0, marginBottom: '0.6rem', color: '#d1d5db', fontStyle: 'italic' }}>
                {children}
              </blockquote>
            ),
            code: ({ children }) => {
              const raw = String(children ?? '')
              const isRef = /^BEG_CH\d{2}_\d{3}$/.test(raw)
              if (isRef && onRefClick) {
                const isActive = activeRef === raw
                return (
                  <code
                    onClick={() => onRefClick(raw)}
                    style={{
                      cursor: 'pointer',
                      background: isActive ? 'rgba(34,211,238,0.25)' : 'rgba(34,211,238,0.12)',
                      color: isActive ? '#a5f3fc' : '#67e8f9',
                      border: isActive ? '1px solid #22d3ee' : '1px solid rgba(34,211,238,0.4)',
                      padding: '1px 6px',
                      borderRadius: 4,
                      fontSize: '0.85em',
                      fontWeight: 600,
                      textDecoration: 'none',
                    }}
                    title={`Charger ${raw} sur le damier`}
                  >
                    {raw}
                  </code>
                )
              }
              return <code style={{ background: 'rgba(251,191,36,0.12)', padding: '1px 4px', borderRadius: 3, fontSize: '0.88em' }}>{children}</code>
            },
            ul: ({ children }) => <ul style={{ listStyle: 'disc', paddingLeft: '1.4rem', marginBottom: '0.6rem' }}>{children}</ul>,
            ol: ({ children }) => <ol style={{ listStyle: 'decimal', paddingLeft: '1.4rem', marginBottom: '0.6rem' }}>{children}</ol>,
            li: ({ children }) => <li style={{ marginBottom: '0.2rem' }}>{children}</li>,
            a: ({ children, href }) => <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: '#67e8f9', textDecoration: 'underline' }}>{children}</a>,
            hr: () => <hr style={{ border: 0, borderTop: '1px solid #374151', margin: '1rem 0' }} />,
            table: ({ children }) => <table style={{ borderCollapse: 'collapse', marginBottom: '0.6rem' }}>{children}</table>,
            th: ({ children }) => <th style={{ border: '1px solid #374151', padding: '4px 8px', background: 'rgba(251,191,36,0.08)', fontWeight: 700 }}>{children}</th>,
            td: ({ children }) => <td style={{ border: '1px solid #374151', padding: '4px 8px' }}>{children}</td>,
          }}
        >
          {text}
        </ReactMarkdown>
      </div>
    )
  }

  const tokens = tokenize(text)
  return (
    <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.75, fontSize: '0.92rem' }}>
      {tokens.map((tok, i) => {
        if (tok.kind === 'movenum') {
          // Start each numbered move on its own line so a long score reads as a
          // column (1. … / 2. … / 3. …) instead of one inline block.
          return (
            <React.Fragment key={i}>
              {i > 0 ? '\n' : ''}
              <span style={{ fontWeight: 700, color: '#fcd34d' }}>{tok.value}</span>
            </React.Fragment>
          )
        }
        if (tok.kind === 'square') {
          const isHl = highlighted.includes(tok.sq)
          return (
            <span
              key={i}
              onClick={() => onSquareClick(tok.sq)}
              style={{
                cursor: 'pointer',
                fontWeight: 700,
                color: isHl ? '#f59e0b' : '#fbbf24',
                background: isHl ? 'rgba(245,158,11,0.18)' : 'transparent',
                borderRadius: 3,
                padding: '0 1px',
                textDecoration: 'underline dotted',
              }}
              title={`Case ${tok.sq}`}
            >
              {tok.value}
            </span>
          )
        }
        if (tok.kind === 'diag') {
          return (
            <span
              key={i}
              onClick={() => onDiagramClick(tok.n)}
              style={{
                cursor: 'pointer',
                fontWeight: 700,
                color: '#67e8f9',
                background: 'rgba(103,232,249,0.12)',
                borderRadius: 4,
                padding: '0 3px',
                textDecoration: 'underline dotted',
              }}
              title={`Voir diagramme ${tok.n}`}
            >
              {tok.value}
            </span>
          )
        }
        return <span key={i}>{tok.value}</span>
      })}
    </div>
  )
}

export default function LessonPanel({ chapter, exampleFen, onClose, onLessonRead, isRead: isReadProp, manualSource, onPrev, onNext, navLabel, onAnnotateDiagram }: LessonPanelProps) {
  const { user } = useAuth()
  type LessonSolution = { moves: string[]; fens: string[]; prompt?: string }
  type LessonDiagram = string | { fen: string; label: string; ref?: string; solution?: LessonSolution }
  const [lesson, setLesson] = useState<{ title: string; text: string; diagrams?: LessonDiagram[] } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [exercises, setExercises] = useState<ExerciseResponse[]>([])
  const [activeDiagram, setActiveDiagram] = useState(0)
  const [highlighted, setHighlighted] = useState<number[]>([])
  // Exercise-book solution playback (Goedemoed): reveal + step the winning line.
  const [showSolution, setShowSolution] = useState(false)
  const [solutionPly, setSolutionPly] = useState(0)
  // Exercise SOLVE mode: the user plays the winning move(s); we validate each
  // against the proven line and auto-reply for the opponent. ``solveStep`` is
  // the number of plies already played (points at the next move expected from
  // the user); ``solveStatus`` drives the feedback line.
  const [solveStep, setSolveStep] = useState(0)
  const [solveStatus, setSolveStatus] = useState<'playing' | 'wrong' | 'solved'>('playing')
  const solveTimerRef = useRef<number | null>(null)
  const [isRead, setIsRead] = useState(isReadProp ?? false)
  const [marking, setMarking] = useState(false)

  // Interactive board state
  const [currentFen, setCurrentFen] = useState<string>('')
  const [legalMoves, setLegalMoves] = useState<MoveData[]>([])
  const [selectedSquare, setSelectedSquare] = useState<number | null>(null)
  const [isDirty, setIsDirty] = useState(false) // position changed from initial
  const loadingMovesRef = useRef(false)

  useEffect(() => {
    setIsRead(isReadProp ?? false)
  }, [isReadProp, chapter])

  useEffect(() => {
    setLoading(true)
    setError(null)
    setHighlighted([])
    setActiveDiagram(0)
    if (manualSource) {
      // Strategic manual: lesson-shaped content, no per-chapter exercises.
      getManualLesson(manualSource, chapter)
        .then(data => { setLesson(data as typeof lesson); setExercises([]) })
        .catch(() => setError('Leçon introuvable'))
        .finally(() => setLoading(false))
      return
    }
    Promise.all([getLesson(chapter), getExercises()])
      .then(([lessonData, allExercises]) => {
        setLesson(lessonData as typeof lesson)
        const chExercises = allExercises.filter(e => e.chapter === chapter)
        setExercises(chExercises)
      })
      .catch(() => setError('Leçon introuvable'))
      .finally(() => setLoading(false))
  }, [chapter, manualSource])

  const lessonDiagrams = lesson?.diagrams ?? []
  const diagrams: Array<{ label: string; fen: string; ref?: string; solution?: LessonSolution }> = lessonDiagrams.length > 0
    ? lessonDiagrams.map((d, i) =>
        typeof d === 'string'
          ? { label: `Diag. ${i + 1}`, fen: d }
          : { label: d.label, fen: d.fen, ref: d.ref, solution: d.solution }
      )
    : exercises.map((ex, i) => ({ label: `D${i + 1}`, fen: ex.initial_fen }))

  // When diagrams come from the manuel pipeline they carry a `ref`
  // (BEG_CHnn_mmm) — clicking inline code in the markdown picks one of
  // these, and the legacy D1..Dn selector strip below the board is
  // hidden in favour of a single "current ref" chip.
  const hasRefs = diagrams.some(d => !!d.ref)
  const refIndex = (ref: string) => diagrams.findIndex(d => d.ref === ref)

  const initialFen = diagrams[activeDiagram]?.fen ?? exampleFen

  // Load legal moves whenever currentFen changes
  const loadLegalMoves = useCallback(async (fen: string) => {
    if (!fen || loadingMovesRef.current) return
    loadingMovesRef.current = true
    try {
      const moves = await getPositionLegalMoves(fen)
      setLegalMoves(moves)
    } catch {
      setLegalMoves([])
    } finally {
      loadingMovesRef.current = false
    }
  }, [])

  // Reset board to initial diagram FEN
  const resetToInitial = useCallback((fen: string) => {
    setCurrentFen(fen)
    setSelectedSquare(null)
    setIsDirty(false)
    loadLegalMoves(fen)
  }, [loadLegalMoves])

  // When active diagram changes, reset board (and hide any revealed solution)
  useEffect(() => {
    const fen = diagrams[activeDiagram]?.fen ?? exampleFen
    resetToInitial(fen)
    setHighlighted([])
    setShowSolution(false)
    setSolutionPly(0)
    setSolveStep(0)
    setSolveStatus('playing')
    if (solveTimerRef.current) { window.clearTimeout(solveTimerRef.current); solveTimerRef.current = null }
  }, [activeDiagram, diagrams.length]) // eslint-disable-line react-hooks/exhaustive-deps

  // Clear any pending opponent-reply timer when the panel unmounts.
  useEffect(() => () => {
    if (solveTimerRef.current) window.clearTimeout(solveTimerRef.current)
  }, [])

  // Jump the board to a given ply of the active diagram's solution line.
  const activeSolution = diagrams[activeDiagram]?.solution
  const goToSolutionPly = useCallback((ply: number) => {
    const sol = diagrams[activeDiagram]?.solution
    if (!sol) return
    const p = Math.max(0, Math.min(ply, sol.fens.length - 1))
    setSolutionPly(p)
    setHighlighted([])
    resetToInitial(sol.fens[p])
  }, [diagrams, activeDiagram, resetToInitial])

  const board = fenToBoard(currentFen || initialFen)
  // Fix orientation based on the initial diagram FEN — never flip mid-exploration
  const flipped = initialFen.startsWith('B:')

  // Restart the current exercise from its starting position.
  const restartSolve = useCallback(() => {
    const sol = diagrams[activeDiagram]?.solution
    if (solveTimerRef.current) { window.clearTimeout(solveTimerRef.current); solveTimerRef.current = null }
    setSolveStep(0)
    setSolveStatus('playing')
    setHighlighted([])
    if (sol) resetToInitial(sol.fens[0])
  }, [diagrams, activeDiagram, resetToInitial])

  const handleMove = useCallback(async (move: MoveData) => {
    setSelectedSquare(null)
    const sol = diagrams[activeDiagram]?.solution
    // ── Exercise solve mode: validate the move against the proven line ──
    if (sol && !showSolution && solveStatus !== 'solved') {
      const expected = sol.moves[solveStep]
      const expPath = expected.split(/[-x]/).filter(Boolean).map(Number)
      const correct = move.path.length === expPath.length
        && move.path.every((v, i) => v === expPath[i])
      if (!correct) {
        setSolveStatus('wrong')
        loadLegalMoves(sol.fens[solveStep]) // stay on the position, let them retry
        return
      }
      // Correct move from the user → show the resulting position.
      const afterUser = solveStep + 1
      setCurrentFen(sol.fens[afterUser])
      setHighlighted([])
      if (afterUser >= sol.moves.length) {
        setSolveStep(afterUser); setSolveStatus('solved'); setLegalMoves([]); return
      }
      // Opponent's reply is forced — play it after a short beat.
      setSolveStep(afterUser); setSolveStatus('playing'); setLegalMoves([])
      solveTimerRef.current = window.setTimeout(() => {
        solveTimerRef.current = null
        const afterReply = afterUser + 1
        setCurrentFen(sol.fens[afterReply])
        setSolveStep(afterReply)
        if (afterReply >= sol.moves.length) { setSolveStatus('solved'); setLegalMoves([]) }
        else { setSolveStatus('playing'); loadLegalMoves(sol.fens[afterReply]) }
      }, 550)
      return
    }
    // ── Free exploration (non-exercise diagrams / Débutant lessons) ──
    try {
      const result = await applyPositionMove(currentFen, move.path)
      setCurrentFen(result.fen)
      setLegalMoves(result.moves)
      setIsDirty(true)
    } catch {
      // Reload legal moves on error
      loadLegalMoves(currentFen)
    }
  }, [diagrams, activeDiagram, showSolution, solveStatus, solveStep, currentFen, loadLegalMoves])

  const handleSquareClick = useCallback((sq: number) => {
    setHighlighted(prev => prev.includes(sq) ? prev.filter(s => s !== sq) : [...prev, sq])
  }, [])

  const handleDiagramClick = useCallback((n: number) => {
    const idx = n - 1
    if (idx >= 0 && idx < diagrams.length) {
      setActiveDiagram(idx)
      setHighlighted([])
    }
  }, [diagrams])

  const handleMarkRead = useCallback(async () => {
    if (!user || isRead || marking) return
    setMarking(true)
    try {
      await markLessonRead(chapter)
      setIsRead(true)
      onLessonRead?.(chapter)
    } finally {
      setMarking(false)
    }
  }, [user, isRead, marking, chapter, onLessonRead])

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 bg-gray-800 border-b border-gray-700 flex-shrink-0">
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-amber-500 text-2xl w-9 h-9 flex items-center justify-center rounded-lg hover:bg-gray-700 transition-colors"
        >
          ←
        </button>
        <h2 className="font-bold text-amber-500 text-base leading-tight flex-1 min-w-0 truncate">
          {lesson?.title ?? `Chapitre ${chapter}`}
        </h2>
      </div>

      {/* Board — fixed below header */}
      <div className="flex-shrink-0 flex flex-col items-center py-3 bg-gray-900 border-b border-gray-700">
        <div style={{ width: '100%', maxWidth: 240 }}>
          <Board
            board={board}
            legalMoves={legalMoves}
            onMove={handleMove}
            selectedSquare={selectedSquare}
            onSelectSquare={setSelectedSquare}
            disabled={false}
            highlightSquares={highlighted}
            flipped={flipped}
          />
        </div>

        {/* Diagram selector — single ref chip for manuel lessons,
            multi-button strip for legacy lessons. */}
        {diagrams.length > 0 && hasRefs && (
          <div className="flex items-center justify-center mt-2 px-2">
            <span
              className="px-3 py-0.5 text-xs rounded border bg-cyan-900/40 border-cyan-600 text-cyan-200 font-mono"
              title="Référence active — cliquer une autre référence dans le texte pour changer"
            >
              {diagrams[activeDiagram]?.ref ?? diagrams[activeDiagram]?.label}
            </span>
          </div>
        )}
        {diagrams.length > 0 && !hasRefs && (
          <div className="flex items-center gap-1 mt-2 px-2 flex-wrap justify-center">
            {diagrams.map((d, idx) => {
              const isActive = activeDiagram === idx
              return (
                <button
                  key={idx}
                  onClick={() => { setActiveDiagram(idx); setHighlighted([]) }}
                  className={`px-2 py-0.5 text-xs rounded border cursor-pointer ${
                    isActive
                      ? 'bg-cyan-700 border-cyan-500 text-white font-bold'
                      : 'bg-gray-800 border-gray-600 text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {d.label}
                </button>
              )
            })}
          </div>
        )}

        {/* Exercise — solve mode: play the move, get feedback; reveal as help. */}
        {activeSolution && (
          <div className="mt-2 px-2">
            <div className="text-center text-xs font-semibold mb-1">
              <span className="text-amber-300">⚑ {activeSolution.prompt ?? 'À vous de jouer'}</span>
            </div>
            {!showSolution && (
              <div className="text-center text-xs mb-1.5">
                {solveStatus === 'solved' ? (
                  <span className="text-emerald-400 font-bold">🎉 Bien joué ! Combinaison trouvée.</span>
                ) : solveStatus === 'wrong' ? (
                  <span className="text-red-400">✗ Ce n'est pas le meilleur coup — réessayez.</span>
                ) : solveStep > 0 ? (
                  <span className="text-emerald-400">✓ Bon coup ! Continuez…</span>
                ) : (
                  <span className="text-gray-400">Jouez le meilleur coup sur le damier.</span>
                )}
              </div>
            )}
            <div className="flex items-center justify-center gap-2 flex-wrap">
              {!showSolution && (solveStep > 0 || solveStatus !== 'playing') && (
                <button
                  onClick={restartSolve}
                  className="px-2 py-0.5 text-xs rounded border border-gray-600 text-gray-300 hover:bg-gray-700 cursor-pointer"
                >
                  ↺ Recommencer
                </button>
              )}
              <button
                onClick={() => {
                  if (showSolution) { setShowSolution(false); restartSolve() }
                  else { setShowSolution(true) }
                }}
                className="px-2 py-0.5 text-xs rounded border border-emerald-600 text-emerald-300 hover:bg-emerald-900/40 cursor-pointer"
              >
                {showSolution ? 'Cacher la solution' : 'Voir la solution'}
              </button>
            </div>
            {showSolution && (
              <div className="mt-2">
                <div className="flex items-center justify-center gap-2 mb-1.5">
                  <button
                    disabled={solutionPly <= 0}
                    onClick={() => goToSolutionPly(solutionPly - 1)}
                    className="px-2 py-0.5 text-xs rounded border border-gray-600 text-gray-300 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-default cursor-pointer"
                  >
                    ‹
                  </button>
                  <span className="text-xs text-gray-400 font-mono">
                    {solutionPly} / {activeSolution.fens.length - 1}
                  </span>
                  <button
                    disabled={solutionPly >= activeSolution.fens.length - 1}
                    onClick={() => goToSolutionPly(solutionPly + 1)}
                    className="px-2 py-0.5 text-xs rounded border border-gray-600 text-gray-300 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-default cursor-pointer"
                  >
                    ›
                  </button>
                </div>
                <div className="flex flex-wrap justify-center gap-1">
                  {activeSolution.moves.map((mv, i) => {
                    const isActive = solutionPly === i + 1
                    return (
                      <button
                        key={i}
                        onClick={() => goToSolutionPly(i + 1)}
                        className={`px-2 py-0.5 text-xs rounded border font-mono cursor-pointer ${
                          isActive
                            ? 'bg-emerald-700 border-emerald-500 text-white font-bold'
                            : 'bg-gray-800 border-gray-600 text-gray-300 hover:text-white'
                        }`}
                      >
                        {i + 1}. {mv}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="flex items-center gap-3 mt-1.5 flex-wrap justify-center">
          {isDirty && (
            <button
              onClick={() => resetToInitial(initialFen)}
              className="text-xs text-amber-500 hover:text-amber-300 underline cursor-pointer"
            >
              ↺ Réinitialiser
            </button>
          )}
          {highlighted.length > 0 && (
            <button
              onClick={() => setHighlighted([])}
              className="text-xs text-gray-500 hover:text-gray-300 underline cursor-pointer"
            >
              Effacer sélection
            </button>
          )}
          {!isDirty && highlighted.length === 0 && !activeSolution && (
            <p className="text-xs text-gray-600">
              Déplace les pions · <span className="text-cyan-600">diag.</span> → damier
            </p>
          )}
          {onAnnotateDiagram && (() => {
            // Active diagram ref is "SOURCE_pP_dN" — offer to correct it.
            const m = /^(.+)_p(\d+)_d(\d+)$/.exec(diagrams[activeDiagram]?.ref ?? '')
            if (!m) return null
            return (
              <button
                onClick={() => onAnnotateDiagram(m[1], parseInt(m[2], 10), parseInt(m[3], 10))}
                className="text-xs text-emerald-500 hover:text-emerald-300 underline cursor-pointer"
                title="Corriger la position détectée et copier l'entrée JSON"
              >
                ✎ Corriger la position
              </button>
            )
          })()}
        </div>
      </div>

      {/* Lesson text — scrollable */}
      <div className="flex-1 overflow-y-auto overscroll-contain px-4 py-4">
        {loading && (
          <div className="flex justify-center py-12">
            <div className="spinner" style={{ width: 28, height: 28 }} />
          </div>
        )}
        {error && <p className="text-red-400 text-sm py-6 text-center">{error}</p>}
        {lesson && !loading && (
          <>
            <LessonText
              text={lesson.text}
              onSquareClick={handleSquareClick}
              onDiagramClick={handleDiagramClick}
              highlighted={highlighted}
              onRefClick={hasRefs ? (ref => {
                const idx = refIndex(ref)
                if (idx >= 0) { setActiveDiagram(idx); setHighlighted([]) }
              }) : undefined}
              activeRef={hasRefs ? (diagrams[activeDiagram]?.ref ?? null) : null}
            />
            {!manualSource && (
              <div className="mt-6 mb-2 flex justify-center">
                {user && (
                  isRead ? (
                    <span className="flex items-center gap-2 text-green-400 font-semibold text-sm px-4 py-2 rounded-lg bg-green-900/30 border border-green-700">
                      <span className="text-base">✓</span> Leçon lue
                    </span>
                  ) : (
                    <button
                      onClick={handleMarkRead}
                      disabled={marking}
                      className="flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-lg border border-amber-600 text-amber-400 hover:bg-amber-900/40 transition-colors disabled:opacity-50 cursor-pointer"
                    >
                      {marking ? '...' : '✓ Marquer comme lue'}
                    </button>
                  )
                )}
              </div>
            )}
            {manualSource && (onPrev || onNext) && (
              <div className="mt-6 mb-2 flex items-center justify-between gap-3">
                <button
                  onClick={onPrev}
                  disabled={!onPrev}
                  className="px-3 py-2 rounded-lg text-sm border border-gray-600 text-gray-300 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-default cursor-pointer"
                >
                  ‹ Précédent
                </button>
                {navLabel && <span className="text-xs text-gray-500">{navLabel}</span>}
                <button
                  onClick={onNext}
                  disabled={!onNext}
                  className="px-3 py-2 rounded-lg text-sm border border-gray-600 text-gray-300 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-default cursor-pointer"
                >
                  Suivant ›
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
