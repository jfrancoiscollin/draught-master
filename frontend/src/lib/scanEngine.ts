import type { MoveData } from '../types'

export interface ScanInfo {
  depth: number
  score: number   // centipawns, positive = white advantage
  nodes: number
  nps: number
  pv: string[]    // principal variation in Hub notation
  bestMove: string | null
  done: boolean
}

export type ScanCallback = (info: ScanInfo) => void

// Convert our FEN (W:W32,...:B1,...) to Hub 51-char position string
export function fenToHubPos(fen: string): string {
  const board = new Array(51).fill('e')
  const parts = fen.split(':')
  const turn = parts[0]  // 'W' or 'B'
  for (let i = 1; i < parts.length; i++) {
    const section = parts[i]
    if (!section) continue
    const color = section[0]
    const tokens = section.slice(1).split(',')
    for (const token of tokens) {
      if (!token) continue
      const isKing = token.startsWith('K')
      const num = parseInt(isKing ? token.slice(1) : token, 10)
      if (!isNaN(num) && num >= 1 && num <= 50) {
        board[num] = color === 'W' ? (isKing ? 'W' : 'w') : (isKing ? 'B' : 'b')
      }
    }
  }
  return turn + board.slice(1).join('')
}

function emptyInfo(): ScanInfo {
  return { depth: 0, score: 0, nodes: 0, nps: 0, pv: [], bestMove: null, done: false }
}

function parseInfo(msg: string): Partial<ScanInfo> {
  const result: Partial<ScanInfo> = {}
  const depthM = msg.match(/\bdepth=(\d+)/)
  const scoreM = msg.match(/\bscore=([+-]?\d+)/)
  const nodesM = msg.match(/\bnodes=(\d+)/)
  const npsM   = msg.match(/\bnps=(\d+)/)
  const pvM    = msg.match(/\bpv="([^"]*)"/)
  if (depthM) result.depth = parseInt(depthM[1])
  if (scoreM) result.score = parseInt(scoreM[1])
  if (nodesM) result.nodes = parseInt(nodesM[1])
  if (npsM)   result.nps   = parseInt(npsM[1])
  if (pvM)    result.pv    = pvM[1].trim().split(/\s+/).filter(Boolean)
  return result
}

class ScanEngineWorker {
  private worker: Worker | null = null
  private _ready = false
  private analyzing = false
  private currentCb: ScanCallback | null = null
  private lastInfo: Partial<ScanInfo> = {}
  private bestSoFar: string | null = null
  private generation = 0
  private activegen = 0
  private onReadyQueue: (() => void)[] = []

  // Prevent external stop() calls during batch evaluation (annotateGame)
  private locked = false
  // How many "done" responses we expect from previously-stopped searches
  // to discard before processing new search results
  private pendingStopDones = 0

  constructor() {
    this.boot()
  }

  private boot() {
    try {
      this.worker = new Worker('/scan_normal.wasm.js')
      this.worker.onmessage = (e: MessageEvent<string>) => this.recv(e.data)
      this.worker.onerror = (err) => {
        console.error('[Scan WASM] worker error:', err)
        this.worker = null
        const queue = this.onReadyQueue.splice(0)
        queue.forEach(fn => fn())
      }
      this.send('hub')
      this.send('set-param name=variant value=normal')
      this.send('set-param name=bb-size value=0')
      this.send('init')
    } catch (e) {
      console.warn('[Scan WASM] could not create worker:', e)
    }
  }

  private send(cmd: string) {
    this.worker?.postMessage(cmd)
  }

  private recv(msg: string) {
    if (!msg) return

    if (msg === 'ready') {
      this._ready = true
      const queue = this.onReadyQueue.splice(0)
      queue.forEach(fn => fn())
      return
    }

    if (msg === 'wait' || msg.startsWith('hub ')) return

    if (msg.startsWith('info ')) {
      const parsed = parseInfo(msg)
      this.lastInfo = { ...this.lastInfo, ...parsed }
      if (this.lastInfo.pv?.length) this.bestSoFar = this.lastInfo.pv[0]
      this.currentCb?.({ ...emptyInfo(), ...this.lastInfo, done: false })
      return
    }

    if (msg.startsWith('done ')) {
      this.analyzing = false
      // Consume stale "done" from a search we stopped manually.
      // These arrive as macro-tasks and can corrupt the next search's callback.
      if (this.pendingStopDones > 0) {
        this.pendingStopDones--
        return
      }
      const moveM  = msg.match(/move=(\S+)/)
      const depthM = msg.match(/depth=(\d+)/)
      const scoreM = msg.match(/score=([+-]?\d+)/)
      const bestMove = moveM?.[1] ?? this.bestSoFar ?? null
      const cb = this.currentCb
      this.currentCb = null
      cb?.({
        ...emptyInfo(),
        ...this.lastInfo,
        bestMove,
        depth:    parseInt(depthM?.[1] ?? '0') || (this.lastInfo.depth ?? 0),
        score:    parseInt(scoreM?.[1] ?? String(this.lastInfo.score ?? 0)),
        done: true,
      })
    }
  }

  private stopSearch() {
    if (this.analyzing) {
      this.send('stop')
      this.pendingStopDones++
      this.analyzing = false
    }
  }

  private whenReady(): Promise<void> {
    if (this._ready) return Promise.resolve()
    return new Promise(resolve => this.onReadyQueue.push(resolve))
  }

  private doAnalyze(hubPos: string, cb: ScanCallback) {
    this.stopSearch()
    this.generation++
    this.activegen = this.generation
    this.currentCb = cb
    this.lastInfo = {}
    this.bestSoFar = null
    this.analyzing = true
    this.send(`pos pos=${hubPos}`)
    this.send('go analyze')
  }

  analyze(fen: string, cb: ScanCallback): void {
    const hubPos = fenToHubPos(fen)
    this.whenReady().then(() => this.doAnalyze(hubPos, cb))
  }

  // One-shot evaluation for batch analysis: returns {score, bestMove} or null if not ready.
  // Uses "go analyze" + timeout-stop (the WASM build does not support "go think" with time limits).
  evaluate(fen: string, ms: number = 500): Promise<{ score: number; bestMove: string | null } | null> {
    if (!this._ready) return Promise.resolve(null)

    return new Promise(resolve => {
      let resolved = false
      const myGen = ++this.generation
      this.activegen = myGen
      let localScore = 0
      let localBest: string | null = null

      const finish = (score: number, bestMove: string | null) => {
        if (resolved) return
        resolved = true
        resolve({ score, bestMove })
      }

      this.stopSearch()
      this.currentCb = (info) => {
        if (this.activegen !== myGen) return
        if (info.pv.length > 0) { localBest = info.pv[0]; this.bestSoFar = info.pv[0] }
        localScore = info.score
        if (info.done) finish(info.score, info.bestMove ?? localBest)
      }
      this.lastInfo = {}
      this.bestSoFar = null
      this.analyzing = true
      this.send(`pos pos=${fenToHubPos(fen)}`)
      this.send('go analyze')

      setTimeout(() => {
        if (!resolved) {
          this.activegen++
          this.stopSearch()
          this.currentCb = null
          finish(localScore, localBest)
        }
      }, ms)
    })
  }

  // One-shot best move: returns null immediately if not ready (caller falls back to server)
  getMove(fen: string, ms: number = 1500): Promise<string | null> {
    if (!this._ready) return Promise.resolve(null)

    return new Promise(resolve => {
      let resolved = false
      const myGen = ++this.generation
      this.activegen = myGen
      let localBest: string | null = null

      const finish = (move: string | null) => {
        if (resolved) return
        resolved = true
        resolve(move)
      }

      this.stopSearch()
      this.currentCb = (info) => {
        if (this.activegen !== myGen) return
        if (info.pv.length > 0) { localBest = info.pv[0]; this.bestSoFar = info.pv[0] }
        if (info.done) finish(info.bestMove ?? localBest)
      }
      this.lastInfo = {}
      this.bestSoFar = null
      this.analyzing = true
      this.send(`pos pos=${fenToHubPos(fen)}`)
      this.send('go analyze')

      setTimeout(() => {
        if (!resolved) {
          this.activegen++
          this.stopSearch()
          this.currentCb = null
          finish(localBest)
        }
      }, ms)
    })
  }

  stop(): void {
    // During batch evaluation, external stops (e.g. from useScanEngine cleanup) are ignored
    // so they don't interrupt mid-evaluation.
    if (this.locked) return
    this.stopSearch()
    this.activegen++
    this.currentCb = null
  }

  // Prevent external stop() calls during batch evaluation
  lock(): void { this.locked = true }
  unlock(): void { this.locked = false }

  get available(): boolean { return this.worker !== null }
  get ready(): boolean { return this._ready }
}

// Match a Hub move notation ("37-32" or "26x17x8") against legal moves
export function matchHubMove(hubMove: string, legalMoves: MoveData[]): MoveData | null {
  if (!hubMove || !legalMoves.length) return null

  if (hubMove.includes('x')) {
    const squares = hubMove.split('x').map(Number)
    const from = squares[0]
    const to = squares[squares.length - 1]
    const exact = legalMoves.find(m =>
      m.path.length === squares.length && m.path.every((sq, i) => sq === squares[i])
    )
    if (exact) return exact
    return legalMoves.find(m =>
      m.path[0] === from && m.path[m.path.length - 1] === to && m.captures.length > 0
    ) ?? null
  }

  if (hubMove.includes('-')) {
    const [from, to] = hubMove.split('-').map(Number)
    return legalMoves.find(m =>
      m.path[0] === from && m.path[m.path.length - 1] === to && m.captures.length === 0
    ) ?? null
  }

  return null
}

let _instance: ScanEngineWorker | null = null

export function getScanEngine(): ScanEngineWorker {
  if (!_instance) _instance = new ScanEngineWorker()
  return _instance
}
