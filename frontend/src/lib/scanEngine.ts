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
  private ready = false
  private analyzing = false
  private currentCb: ScanCallback | null = null
  private lastInfo: Partial<ScanInfo> = {}
  private pending: { hubPos: string; cb: ScanCallback } | null = null

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
      }
      // Init sequence — queued by worker until WASM finishes loading
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
      this.ready = true
      if (this.pending) {
        this.run(this.pending.hubPos, this.pending.cb)
        this.pending = null
      }
      return
    }

    if (msg === 'wait' || msg.startsWith('hub ')) return

    if (msg.startsWith('info ')) {
      const parsed = parseInfo(msg)
      this.lastInfo = { ...this.lastInfo, ...parsed }
      this.currentCb?.({ ...emptyInfo(), ...this.lastInfo, done: false })
      return
    }

    if (msg.startsWith('done ')) {
      this.analyzing = false
      const moveM  = msg.match(/move=(\S+)/)
      const depthM = msg.match(/depth=(\d+)/)
      const scoreM = msg.match(/score=([+-]?\d+)/)
      this.currentCb?.({
        ...emptyInfo(),
        ...this.lastInfo,
        bestMove: moveM?.[1] ?? null,
        depth:    parseInt(depthM?.[1] ?? '0') || (this.lastInfo.depth ?? 0),
        score:    parseInt(scoreM?.[1] ?? String(this.lastInfo.score ?? 0)),
        done: true,
      })
    }
  }

  private run(hubPos: string, cb: ScanCallback) {
    if (this.analyzing) this.send('stop')
    this.currentCb = cb
    this.lastInfo = {}
    this.analyzing = true
    this.send(`pos pos=${hubPos}`)
    this.send('go analyze')
  }

  analyze(fen: string, cb: ScanCallback) {
    const hubPos = fenToHubPos(fen)
    if (!this.ready) {
      this.pending = { hubPos, cb }
      return
    }
    this.run(hubPos, cb)
  }

  stop() {
    if (this.analyzing) {
      this.send('stop')
      this.analyzing = false
    }
    this.currentCb = null
    this.pending = null
  }

  get available(): boolean {
    return this.worker !== null
  }
}

let _instance: ScanEngineWorker | null = null

export function getScanEngine(): ScanEngineWorker {
  if (!_instance) _instance = new ScanEngineWorker()
  return _instance
}
