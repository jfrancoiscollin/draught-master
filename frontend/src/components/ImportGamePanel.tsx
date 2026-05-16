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
import PedagogyPanel from './PedagogyPanel'
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
}

type PanelMode = 'review' | 'learn'

export default function ImportGamePanel({
  onClose,
  initialPdn,
  initialGameId,
  initialUserSide,
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

  // ── Import phase UI ───────────────────────────────────────────
  if (!result) {
    return (
      <div className="flex flex-col h-full bg-gray-900 text-gray-100">
        <div className="flex items-center gap-3 px-4 py-3 bg-gray-800 border-b border-gray-700 flex-shrink-0">
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-amber-500 text-2xl w-9 h-9 flex items-center justify-center rounded-lg hover:bg-gray-700 transition-colors"
          >
            ←
          </button>
          <h2 className="font-bold text-amber-500 text-base">Importer une partie</h2>
        </div>

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
            {(meta.white && meta.black) ? `${meta.white} — ${meta.black}` : 'Partie importée'}
          </p>
          {(meta.result || meta.event) && (
            <p className="text-gray-500 text-xs truncate">
              {[meta.result, meta.event, meta.date].filter(Boolean).join(' · ')}
            </p>
          )}
        </div>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-300 text-sm px-1">✕</button>
      </div>

      {/* Board + navigation */}
      <div className="flex-shrink-0 flex flex-col items-center py-2 bg-gray-900 border-b border-gray-700">
        <div style={{ width: '100%', maxWidth: 240 }}>
          <Board
            board={board}
            legalMoves={legalMoves}
            onMove={handleMove}
            selectedSquare={selectedSquare}
            onSelectSquare={setSelectedSquare}
            disabled={false}
            highlightSquares={highlighted}
            arrows={arrow ? [arrow] : []}
            flipped={flipped}
          />
        </div>

        <div className="flex items-center gap-2 mt-2 w-full max-w-xs px-2">
          <button
            onClick={() => goTo(Math.max(0, currentIdx - 1), positions)}
            disabled={currentIdx === 0}
            className="w-10 h-10 flex items-center justify-center rounded-lg bg-gray-800 border border-gray-600 text-white disabled:opacity-25 text-2xl hover:bg-gray-700 transition-colors cursor-pointer"
          >‹</button>
          <div className="flex-1 text-center">
            <p className="text-xs text-gray-200 truncate">{moveLabel}</p>
            <p className="text-xs text-gray-600">{currentIdx} / {result.total_moves}</p>
          </div>
          <button
            onClick={() => goTo(Math.min(positions.length - 1, currentIdx + 1), positions)}
            disabled={currentIdx >= positions.length - 1}
            className="w-10 h-10 flex items-center justify-center rounded-lg bg-gray-800 border border-gray-600 text-white disabled:opacity-25 text-2xl hover:bg-gray-700 transition-colors cursor-pointer"
          >›</button>
        </div>

        {isDiverted && (
          <button
            onClick={() => goTo(currentIdx, positions)}
            className="mt-1.5 text-xs text-amber-500 hover:text-amber-300 underline cursor-pointer"
          >
            ↺ Revenir à la partie importée
          </button>
        )}
      </div>

      {/* Scan WASM engine bar */}
      <ScanBar info={scanInfo} loading={annotating} />

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

          {initialGameId && (
            <PedagogyPanel
              gameId={initialGameId}
              analysis={pedagogyAnalysis}
              loading={pedagogyLoading}
              userSide={initialUserSide ?? 'white'}
              lang={language}
              onAnalyze={handleAnalyzePedagogy}
              error={pedagogyError}
            />
          )}

          {initialGameId && (
            <PedagogyPanel
              gameId={initialGameId}
              analysis={pedagogyAnalysis}
              loading={pedagogyLoading}
              userSide={initialUserSide ?? 'white'}
              lang={language}
              onAnalyze={handleAnalyzePedagogy}
              error={pedagogyError}
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
