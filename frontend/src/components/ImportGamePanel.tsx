import React, { useState, useEffect, useCallback, useRef } from 'react'
import Board from './Board'
import AnalysisPanel from './AnalysisPanel'
import ScanBar from './ScanBar'
import LearnFromMistakes from './LearnFromMistakes'
import { useScanEngine } from '../hooks/useScanEngine'
import { getScanEngine } from '../lib/scanEngine'
import type { Arrow } from './Board'
import {
  importPdn, getPositionLegalMoves, applyPositionMove,
  analyzePositionFen, getPositionBestMove, precomputePositions,
  getGameAnalysis, analyzeGamePedagogy,
} from '../api/client'
import type { PdnPosition, PdnImportResult, PedagogyAnalysis } from '../api/client'
import PedagogyPanel, {
  AccuracySummary, GameHeatmap, MaterialTimeline, MovesTable, MoveRow, WeaknessGantt,
} from './PedagogyPanel'
import GameNarrativeSummary from './GameNarrativeSummary'
import { fenToBoard } from '../utils/fen'
import { useLanguage } from '../i18n/LanguageContext'
import type { MoveData, AnalysisResponse } from '../types'
import {
  annotateGame, computeStats,
  type MoveAnnotation, type GameStats,
  VERDICT_SYMBOL, VERDICT_COLOR,
} from '../lib/gameAnnotations'

interface ImportGamePanelProps {
  onClose: () => void
  initialPdn?: string | null
  initialGameId?: string | null
  initialUserSide?: 'white' | 'black' | null
  /** Open the MotifDetailPage drill view. Wired from App.tsx, used
   *  by the recommended-drills chips of the narrative cards. */
  onMotifClick?: (slug: string) => void
  /** Open the manuel chapter `chapter` as a full-area overlay. Wired
   *  from App.tsx (the lesson view is global so the user keeps their
   *  ImportGamePanel state while reading). */
  onOpenLesson?: (chapter: number) => void
}

type PanelMode = 'review' | 'learn'

// ── Phase + formations ────────────────────────────────────────────────────
// Mirrors dilf/pedagogy/features/formations.py:KNOWN_FORMATIONS. The slugs
// must stay byte-identical with the dilf registry — drift means the badge
// won't render, click-highlight won't work.

const PHASE_FR: Record<'opening' | 'middlegame' | 'endgame', string> = {
  opening: 'ouverture',
  middlegame: 'milieu de jeu',
  endgame: 'finale',
}

const FORMATION_SQUARES: Record<string, number[]> = {
  classique_blancs:   [32, 37, 41],
  classique_noirs:    [10, 14, 19],
  roozenburg_blancs:  [28, 32, 37],
  roozenburg_noirs:   [14, 19, 23],
  ghestem_blancs:     [27, 32, 38],
}

function prettyFormation(slug: string): { name: string; side: '⬜' | '⬛' | null } {
  const isWhite = slug.endsWith('_blancs')
  const isBlack = slug.endsWith('_noirs')
  const stem = slug.replace(/_(blancs|noirs)$/, '')
  const name = stem.charAt(0).toUpperCase() + stem.slice(1)
  return { name, side: isWhite ? '⬜' : isBlack ? '⬛' : null }
}

// ── Position diagnostic ───────────────────────────────────────────────────
// Four geometric weakness families surfaced from dilf's features_after.
// One row per family, two clickable counts (white / black) per row; the
// active count drives the board's highlightSquares overlay.

type VerdictForDiag = {
  isolated_pawns_white: number[]; isolated_pawns_black: number[]
  backward_pawns_white: number[]; backward_pawns_black: number[]
  holes_white: number[]; holes_black: number[]
  outposts_white: number[]; outposts_black: number[]
}

// Per-row colour matches the corner dot painted by Board.tsx — same
// palette in both places. Keep it that way so the diagnostic grid acts
// as the live legend.
const DIAG_ROWS: ReadonlyArray<{
  label: string; hint: string; color: string
  keys: readonly [string, string]
  pick: (v: VerdictForDiag) => readonly [number[], number[]]
}> = [
  { label: 'Isolés',  color: '#06b6d4', hint: 'Pions sans soutien diagonal (côtés vulnérables)',
    keys: ['iso-w', 'iso-b'], pick: v => [v.isolated_pawns_white, v.isolated_pawns_black] },
  { label: 'Retardés', color: '#f59e0b', hint: 'Pions de la rangée de base privés d\'avance soutenue',
    keys: ['ret-w', 'ret-b'], pick: v => [v.backward_pawns_white, v.backward_pawns_black] },
  { label: 'Trous',   color: '#a855f7', hint: 'Cases vides cernées de pièces amies — faiblesses géométriques',
    keys: ['tro-w', 'tro-b'], pick: v => [v.holes_white, v.holes_black] },
  { label: 'Postes',  color: '#22c55e', hint: 'Cases avancées, soutenues, à l\'abri d\'une simple prise',
    keys: ['pos-w', 'pos-b'], pick: v => [v.outposts_white, v.outposts_black] },
]

function PositionDiagnostic({
  verdict, activeKey, onToggle,
}: {
  verdict: VerdictForDiag
  activeKey: string | null
  onToggle: (key: string) => void
}) {
  return (
    <div className="grid grid-cols-[auto_repeat(2,1fr)] gap-x-1.5 gap-y-0.5 text-xs">
      {DIAG_ROWS.map(row => {
        const [w, b] = row.pick(verdict)
        const [kw, kb] = row.keys
        return (
          <React.Fragment key={row.label}>
            <span className="text-gray-500 flex items-center gap-1" title={row.hint}>
              <span
                aria-hidden="true"
                style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: row.color, flexShrink: 0,
                  boxShadow: '0 0 1px rgba(0,0,0,0.5)',
                }}
              />
              {row.label}
            </span>
            {[
              { sqs: w, key: kw, side: '⬜' as const },
              { sqs: b, key: kb, side: '⬛' as const },
            ].map(({ sqs, key, side }) => {
              const active = activeKey === key
              const disabled = sqs.length === 0
              return (
                <button
                  key={key}
                  disabled={disabled}
                  onClick={() => onToggle(key)}
                  className={
                    'px-1 rounded text-left font-mono tabular-nums transition-colors ' +
                    (disabled
                      ? 'text-gray-700 cursor-default'
                      : active
                      ? 'bg-amber-600/40 text-amber-200 cursor-pointer'
                      : 'text-gray-300 hover:bg-gray-700/60 cursor-pointer')
                  }
                  title={disabled ? '—' : `${sqs.length} case(s) : ${sqs.join(', ')}`}
                >
                  {side} {sqs.length}
                </button>
              )
            })}
          </React.Fragment>
        )
      })}
    </div>
  )
}

// ── Pedagogy tabs ─────────────────────────────────────────────────────────
// Three-tab container surfaced once dilf analysis is ready: Position
// (current half-move's pedagogy summary + diagnostic grid + matching
// move row), Heatmap & Gantt (cumulative game-wide visualisations),
// Tables des positions (per-side accuracy bars + filter + full move
// list). Replaces the single PedagogyPanel that used to dump
// everything in one scroll.

type TabKey = 'position' | 'graphs' | 'tables'

function PedagogyTabsPanel({
  gameId, analysis, userSide, lang, activeVerdict, hangingSquares,
  threatCount, showThreats, onToggleThreats, diagKey, onDiagKey,
  currentHalfMove, onJumpTo, onWeaknessClick, onMotifJump, onMotifClick, onOpenLesson,
}: {
  gameId: string
  analysis: PedagogyAnalysis
  userSide: 'white' | 'black'
  lang: string
  activeVerdict: VerdictForDiag & {
    phase: 'opening' | 'middlegame' | 'endgame'
    material_balance: number | null
    formations: string[]
    move_number: number
  } | null
  hangingSquares: number[]
  threatCount: number
  showThreats: boolean
  onToggleThreats: () => void
  diagKey: string | null
  onDiagKey: (k: string) => void
  currentHalfMove: number
  onJumpTo: (hm: number) => void
  /** Called when the user clicks a persistent-weakness row in the
   *  narrative cards. Squares are highlighted on the board until the
   *  user navigates or clicks another diagnostic row. */
  onWeaknessClick?: (squares: number[]) => void
  /** Called when the user clicks a played/missed motif chip in the
   *  narrative cards. Jumps the board to the first verdict that fired
   *  that motif. */
  onMotifJump?: (slug: string) => void
  /** Open the MotifDetailPage drill view. Wired by App.tsx —
   *  used by the recommended-drills chips ("À travailler"). */
  onMotifClick?: (slug: string) => void
  /** Open a manuel chapter as a global lesson overlay. Wired by
   *  App.tsx; PedagogyTabsPanel just forwards it to the narrative. */
  onOpenLesson?: (chapter: number) => void
}) {
  const [tab, setTab] = useState<TabKey>('position')
  const { verdicts } = analysis
  const activeRow = activeVerdict
    ? verdicts.find(v => v.move_number === activeVerdict.move_number) ?? null
    : null

  const tabs: ReadonlyArray<{ key: TabKey; label: string }> = [
    { key: 'position', label: 'Position' },
    { key: 'graphs',   label: 'Heatmap & Gantt' },
    { key: 'tables',   label: 'Table des positions' },
  ]

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl flex flex-col overflow-hidden">
      <div className="flex border-b border-gray-700">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={
              'flex-1 py-1.5 text-xs font-medium transition-colors ' +
              (tab === t.key
                ? 'bg-gray-700 text-amber-300'
                : 'text-gray-400 hover:text-gray-200 cursor-pointer')
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="p-3 flex flex-col gap-2">
        {tab === 'position' && (
          <>
            {/* Global game narrative cards (dilf.profile.narrate_game).
                Surfaced ABOVE the per-position overlay AND outside the
                activeVerdict gate — the résumé is global, so it makes
                sense at currentIdx=0 (initial position, no move played
                yet) too. */}
            <GameNarrativeSummary
              gameId={gameId}
              lang={lang}
              onJumpTo={onJumpTo}
              onMotifJump={onMotifJump}
              onMotifClick={onMotifClick}
              onWeaknessClick={onWeaknessClick}
              onOpenLesson={onOpenLesson}
            />

            {activeVerdict ? (
              <>
                <div className="flex items-center gap-3 flex-wrap text-xs text-gray-400">
                  <span title={`Phase : ${PHASE_FR[activeVerdict.phase]}`}>
                    <span className="text-gray-600">Phase </span>
                    <span className="font-semibold text-indigo-300">{PHASE_FR[activeVerdict.phase]}</span>
                  </span>
                {activeVerdict.material_balance !== null && (
                  <span title="Solde matériel (dames = 3 pions), point de vue blancs">
                    <span className="text-gray-600">Matériel </span>
                    <span
                      className={
                        activeVerdict.material_balance > 0
                          ? 'font-mono font-bold text-green-400'
                          : activeVerdict.material_balance < 0
                          ? 'font-mono font-bold text-red-400'
                          : 'font-mono font-bold text-gray-400'
                      }
                    >
                      {activeVerdict.material_balance > 0 ? '+' : ''}{activeVerdict.material_balance}
                    </span>
                  </span>
                )}
                {hangingSquares.length > 0 && (
                  <span className="font-bold text-red-400" title="Pièces capturables au coup suivant">
                    ⚠ {hangingSquares.length} pièce{hangingSquares.length > 1 ? 's' : ''} en l'air
                  </span>
                )}
                {threatCount > 0 && (
                  <button
                    onClick={onToggleThreats}
                    className={
                      'px-1.5 py-0.5 rounded text-xs transition-colors ' +
                      (showThreats
                        ? 'bg-red-600/40 text-red-200 cursor-pointer'
                        : 'bg-gray-800 text-gray-300 hover:bg-gray-700 cursor-pointer')
                    }
                  >
                    {showThreats ? '✓ ' : ''}Menaces {threatCount}
                  </button>
                )}
              </div>
              {activeVerdict.formations.length > 0 && (
                <div className="flex items-center gap-1 flex-wrap text-xs">
                  <span className="text-gray-600">Formations</span>
                  {activeVerdict.formations.map(slug => {
                    const { name, side } = prettyFormation(slug)
                    const active = diagKey === slug
                    const clickable = (FORMATION_SQUARES[slug] ?? []).length > 0
                    return (
                      <button
                        key={slug}
                        disabled={!clickable}
                        onClick={() => onDiagKey(slug)}
                        className={
                          'px-1.5 py-0.5 rounded transition-colors ' +
                          (active
                            ? 'bg-amber-600/40 text-amber-200 cursor-pointer'
                            : clickable
                            ? 'bg-gray-800 text-gray-300 hover:bg-gray-700 cursor-pointer'
                            : 'bg-gray-800/40 text-gray-500 cursor-default')
                        }
                      >
                        {side} {name}
                      </button>
                    )
                  })}
                </div>
              )}
              <PositionDiagnostic
                verdict={activeVerdict}
                activeKey={diagKey}
                onToggle={onDiagKey}
              />
              {activeRow && (
                <div className="border-t border-gray-700 pt-2 mt-1">
                  <span className="text-xs text-gray-600 mb-1 block">Coup correspondant</span>
                  <MoveRow
                    verdict={activeRow}
                    gameId={gameId}
                    lang={lang}
                    isActive={true}
                    onJump={onJumpTo}
                  />
                </div>
              )}
            </>
            ) : (
              <p className="text-xs text-gray-500 italic">
                Détails par coup : utilise les flèches pour avancer dans la partie.
              </p>
            )}
          </>
        )}

        {tab === 'graphs' && (
          <>
            <MaterialTimeline
              verdicts={verdicts}
              currentHalfMove={currentHalfMove}
              onJumpTo={onJumpTo}
            />
            <GameHeatmap verdicts={verdicts} userSide={userSide} />
            <WeaknessGantt verdicts={verdicts} userSide={userSide} />
          </>
        )}

        {tab === 'tables' && (
          <>
            <AccuracySummary verdicts={verdicts} userSide={userSide} />
            <MovesTable
              verdicts={verdicts}
              gameId={gameId}
              lang={lang}
              currentHalfMove={currentHalfMove}
              onJumpTo={onJumpTo}
            />
          </>
        )}
      </div>
    </div>
  )
}

export default function ImportGamePanel({
  onClose,
  initialPdn,
  initialGameId,
  initialUserSide,
  onMotifClick,
  onOpenLesson,
}: ImportGamePanelProps) {
  const { language } = useLanguage()

  // ── Import phase ──────────────────────────────────────────────
  const [pdn, setPdn] = useState('')
  const [importing, setImporting] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)
  const [result, setResult] = useState<PdnImportResult | null>(null)

  // Auto-load a PDN passed in by the caller (e.g. from GameHistory click)
  useEffect(() => {
    if (!initialPdn || result) return
    setPdn(initialPdn)
    setImportError(null)
    setImporting(true)
    importPdn(initialPdn)
      .then(data => {
        setResult(data)
        setCurrentIdx(0)
        if (data.positions.length > 0) {
          setCurrentFen(data.positions[0].fen)
          loadLegalMoves(data.positions[0].fen)
        }
      })
      .catch((err: unknown) => {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        setImportError(detail ?? 'Erreur lors de l\'import')
      })
      .finally(() => setImporting(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialPdn])

  // ── Pedagogy analysis (dilf) for a game loaded from history ────
  const [pedagogyAnalysis, setPedagogyAnalysis] = useState<PedagogyAnalysis | null>(null)
  const [pedagogyLoading, setPedagogyLoading] = useState(false)
  const [pedagogyError, setPedagogyError] = useState<string | null>(null)

  // On mount with initialGameId, fetch any persisted dilf analysis.
  // 404 is normal (game never analysed) and we leave the panel empty so
  // the "Analyser" button shows.
  useEffect(() => {
    if (!initialGameId) {
      setPedagogyAnalysis(null)
      return
    }
    setPedagogyLoading(true)
    setPedagogyError(null)
    getGameAnalysis(initialGameId)
      .then(data => setPedagogyAnalysis(data))
      .catch((err: unknown) => {
        const status = (err as { response?: { status?: number } })?.response?.status
        if (status !== 404) {
          setPedagogyError(String((err as { message?: string })?.message ?? err))
        }
        setPedagogyAnalysis(null)
      })
      .finally(() => setPedagogyLoading(false))
  }, [initialGameId])

  const handleAnalyzePedagogy = useCallback(async () => {
    if (!initialGameId) return
    setPedagogyLoading(true)
    setPedagogyError(null)
    try {
      const data = await analyzeGamePedagogy(
        initialGameId,
        initialUserSide ?? 'white',
        language,
      )
      setPedagogyAnalysis(data)
    } catch (err: unknown) {
      setPedagogyError(String((err as { message?: string })?.message ?? err))
    } finally {
      setPedagogyLoading(false)
    }
  }, [initialGameId, initialUserSide, language])

  // ── Review phase ──────────────────────────────────────────────
  const [currentIdx, setCurrentIdx] = useState(0)
  const [currentFen, setCurrentFen] = useState('')
  const [legalMoves, setLegalMoves] = useState<MoveData[]>([])
  const [selectedSquare, setSelectedSquare] = useState<number | null>(null)
  const [isDiverted, setIsDiverted] = useState(false)
  const [highlighted, setHighlighted] = useState<number[]>([])
  // Squares highlighted from the position-diagnostic panel (isolated /
  // backward / holes / outposts). Kept separate from `highlighted` so
  // the AnalysisPanel's hover-highlight doesn't fight with it.
  const [diagKey, setDiagKey] = useState<string | null>(null)
  // Squares highlighted from clicking a persistent-weakness row in
  // the narrative cards. Cleared when the user navigates between
  // half-moves (the highlight wouldn't make sense on a different
  // position) and overridden when they click a diagnostic row.
  const [narrativeHighlight, setNarrativeHighlight] = useState<number[]>([])
  // Show red arrows for the captures the opponent could play next turn.
  // Hidden by default — even one big capture sequence clutters the
  // board, and users who want it just toggle the pill.
  const [showThreats, setShowThreats] = useState(false)
  const loadingMovesRef = useRef(false)

  // ── Analysis ──────────────────────────────────────────────────
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [aiThinking, setAiThinking] = useState(false)

  // ── Game annotation (move-by-move analysis) ───────────────────
  const [annotations, setAnnotations] = useState<MoveAnnotation[]>([])
  const [gameStats, setGameStats] = useState<GameStats | null>(null)
  const [annotating, setAnnotating] = useState(false)
  const [annotationProgress, setAnnotationProgress] = useState(0)
  const [annotationTotal, setAnnotationTotal] = useState(0)
  const annotationAbortRef = useRef<AbortController | null>(null)
  const autoLearnRef = useRef(false)

  // ── Deep pre-computation ──────────────────────────────────────
  const [precomputing, setPrecomputing] = useState(false)
  const [lastCacheHits, setLastCacheHits] = useState<{ hits: number; total: number } | null>(null)

  // ── Mode: review or learn ─────────────────────────────────────
  const [panelMode, setPanelMode] = useState<PanelMode>('review')

  // ── WASM engine (paused during batch annotation) ──────────────
  const scanFen = (result && !annotating) ? currentFen : null
  const scanInfo = useScanEngine(scanFen)

  // ── Best-move arrow ────────────────────────────────────────────
  const [arrow, setArrow] = useState<Arrow | null>(null)

  // ── Auto-scroll active move row ───────────────────────────────
  const activeRowRef = useRef<HTMLTableRowElement | null>(null)
  // Pre-load WASM engine as soon as the panel opens so it's ready if server-side fails
  useEffect(() => { getScanEngine() }, [])

  useEffect(() => {
    activeRowRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [currentIdx])

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

  const goTo = useCallback((idx: number, positions: PdnPosition[]) => {
    const pos = positions[Math.max(0, Math.min(idx, positions.length - 1))]
    setCurrentIdx(idx)
    setCurrentFen(pos.fen)
    setIsDiverted(false)
    setSelectedSquare(null)
    setHighlighted([])
    setAnalysis(null)
    setArrow(null)
    // Drop the narrative-row highlight so it doesn't survive a board
    // navigation — the square is contextual to the weakness summary
    // the user clicked, not the new position.
    setNarrativeHighlight([])
    loadLegalMoves(pos.fen)
  }, [loadLegalMoves])

  // Keyboard navigation ← →
  useEffect(() => {
    if (!result) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') goTo(Math.max(0, currentIdx - 1), result.positions)
      else if (e.key === 'ArrowRight') goTo(Math.min(result.positions.length - 1, currentIdx + 1), result.positions)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [result, currentIdx, goTo])

  const handleMove = useCallback(async (move: MoveData) => {
    setSelectedSquare(null)
    setArrow(null)
    try {
      const res = await applyPositionMove(currentFen, move.path)
      setCurrentFen(res.fen)
      setLegalMoves(res.moves)
      setIsDiverted(true)
      setAnalysis(null)
    } catch {
      loadLegalMoves(currentFen)
    }
  }, [currentFen, loadLegalMoves])

  const handleAnalyze = useCallback(async (question?: string, mode?: string) => {
    setAnalysisLoading(true)
    try {
      const analysisMode = mode ?? 'position'
      const moveHistory = (analysisMode === 'full_game' && result)
        ? result.positions.slice(1, currentIdx + 1).map(p => p.notation).filter((n): n is string => n !== null)
        : undefined
      const res = await analyzePositionFen(currentFen, question, language, analysisMode, moveHistory)
      setAnalysis(res)
      return res
    } catch {
      return null
    } finally {
      setAnalysisLoading(false)
    }
  }, [currentFen, language, result, currentIdx])

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const text = await file.text()
    setPdn(text)
    setImportError(null)
    setImporting(true)
    try {
      const data = await importPdn(text)
      setResult(data)
      setCurrentIdx(0)
      setCurrentFen(data.positions[0].fen)
      loadLegalMoves(data.positions[0].fen)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setImportError(detail ?? 'Erreur lors de l\'import')
    } finally {
      setImporting(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  function hubNotationToArrow(hub: string): Arrow | null {
    const sep = hub.includes('x') ? 'x' : hub.includes('-') ? '-' : null
    if (!sep) return null
    const parts = hub.split(sep).map(Number)
    if (parts.length < 2 || isNaN(parts[0]) || isNaN(parts[parts.length - 1])) return null
    return { from: parts[0], to: parts[parts.length - 1] }
  }

  const handleBestMove = useCallback(async (): Promise<string[] | null> => {
    setAiThinking(true)
    setArrow(null)
    try {
      const engine = getScanEngine()
      let hubMove: string | null = await engine.getMove(currentFen, 1500)
      if (!hubMove) hubMove = await getPositionBestMove(currentFen)
      if (!hubMove) return null
      const a = hubNotationToArrow(hubMove)
      if (a) setArrow(a)
      return [hubMove]
    } catch {
      return null
    } finally {
      setAiThinking(false)
    }
  }, [currentFen])

  // ── Batch game annotation ──────────────────────────────────────
  const handleAnnotateGame = useCallback(async () => {
    if (!result) return

    annotationAbortRef.current?.abort()
    const ctrl = new AbortController()
    annotationAbortRef.current = ctrl

    setAnnotating(true)
    setAnnotations([])
    setGameStats(null)
    setAnnotationProgress(0)
    setAnnotationTotal(result.positions.length)

    try {
      const { annotations: anns, cacheHits } = await annotateGame(
        result.positions,
        500,
        (done, total) => {
          setAnnotationProgress(done)
          setAnnotationTotal(total)
        },
        ctrl.signal,
      )
      if (!ctrl.signal.aborted) {
        setAnnotations(anns)
        setGameStats(computeStats(anns))
        setLastCacheHits({ hits: cacheHits, total: result.positions.length })
        if (autoLearnRef.current) {
          autoLearnRef.current = false
          setPanelMode('learn')
        }
      }
    } finally {
      setAnnotating(false)
      autoLearnRef.current = false
    }
  }, [result])

  const handleLearnClick = useCallback(() => {
    if (gameStats !== null) {
      setPanelMode('learn')
    } else {
      autoLearnRef.current = true
      handleAnnotateGame()
    }
  }, [gameStats, handleAnnotateGame])

  const handleDeepAnalysis = useCallback(async () => {
    if (!result) return
    setPrecomputing(true)
    try {
      const res = await precomputePositions(result.positions)
      if (res.success) {
        // Cache is now populated — run annotation which will use it instantly
        await handleAnnotateGame()
      }
    } finally {
      setPrecomputing(false)
    }
  }, [result, handleAnnotateGame])

  const annotationByIdx = new Map(annotations.map(a => [a.posIdx, a]))

  // ── Build move pairs for the table ────────────────────────────
  // positions[0] = initial, positions[1] = white move 1, positions[2] = black move 1 …
  const movePairs = result ? (() => {
    const pairs: Array<{
      moveNum: number
      whiteIdx: number
      whiteMoveLabel: string
      whiteVerdict: string | null
      whiteVerdictColor: string | undefined
      blackIdx: number | null
      blackMoveLabel: string | null
      blackVerdict: string | null
      blackVerdictColor: string | undefined
    }> = []
    const pos = result.positions
    for (let i = 1; i < pos.length; i += 2) {
      const wPos = pos[i]
      const bPos = i + 1 < pos.length ? pos[i + 1] : null
      const wAnn = annotationByIdx.get(i)
      const bAnn = bPos ? annotationByIdx.get(i + 1) : null
      pairs.push({
        moveNum: wPos.move_number,
        whiteIdx: i,
        whiteMoveLabel: wPos.notation ?? '',
        whiteVerdict: wAnn?.verdict ? VERDICT_SYMBOL[wAnn.verdict] : null,
        whiteVerdictColor: wAnn?.verdict ? VERDICT_COLOR[wAnn.verdict] : undefined,
        blackIdx: bPos ? i + 1 : null,
        blackMoveLabel: bPos?.notation ?? null,
        blackVerdict: bAnn?.verdict ? VERDICT_SYMBOL[bAnn.verdict] : null,
        blackVerdictColor: bAnn?.verdict ? VERDICT_COLOR[bAnn.verdict] : undefined,
      })
    }
    return pairs
  })() : []

  // ── Loading / empty state ─────────────────────────────────────
  // Direct PDN upload was removed (chat) — this panel is now reached
  // only from the 👤 Profil > game list. While the PDN auto-loads we
  // show a spinner ; if someone reaches this page without a preloaded
  // game we send them back to the home screen.
  if (!result) {
    // Two cases :
    //  1. Replay from <GameHistory> (initialPdn / initialGameId set) →
    //     spinner while the auto-load runs.
    //  2. Direct PDN upload (no preload) → file-picker.
    const isReplayLoad = !!(initialPdn || initialGameId)
    return (
      <div className="flex flex-col h-full bg-gray-900 text-gray-100">
        <div className="flex items-center gap-3 px-4 py-3 bg-gray-800 border-b border-gray-700 flex-shrink-0">
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-amber-500 text-2xl w-9 h-9 flex items-center justify-center rounded-lg hover:bg-gray-700 transition-colors"
          >
            ←
          </button>
          <h2 className="font-bold text-amber-500 text-base">
            {isReplayLoad ? 'Analyse de partie' : 'Importer une partie'}
          </h2>
        </div>

        {isReplayLoad ? (
          <div className="flex-1 overflow-y-auto p-6 flex flex-col items-center justify-center gap-4 text-center">
            {importError ? (
              <p className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded px-3 py-2 max-w-md">
                {importError}
              </p>
            ) : (
              <>
                <div className="spinner" />
                <p className="text-gray-300 text-sm">Chargement de la partie…</p>
              </>
            )}
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5">
            <p className="text-gray-400 text-sm text-center">
              Sélectionnez un fichier <span className="text-amber-400 font-mono">.pdn</span> exporté depuis lidraughts ou un autre logiciel.
            </p>

            <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileChange} />

            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={importing}
              className="w-full flex flex-col items-center gap-3 border-2 border-dashed border-gray-600 hover:border-amber-500 rounded-xl py-12 px-4 transition-colors disabled:opacity-40 cursor-pointer"
            >
              <span className="text-5xl">📂</span>
              <span className="text-white font-semibold text-sm">
                {importing ? 'Chargement…' : 'Choisir un fichier .pdn'}
              </span>
              <span className="text-gray-500 text-xs">lidraughts · DraughtsBoard · etc.</span>
            </button>

            {importError && (
              <p className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded px-3 py-2">
                {importError}
              </p>
            )}
          </div>
        )}
      </div>
    )
  }

  // ── Learn from mistakes mode ──────────────────────────────────
  if (panelMode === 'learn') {
    return (
      <LearnFromMistakes
        positions={result.positions}
        annotations={annotations}
        playerColor={null}
        onClose={() => setPanelMode('review')}
      />
    )
  }

  // ── Review phase UI ───────────────────────────────────────────
  const positions = result.positions
  const meta = result.metadata
  const currentPos = positions[currentIdx]
  const board = fenToBoard(currentFen)
  const flipped = positions[0].fen.startsWith('B:')

  const moveLabel = currentIdx === 0
    ? 'Position initiale'
    : `Coup ${currentPos.move_number} · ${currentPos.color === 'white' ? '⬜' : '⬛'} ${currentPos.notation}`

  // Verdict of the half-move that produced the currently displayed
  // position. Used to overlay "hanging pieces" warnings and surface the
  // material balance under the board. currentIdx === 0 means the initial
  // position (no move played yet) — no verdict.
  const activeVerdict = pedagogyAnalysis && currentIdx > 0
    ? pedagogyAnalysis.verdicts.find(v => v.move_number === currentIdx) ?? null
    : null
  const hangingSquares = activeVerdict
    ? [...activeVerdict.hanging_pieces_white, ...activeVerdict.hanging_pieces_black]
    : []
  // Mapping diagKey -> the list of squares it pulls from activeVerdict.
  // Defined here so both the panel buttons and the highlight overlay stay
  // in sync without re-walking the verdict shape in two places. Formation
  // slugs (e.g. "roozenburg_blancs") also enter this map and resolve to
  // their fixed 3-square signature.
  const diagSquaresByKey: Record<string, number[]> = activeVerdict ? {
    'iso-w': activeVerdict.isolated_pawns_white,
    'iso-b': activeVerdict.isolated_pawns_black,
    'ret-w': activeVerdict.backward_pawns_white,
    'ret-b': activeVerdict.backward_pawns_black,
    'tro-w': activeVerdict.holes_white,
    'tro-b': activeVerdict.holes_black,
    'pos-w': activeVerdict.outposts_white,
    'pos-b': activeVerdict.outposts_black,
    ...Object.fromEntries(
      activeVerdict.formations.map(f => [f, FORMATION_SQUARES[f] ?? []]),
    ),
  } : {}
  const diagSquares = diagKey && diagSquaresByKey[diagKey] ? diagSquaresByKey[diagKey] : []

  // Persistent flag overlay — small coloured dots on every square that
  // matches one of the 4 categories. Union of both sides; the dot
  // colour tells you the category, the piece colour tells you whose.
  // Empty when no verdict is active so the analysis-panel mode stays
  // visually clean.
  const flagSquares = activeVerdict ? {
    isolated: [...activeVerdict.isolated_pawns_white, ...activeVerdict.isolated_pawns_black],
    backward: [...activeVerdict.backward_pawns_white, ...activeVerdict.backward_pawns_black],
    holes:    [...activeVerdict.holes_white,          ...activeVerdict.holes_black],
    outposts: [...activeVerdict.outposts_white,       ...activeVerdict.outposts_black],
  } : undefined

  // Threat arrows — captures the side-to-move could play in features_after.
  // The side-to-move in features_after is the *opposite* of activeVerdict.side
  // (whoever just moved is no longer to move). We split each capture path
  // into adjacent (from, to) pairs so multi-jump captures render as a
  // chain of arrows, mirroring the actual move geometry.
  const threatArrows: Arrow[] = (showThreats && activeVerdict) ? (() => {
    const threats = activeVerdict.side === 'white'
      ? activeVerdict.threatened_captures_black
      : activeVerdict.threatened_captures_white
    const arr: Arrow[] = []
    for (const t of threats) {
      for (let i = 0; i < t.path.length - 1; i++) {
        arr.push({
          from: t.path[i],
          to: t.path[i + 1],
          color: '#ef4444',
          opacity: 0.55,
          width: 2.4,
        })
      }
    }
    return arr
  })() : []
  const threatCount = activeVerdict
    ? (activeVerdict.side === 'white'
        ? activeVerdict.threatened_captures_black.length
        : activeVerdict.threatened_captures_white.length)
    : 0

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 bg-gray-800 border-b border-gray-700 flex-shrink-0">
        <button
          onClick={() => { setResult(null); setPdn(''); setAnnotations([]); setGameStats(null) }}
          className="text-gray-400 hover:text-amber-500 w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-700 transition-colors"
        >
          ←
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-amber-500 font-bold text-sm truncate">
            {(meta.white && meta.black)
              // Color badge after each name so the reader instantly
              // knows who's playing whom on the board. ⬜ = blancs,
              // ⬛ = noirs. The badge sits after the name (not before)
              // so the truncate ellipsis falls on the badge rather
              // than the player's identifier when space runs short.
              ? <>{meta.white} ⬜ — {meta.black} ⬛</>
              : 'Partie importée'}
          </p>
          {(meta.result || meta.event) && (
            <p className="text-gray-500 text-xs truncate">
              {[meta.result, meta.event, meta.date].filter(Boolean).join(' · ')}
            </p>
          )}
        </div>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-300 text-sm px-1">✕</button>
      </div>

      {/* Board (left) + navigation / scan / pedagogy summary (right).
          Always 2-column — even on a 393 px iPhone — per user request.
          Board shrinks to ~55% of viewport width so the right column
          gets the remaining ~170-180 px for nav + ScanBar. */}
      <div className="flex-shrink-0 flex flex-row items-start gap-2 py-2 px-2 bg-gray-900 border-b border-gray-700">
        {/* LEFT: board */}
        <div className="flex-shrink-0" style={{ width: '55%', maxWidth: 280 }}>
          <Board
            board={board}
            legalMoves={legalMoves}
            onMove={handleMove}
            selectedSquare={selectedSquare}
            onSelectSquare={setSelectedSquare}
            disabled={false}
            highlightSquares={
              // Priority: narrative-click > diagnostic-row click > hover.
              // setNarrativeHighlight gives the persistent-weakness rows
              // a board-side preview without colliding with the diagnostic
              // grid's own row click handler.
              narrativeHighlight.length > 0 ? narrativeHighlight
              : diagSquares.length > 0     ? diagSquares
              : highlighted
            }
            warningSquares={hangingSquares}
            flagSquares={flagSquares}
            arrows={[...(arrow ? [arrow] : []), ...threatArrows]}
            flipped={flipped}
          />
        </div>

        {/* RIGHT: navigation, scan engine bar, pedagogy overlay. */}
        <div className="flex-1 min-w-0 flex flex-col gap-2">
          {/* Move-by-move navigation */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => goTo(Math.max(0, currentIdx - 1), positions)}
              disabled={currentIdx === 0}
              className="w-10 h-10 flex-shrink-0 flex items-center justify-center rounded-lg bg-gray-800 border border-gray-600 text-white disabled:opacity-25 text-2xl hover:bg-gray-700 transition-colors cursor-pointer"
            >‹</button>
            <div className="flex-1 min-w-0 text-center">
              <p className="text-xs text-gray-200 truncate">{moveLabel}</p>
              <p className="text-xs text-gray-600">{currentIdx} / {result.total_moves}</p>
            </div>
            <button
              onClick={() => goTo(Math.min(positions.length - 1, currentIdx + 1), positions)}
              disabled={currentIdx >= positions.length - 1}
              className="w-10 h-10 flex-shrink-0 flex items-center justify-center rounded-lg bg-gray-800 border border-gray-600 text-white disabled:opacity-25 text-2xl hover:bg-gray-700 transition-colors cursor-pointer"
            >›</button>
          </div>

          {isDiverted && (
            <button
              onClick={() => goTo(currentIdx, positions)}
              className="text-xs text-amber-500 hover:text-amber-300 underline cursor-pointer self-start"
            >
              ↺ Revenir à la partie importée
            </button>
          )}

          {/* Scan WASM engine bar — moved from below the board into the
              right column. Keeps engine info adjacent to nav, not far
              from the position it describes. */}
          <ScanBar info={scanInfo} loading={annotating} />
          {/* Pedagogy overlay (phase / matériel / formations / diagnostic
              + active move row) moved into the Position tab below the
              board — keeps the right column compact next to the board. */}
        </div>
      </div>

      {/* Scrollable content: analysis first, then move list */}
      <div className="flex-1 overflow-y-auto overscroll-contain">

        {/* ── Analysis section (6 buttons + progress + stats + AI results) ── */}
        <div className="px-3 py-3 flex flex-col gap-3 border-b border-gray-800">

          {/* Progress bar (shown while annotating) */}
          {annotating && (
            <div>
              <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                <span>{annotationProgress === 0 && annotationTotal > 0 ? '⚡ Analyse serveur…' : 'Analyse en cours…'}</span>
                {annotationProgress > 0 && (
                  <span className="font-mono">{annotationProgress} / {annotationTotal}</span>
                )}
              </div>
              <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                {annotationProgress === 0 && annotationTotal > 0 ? (
                  <div className="h-full bg-indigo-500 rounded-full animate-pulse w-full" />
                ) : (
                  <div
                    className="h-full bg-indigo-500 rounded-full transition-all duration-200"
                    style={{ width: annotationTotal > 0 ? `${(annotationProgress / annotationTotal) * 100}%` : '0%' }}
                  />
                )}
              </div>
            </div>
          )}

          {/* Stats (shown after annotation) */}
          {lastCacheHits && !annotating && (
            <div className="text-xs text-center text-gray-500 -mb-1">
              {lastCacheHits.hits > 0
                ? `⚡ ${lastCacheHits.hits}/${lastCacheHits.total} positions depuis le cache`
                : `Cache : 0/${lastCacheHits.total} — aucune position en mémoire`}
            </div>
          )}

          {gameStats && !annotating && (
            <div className="grid grid-cols-2 gap-px bg-gray-800 rounded-lg overflow-hidden text-xs">
              {(['white', 'black'] as const).map(color => {
                const acpl = color === 'white' ? gameStats.whiteAcpl : gameStats.blackAcpl
                const counts = color === 'white' ? gameStats.whiteCounts : gameStats.blackCounts
                const player = color === 'white' ? meta.white : meta.black
                return (
                  <div key={color} className="bg-gray-950 px-3 py-2 flex flex-col gap-1">
                    <div className="flex items-center gap-1.5">
                      <span>{color === 'white' ? '⬜' : '⬛'}</span>
                      {player && <span className="text-gray-300 truncate font-semibold">{player}</span>}
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-gray-500">Moy.</span>
                      <span className="font-mono font-bold text-gray-200">{acpl} cp</span>
                    </div>
                    <div className="flex gap-2">
                      {counts.blunder > 0 && (
                        <span className="font-bold" style={{ color: VERDICT_COLOR.blunder }}>{counts.blunder}??</span>
                      )}
                      {counts.mistake > 0 && (
                        <span className="font-bold" style={{ color: VERDICT_COLOR.mistake }}>{counts.mistake}?</span>
                      )}
                      {counts.inaccuracy > 0 && (
                        <span className="font-bold" style={{ color: VERDICT_COLOR.inaccuracy }}>{counts.inaccuracy}?!</span>
                      )}
                      {counts.blunder + counts.mistake + counts.inaccuracy === 0 && (
                        <span className="text-green-500">Parfait ✓</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* AnalysisPanel — 6 buttons (4 AI + Coup par coup + Apprendre).
              Hidden in history-replay mode (initialGameId) to leave the
              floor to <PedagogyPanel>. */}
          {!initialGameId && (
            <AnalysisPanel
              gameId="import"
              onAnalyze={handleAnalyze}
              onBestMove={handleBestMove}
              analysis={analysis}
              loading={analysisLoading}
              onHighlightSquare={setHighlighted}
              aiThinking={aiThinking}
              onAnnotate={handleAnnotateGame}
              onLearn={handleLearnClick}
              annotating={annotating}
            />
          )}

          {/* Pedagogy mode — without analysis, show the "Analyser" /
              loading state through PedagogyPanel. With analysis, the
              tab system below this section takes over. */}
          {initialGameId && !pedagogyAnalysis && (
            <PedagogyPanel
              gameId={initialGameId}
              analysis={pedagogyAnalysis}
              loading={pedagogyLoading}
              userSide={initialUserSide ?? 'white'}
              lang={language}
              onAnalyze={handleAnalyzePedagogy}
              error={pedagogyError}
              currentHalfMove={currentIdx}
              onJumpTo={(hm) => goTo(hm, positions)}
            />
          )}

          {initialGameId && pedagogyAnalysis && (
            <PedagogyTabsPanel
              gameId={initialGameId}
              analysis={pedagogyAnalysis}
              userSide={initialUserSide ?? 'white'}
              lang={language}
              activeVerdict={activeVerdict}
              hangingSquares={hangingSquares}
              threatCount={threatCount}
              showThreats={showThreats}
              onToggleThreats={() => setShowThreats(v => !v)}
              diagKey={diagKey}
              onDiagKey={k => setDiagKey(prev => prev === k ? null : k)}
              currentHalfMove={currentIdx}
              onJumpTo={(hm) => goTo(hm, positions)}
              onWeaknessClick={(sqs) => {
                setNarrativeHighlight(sqs)
                setDiagKey(null)   // Clear diagnostic-row highlight so
                                   // the new selection isn't fighting
                                   // with the previous one.
              }}
              onMotifJump={(slug) => {
                const v = pedagogyAnalysis.verdicts.find(
                  vd => vd.motifs.some(m => m.motif === slug),
                )
                if (v) goTo(v.move_number, positions)
              }}
              onMotifClick={onMotifClick}
              onOpenLesson={onOpenLesson}
            />
          )}

        </div>

        {/* ── Move list ──
            In history-replay mode, this table is redundant with the
            move-by-move verdicts already shown inside <PedagogyPanel>
            once dilf has run. Keep it for uploaded PDNs (no pedagogy
            data) and for the brief loading window. */}
        {!(initialGameId && pedagogyAnalysis) && (
        <div className="px-2 pt-2 pb-3">
          <table className="w-full border-collapse text-xs font-mono">
            <tbody>
              {movePairs.map(row => {
                const isActiveRow = currentIdx === row.whiteIdx || currentIdx === row.blackIdx
                return (
                  <tr
                    key={row.moveNum}
                    ref={isActiveRow ? activeRowRef : null}
                  >
                    <td className="text-gray-600 pr-1 py-0.5 select-none text-right w-7">
                      {row.moveNum}.
                    </td>
                    <td className="py-0.5 pr-0.5 w-1/2">
                      <button
                        onClick={() => goTo(row.whiteIdx, positions)}
                        className={`w-full text-left px-1.5 py-0.5 rounded transition-colors ${
                          currentIdx === row.whiteIdx
                            ? 'bg-amber-700 text-white font-bold'
                            : 'text-gray-200 hover:bg-gray-800'
                        }`}
                      >
                        {row.whiteMoveLabel}
                        {row.whiteVerdict && (
                          <span className="ml-0.5 font-bold" style={{ color: row.whiteVerdictColor }}>
                            {row.whiteVerdict}
                          </span>
                        )}
                      </button>
                    </td>
                    <td className="py-0.5 w-1/2">
                      {row.blackMoveLabel !== null && row.blackIdx !== null && (
                        <button
                          onClick={() => goTo(row.blackIdx!, positions)}
                          className={`w-full text-left px-1.5 py-0.5 rounded transition-colors ${
                            currentIdx === row.blackIdx
                              ? 'bg-amber-700 text-white font-bold'
                              : 'text-gray-400 hover:bg-gray-800'
                          }`}
                        >
                          {row.blackMoveLabel}
                          {row.blackVerdict && (
                            <span className="ml-0.5 font-bold" style={{ color: row.blackVerdictColor }}>
                              {row.blackVerdict}
                            </span>
                          )}
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        )}
      </div>
    </div>
  )
}
