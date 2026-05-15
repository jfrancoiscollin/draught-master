import React, { useEffect, useState, useCallback, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Board from './Board'
import { getLesson, getExercises, markLessonRead, getPositionLegalMoves, applyPositionMove } from '../api/client'
import { fenToBoard } from '../utils/fen'
import { useAuth } from '../contexts/AuthContext'
import type { MoveData, ExerciseResponse } from '../types'

interface LessonPanelProps {
  chapter: number
  exampleFen: string
  onClose: () => void
  onLessonRead?: (chapter: number) => void
  isRead?: boolean
}

type Token =
  | { kind: 'text'; value: string }
  | { kind: 'square'; sq: number; value: string }
  | { kind: 'diag'; n: number; value: string }

function tokenize(text: string): Token[] {
  const tokens: Token[] = []
  const re = /\(diag\.\s*(\d+)\)|diag\.\s*(\d+)|\b([1-4]?\d|50)\b/g
  let last = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) tokens.push({ kind: 'text', value: text.slice(last, m.index) })
    if (m[1] !== undefined) {
      tokens.push({ kind: 'diag', n: parseInt(m[1]), value: m[0] })
    } else if (m[2] !== undefined) {
      tokens.push({ kind: 'diag', n: parseInt(m[2]), value: m[0] })
    } else {
      const sq = parseInt(m[3])
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
}: {
  text: string
  onSquareClick: (sq: number) => void
  onDiagramClick: (n: number) => void
  highlighted: number[]
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
            code: ({ children }) => <code style={{ background: 'rgba(251,191,36,0.12)', padding: '1px 4px', borderRadius: 3, fontSize: '0.88em' }}>{children}</code>,
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

export default function LessonPanel({ chapter, exampleFen, onClose, onLessonRead, isRead: isReadProp }: LessonPanelProps) {
  const { user } = useAuth()
  type LessonDiagram = string | { fen: string; label: string }
  const [lesson, setLesson] = useState<{ title: string; text: string; diagrams?: LessonDiagram[] } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [exercises, setExercises] = useState<ExerciseResponse[]>([])
  const [activeDiagram, setActiveDiagram] = useState(0)
  const [highlighted, setHighlighted] = useState<number[]>([])
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
    Promise.all([getLesson(chapter), getExercises()])
      .then(([lessonData, allExercises]) => {
        setLesson(lessonData as typeof lesson)
        const chExercises = allExercises.filter(e => e.chapter === chapter)
        setExercises(chExercises)
      })
      .catch(() => setError('Leçon introuvable'))
      .finally(() => setLoading(false))
  }, [chapter])

  const lessonDiagrams = lesson?.diagrams ?? []
  const diagrams: Array<{ label: string; fen: string }> = lessonDiagrams.length > 0
    ? lessonDiagrams.map((d, i) =>
        typeof d === 'string'
          ? { label: `Diag. ${i + 1}`, fen: d }
          : { label: d.label, fen: d.fen }
      )
    : exercises.map((ex, i) => ({ label: `D${i + 1}`, fen: ex.initial_fen }))

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

  // When active diagram changes, reset board
  useEffect(() => {
    const fen = diagrams[activeDiagram]?.fen ?? exampleFen
    resetToInitial(fen)
    setHighlighted([])
  }, [activeDiagram, diagrams.length]) // eslint-disable-line react-hooks/exhaustive-deps

  const board = fenToBoard(currentFen || initialFen)
  // Fix orientation based on the initial diagram FEN — never flip mid-exploration
  const flipped = initialFen.startsWith('B:')

  const handleMove = useCallback(async (move: MoveData) => {
    setSelectedSquare(null)
    try {
      const result = await applyPositionMove(currentFen, move.path)
      setCurrentFen(result.fen)
      setLegalMoves(result.moves)
      setIsDirty(true)
    } catch {
      // Reload legal moves on error
      loadLegalMoves(currentFen)
    }
  }, [currentFen, loadLegalMoves])

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

        {/* Diagram selector buttons + reset */}
        {diagrams.length > 0 && (
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
          {!isDirty && highlighted.length === 0 && (
            <p className="text-xs text-gray-600">
              Déplace les pions · <span className="text-cyan-600">diag.</span> → damier
            </p>
          )}
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
            />
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
          </>
        )}
      </div>
    </div>
  )
}
