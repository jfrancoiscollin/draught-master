import type { PdnPosition, PositionEval } from '../api/client'
import { analyzePositionsBatch } from '../api/client'
import { getScanEngine } from './scanEngine'

export type Verdict = 'blunder' | 'mistake' | 'inaccuracy' | null

export interface MoveAnnotation {
  posIdx: number           // index in positions[] (the position AFTER the move)
  color: 'white' | 'black'
  scoreBefore: number      // eval at pos[posIdx-1], from that position's side-to-move perspective
  scoreAfter: number       // eval at pos[posIdx], from that position's side-to-move perspective
  lossCp: number           // centipawn loss capped at 1000
  deltaWinChance: number   // positive = player lost winning chances
  verdict: Verdict
  bestMove: string | null  // best move at pos[posIdx-1] in Hub notation
}

export interface GameStats {
  whiteAcpl: number
  blackAcpl: number
  whiteCounts: Record<NonNullable<Verdict>, number>
  blackCounts: Record<NonNullable<Verdict>, number>
}

// Scan uses a compressed score scale (~30 units ≈ one man, vs Stockfish's 100 cp = one pawn).
// Coefficient 0.04 is calibrated so: inaccuracy ≥ 4 pts, mistake ≥ 8 pts, blunder ≥ 20 pts.
function winChance(cp: number): number {
  return 2 / (1 + Math.exp(-0.04 * cp)) - 1
}

function classify(dwc: number): Verdict {
  if (dwc >= 0.30) return 'blunder'
  if (dwc >= 0.15) return 'mistake'
  if (dwc >= 0.075) return 'inaccuracy'
  return null
}

export function computeStats(annotations: MoveAnnotation[]): GameStats {
  const empty = (): Record<NonNullable<Verdict>, number> => ({ blunder: 0, mistake: 0, inaccuracy: 0 })
  const whiteLosses: number[] = []
  const blackLosses: number[] = []
  const whiteCounts = empty()
  const blackCounts = empty()

  for (const a of annotations) {
    const losses = a.color === 'white' ? whiteLosses : blackLosses
    const counts = a.color === 'white' ? whiteCounts : blackCounts
    losses.push(a.lossCp)
    if (a.verdict) counts[a.verdict]++
  }

  const avg = (arr: number[]) => arr.length ? Math.round(arr.reduce((a, b) => a + b, 0) / arr.length) : 0
  return {
    whiteAcpl: avg(whiteLosses),
    blackAcpl: avg(blackLosses),
    whiteCounts,
    blackCounts,
  }
}

function buildAnnotations(positions: PdnPosition[], evals: PositionEval[]): MoveAnnotation[] {
  const annotations: MoveAnnotation[] = []
  for (let i = 1; i < positions.length; i++) {
    const pos = positions[i]
    if (!pos.color) continue

    const scoreBefore = evals[i - 1].score
    const scoreAfter  = evals[i].score
    const bestMove    = evals[i - 1].bestMove

    // scoreBefore: from side-to-move's perspective (positive = that player is ahead)
    // scoreAfter:  from opponent's perspective after the move (positive = opponent is ahead)
    // Perfect move: scoreBefore + scoreAfter ≈ 0 (signs cancel). Blunder: both positive = large loss.
    const rawLoss = scoreBefore + scoreAfter
    const lossCp = Math.min(1000, Math.max(0, rawLoss))

    const dwc = winChance(scoreBefore) + winChance(scoreAfter)
    const deltaWinChance = Math.max(0, dwc)
    const verdict = classify(deltaWinChance)

    if (verdict) {
      console.log(`[annotate] move ${pos.move_number} ${pos.color} ${pos.notation}: before=${scoreBefore} after=${scoreAfter} loss=${lossCp}cp dwc=${dwc.toFixed(3)} → ${verdict}`)
    }

    annotations.push({
      posIdx: i,
      color: pos.color as 'white' | 'black',
      scoreBefore,
      scoreAfter,
      lossCp,
      deltaWinChance,
      verdict,
      bestMove,
    })
  }
  return annotations
}

export async function annotateGame(
  positions: PdnPosition[],
  msPerMove: number = 500,
  onProgress: (done: number, total: number) => void,
  signal: AbortSignal,
): Promise<MoveAnnotation[]> {
  onProgress(0, positions.length)

  // ── Try server-side batch analysis first (native Scan binary: faster & deeper) ──
  // Adaptive time budget: up to 5 s/position, capped so total stays under 240 s.
  const adaptiveMs = Math.min(5000, Math.floor(240000 / positions.length))
  if (!signal.aborted) {
    const serverEvals = await analyzePositionsBatch(positions, adaptiveMs)
    if (serverEvals && serverEvals.length === positions.length) {
      onProgress(positions.length, positions.length)
      return buildAnnotations(positions, serverEvals)
    }
  }

  // ── Fall back to client-side WASM Scan ──
  const engine = getScanEngine()
  // If WASM is still initialising (downloading), wait up to 90s for it
  if (!engine.ready) {
    const ok = await engine.waitReady(90000)
    if (!ok) return []
  }

  // Stop any ongoing search and lock the engine so that external callers
  // (e.g. useScanEngine cleanup after React re-render) cannot interrupt us.
  engine.stop()
  engine.lock()

  // Yield to the event loop so any in-flight "done" messages from the
  // stopped search are processed (and discarded) before we start evaluating.
  await new Promise(r => setTimeout(r, 100))

  if (signal.aborted) { engine.unlock(); return [] }

  const evals: PositionEval[] = []

  try {
    for (let i = 0; i < positions.length; i++) {
      if (signal.aborted) break
      const res = await engine.evaluate(positions[i].fen, msPerMove)
      evals.push(res ?? { score: 0, bestMove: null })
      console.log(`[annotate:wasm] pos ${i} score=${evals[i].score} best=${evals[i].bestMove}`)
      onProgress(i + 1, positions.length)
    }
  } finally {
    engine.unlock()
  }

  if (signal.aborted) return []
  return buildAnnotations(positions, evals)
}

export const VERDICT_SYMBOL: Record<NonNullable<Verdict>, string> = {
  blunder:    '??',
  mistake:    '?',
  inaccuracy: '?!',
}

export const VERDICT_COLOR: Record<NonNullable<Verdict>, string> = {
  blunder:    '#ef4444',
  mistake:    '#f97316',
  inaccuracy: '#eab308',
}

export const VERDICT_LABEL_FR: Record<NonNullable<Verdict>, string> = {
  blunder:    'Gaffe',
  mistake:    'Erreur',
  inaccuracy: 'Imprécision',
}
