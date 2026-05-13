import React, { useState, useEffect, useRef } from 'react'
import { getOpeningCacheBuildStatus, ingestPdn, startEval, startReeval } from '../api/client'

interface Props {
  onClose: () => void
}

type SelectionMode = 'manual' | 'elo'

async function fetchPlayersByRating(
  min: number, max: number, count: number
): Promise<{ players: { username: string; rating: number }[]; pool_size: number }> {
  const params = new URLSearchParams({
    rating_min: String(min),
    rating_max: String(max),
    count: String(count),
  })
  const res = await fetch(`/api/opening-book/players?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const data = await res.json()
  return {
    players: (data.players ?? []) as { username: string; rating: number }[],
    pool_size: data.pool_size ?? data.found ?? 0,
  }
}

export default function OpeningCacheBuilder({ onClose }: Props) {
  const [mode, setMode] = useState<SelectionMode>('manual')

  // Manual mode
  const [usernames, setUsernames] = useState('el-negron\npbp7055')

  // Elo mode
  const [ratingMin, setRatingMin] = useState(1800)
  const [ratingMax, setRatingMax] = useState(2300)
  const [playerCount, setPlayerCount] = useState(10)
  const [foundPlayers, setFoundPlayers] = useState<{ username: string; rating: number }[]>([])
  const [poolSize, setPoolSize] = useState<number | null>(null)
  const [searchDone, setSearchDone] = useState(false)

  // Shared config
  const [maxGames, setMaxGames] = useState(100)
  const [maxMoves, setMaxMoves] = useState(12)
  const [msPerPos, setMsPerPos] = useState(5000)

  // Job status
  const [status, setStatus] = useState<{
    status: string; message: string; fetched_games: number;
    unique_positions: number; computed: number; skipped: number;
    total_to_compute: number; errors: number; cache_size: number;
  } | null>(null)
  const [starting, setStarting] = useState(false)
  const [fetchMessage, setFetchMessage] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  const [cacheSize, setCacheSize] = useState<number | null>(null)

  // NNUE corpus
  // 0 = toutes (no ?max param)
  const [corpusMaxGames, setCorpusMaxGames] = useState(0)

  // Corpus — discover strong players via opponent extraction from seed games
  const [topNb, setTopNb] = useState(200)
  const [topSeeds, setTopSeeds] = useState('')  // empty = auto-scrape lidraughts.org/player
  const [topMinRating, setTopMinRating] = useState(1800)
  const [topPlayers, setTopPlayers] = useState<{ username: string; rating: number | null; gameCount: number }[]>([])
  const [topFetching, setTopFetching] = useState(false)
  const [topFetchDone, setTopFetchDone] = useState(false)
  const [topFetchError, setTopFetchError] = useState('')
  const [corpusRatingMax, setCorpusRatingMax] = useState(0)

  // PDN direct download (no DB storage)
  const [pdnDownloading, setPdnDownloading] = useState(false)
  const [pdnMsg, setPdnMsg] = useState('')

  // DB volume info
  const [dbInfo, setDbInfo] = useState<{
    db_path: string; env_override: boolean; file_exists: boolean;
    file_size_bytes: number | null; positions: number; evaluated: number;
  } | null>(null)
  const [dbInfoLoading, setDbInfoLoading] = useState(false)
  const [migrating, setMigrating] = useState(false)
  const [migrateResult, setMigrateResult] = useState<{
    status: string; source_positions?: number; new_positions_added?: number; continuations_merged?: number; message?: string;
  } | null>(null)
  const [reevalRunning, setReevalRunning] = useState(false)
  const [reevalMessage, setReevalMessage] = useState('')

  const filteredCorpusPlayers = topPlayers.filter(p =>
    corpusRatingMax === 0 || (p.rating ?? 0) <= corpusRatingMax
  )

  const filteredTotalGames = filteredCorpusPlayers.reduce((sum, p) => {
    const n = corpusMaxGames > 0 ? Math.min(p.gameCount, corpusMaxGames) : p.gameCount
    return sum + n
  }, 0)

  const handleFetchTopPlayers = async () => {
    setTopFetchDone(false)
    setTopFetchError('')
    setTopFetching(true)
    const params = new URLSearchParams({
      seeds: topSeeds.trim(),   // empty = auto-scrape lidraughts.org/player
      min_rating: String(topMinRating),
      nb: String(topNb),
      max_games_per_seed: '100',
    })
    try {
      const res = await fetch(`/api/lidraughts/top-players?${params}`)
      if (res.ok) {
        const data = await res.json()
        if (data.error) {
          setTopFetchError(data.error)
        } else {
          const incoming: { username: string; rating: number | null; game_count?: number }[] = data.players ?? []
          // Merge with existing players — keep highest rating and latest game_count, deduplicate
          setTopPlayers(prev => {
            const mergedRating = new Map<string, number>()
            const mergedCount = new Map<string, number>()
            for (const p of prev) {
              mergedRating.set(p.username, p.rating ?? 0)
              mergedCount.set(p.username, p.gameCount)
            }
            for (const p of incoming) {
              mergedRating.set(p.username, Math.max(mergedRating.get(p.username) ?? 0, p.rating ?? 0))
              if ((p.game_count ?? 0) > 0) mergedCount.set(p.username, p.game_count!)
            }
            return Array.from(mergedRating.entries())
              .sort((a, b) => b[1] - a[1])
              .map(([username, rating]) => ({ username, rating, gameCount: mergedCount.get(username) ?? 0 }))
          })
          // Don't pre-fill seeds — keep field empty so each click re-scrapes fresh seeds
          if (incoming.length === 0)
            setTopFetchError('Aucun nouveau joueur trouvé — baisse l\'Elo min ou change les seeds.')
        }
      } else {
        setTopFetchError(`Erreur backend HTTP ${res.status}`)
      }
    } catch (e) {
      setTopFetchError(`Erreur réseau : ${e instanceof Error ? e.message : String(e)}`)
    }
    setTopFetchDone(true)
    setTopFetching(false)
  }

  const handleDownloadPdn = async () => {
    const names = topFetchDone && filteredCorpusPlayers.length > 0
      ? filteredCorpusPlayers.map(p => p.username)
      : activeNames
    if (!names.length) return
    setPdnDownloading(true)
    setPdnMsg('')
    let allPdn = ''
    let gameCount = 0
    for (let i = 0; i < names.length; i++) {
      const username = names[i]
      setPdnMsg(`⬇️ ${username} (${i + 1}/${names.length}) — ${gameCount} parties…`)
      try {
        const maxParam = corpusMaxGames > 0 ? `?max=${corpusMaxGames}` : ''
        const resp = await fetch(
          `https://lidraughts.org/api/games/user/${encodeURIComponent(username)}${maxParam}`,
          { headers: { Accept: 'application/x-ndjson' } },
        )
        if (resp.ok) {
          const text = await resp.text()
          for (const line of text.split('\n')) {
            if (!line.trim()) continue
            try {
              const obj = JSON.parse(line)
              const moves = (obj.moves || obj.pdn || obj.pgn || '').trim()
              if (!moves) continue
              const wp = obj.players?.white ?? {}; const bp = obj.players?.black ?? {}
              const whiteName = wp.user?.name ?? wp.name ?? '?'
              const blackName = bp.user?.name ?? bp.name ?? '?'
              const whiteRating = wp.rating ?? wp.user?.rating
              const blackRating = bp.rating ?? bp.user?.rating
              const winner = obj.winner ?? ''
              const result = winner === 'white' ? '1-0' : winner === 'black' ? '0-1' : '1/2-1/2'
              let date: string | null = null
              if (obj.createdAt) {
                try { date = new Date(Number(obj.createdAt)).toISOString().split('T')[0] } catch { /* */ }
              }
              let pdn = `[Event "${obj.event ?? '?'}"]\n[White "${whiteName}"]\n[Black "${blackName}"]\n[Result "${result}"]\n`
              if (whiteRating) pdn += `[WhiteElo "${whiteRating}"]\n`
              if (blackRating) pdn += `[BlackElo "${blackRating}"]\n`
              if (date) pdn += `[Date "${date}"]\n`
              pdn += `\n${moves}\n\n`
              allPdn += pdn
              gameCount++
            } catch { /* skip malformed line */ }
          }
        }
      } catch { /* network error for this player */ }
    }
    if (allPdn.trim()) {
      const blob = new Blob([allPdn], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `corpus_nnue_${new Date().toISOString().split('T')[0]}.pdn`
      document.body.appendChild(a); a.click(); document.body.removeChild(a)
      URL.revokeObjectURL(url)
      setPdnMsg(`✓ ${gameCount.toLocaleString()} parties exportées`)
    } else {
      setPdnMsg('Aucune partie récupérée — vérifie les pseudos.')
    }
    setPdnDownloading(false)
  }

  const fetchCorpusStats = async () => {
    setCorpusLoading(true)
    try {
      const res = await fetch('/api/expert-games/stats')
      if (res.ok) setCorpusStats(await res.json())
    } catch { /* ignore */ } finally {
      setCorpusLoading(false)
    }
  }

  const checkDbInfo = async () => {
    setDbInfoLoading(true)
    try {
      const res = await fetch('/api/opening-book/db-info')
      if (res.ok) setDbInfo(await res.json())
    } catch { /* ignore */ } finally {
      setDbInfoLoading(false)
    }
  }

  const migrateLocalDb = async () => {
    setMigrating(true)
    setMigrateResult(null)
    try {
      const res = await fetch('/api/opening-book/migrate-local-db', { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setMigrateResult(data)
        // Refresh db-info to show updated counts
        await checkDbInfo()
      }
    } catch { /* ignore */ } finally {
      setMigrating(false)
    }
  }

  const handleReeval = async () => {
    setReevalRunning(true)
    setReevalMessage('')
    try {
      const res = await startReeval(msPerPos)
      if (res.started) {
        setReevalMessage(`✓ ${res.message}`)
        setStatus(null)
        startPolling()
      } else {
        setReevalMessage(res.message)
      }
    } catch {
      setReevalMessage('Erreur lors du lancement')
    } finally {
      setReevalRunning(false)
    }
  }

  useEffect(() => {
    getOpeningCacheBuildStatus().then(s => {
      setCacheSize(s.cache_size)
      if (s.status === 'running' || s.status === 'done' || s.status === 'error') setStatus(s)
    })
    return stopPolling
  }, [])

  const startPolling = () => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      const s = await getOpeningCacheBuildStatus()
      setStatus(s)
      setCacheSize(s.cache_size)
      if (s.status === 'done' || s.status === 'error') stopPolling()
    }, 2000)
  }

  const handleSearch = async (allPlayers = false) => {
    setSearchDone(false)
    setFoundPlayers([])
    setPoolSize(null)
    try {
      // count=0 fetches all players in the pool
      const { players, pool_size } = await fetchPlayersByRating(ratingMin, ratingMax, allPlayers ? 0 : playerCount)
      setFoundPlayers(players)
      setPoolSize(pool_size)
    } catch {
      setFoundPlayers([])
      setPoolSize(0)
    }
    setSearchDone(true)
  }

  const handleStart = async () => {
    const names = mode === 'manual'
      ? usernames.split('\n').map(u => u.trim()).filter(Boolean)
      : foundPlayers.map(p => p.username)
    if (!names.length) return
    setStarting(true)
    setFetchMessage('')

    try {
      let totalGames = 0
      let totalFens = 0
      let failCount = 0

      for (let i = 0; i < names.length; i++) {
        const username = names[i]
        setFetchMessage(`⬇️ ${username} (${i + 1}/${names.length}) — ${totalGames} parties, ${totalFens} pos…`)

        // Step 1: download from Lidraughts in browser (bypasses server-side block)
        let raw = ''
        try {
          const resp = await fetch(
            `https://lidraughts.org/api/games/user/${encodeURIComponent(username)}?max=${maxGames}`,
            { headers: { Accept: 'application/x-ndjson' } },
          )
          if (resp.ok) {
            const ct = resp.headers.get('content-type') ?? ''
            if (!ct.includes('html')) {
              raw = await resp.text()
            }
          }
        } catch { /* network/CORS error */ }

        if (!raw || raw.trim().length < 10) {
          failCount++
          continue
        }

        // Step 2: send this player's data to backend immediately (small POST)
        try {
          const result = await ingestPdn(raw, maxMoves)
          totalGames += result.games
          totalFens += result.fens_added
          if (result.games === 0) failCount++
        } catch {
          failCount++  // backend error on this player — continue with others
        }
      }

      if (totalFens === 0) {
        setFetchMessage('')
        alert(`Aucune position extraite (${failCount}/${names.length} joueurs en échec).\nVérifie les pseudos sur lidraughts.org.`)
        return
      }

      // Step 3: start Scan evaluation on all collected FENs
      setFetchMessage(`✓ ${totalGames} parties · ${totalFens} nouvelles positions · Lancement du calcul Scan…`)
      let evalRes: { started: boolean; message: string }
      try {
        evalRes = await startEval(msPerPos)
      } catch (err: unknown) {
        setFetchMessage('')
        const msg = err instanceof Error ? err.message : String(err)
        alert(`Erreur démarrage Scan:\n${msg}`)
        return
      }

      setFetchMessage('')
      if (evalRes.started) {
        setStatus(null)
        startPolling()
      } else {
        alert(evalRes.message)
      }
    } finally {
      setStarting(false)
    }
  }

  const isRunning = status?.status === 'running'
  const isDone = status?.status === 'done'
  const isError = status?.status === 'error'
  const progress = status && status.total_to_compute > 0
    ? Math.round((status.computed / status.total_to_compute) * 100)
    : null

  const activeNames = mode === 'manual'
    ? usernames.split('\n').filter(Boolean)
    : foundPlayers.map(p => p.username)

  const estMinutes = Math.ceil(activeNames.length * maxGames * 0.3 * msPerPos / 1000 / 60)

  const ELO_PRESETS = [
    { label: 'Débutant', min: 800, max: 1200 },
    { label: 'Intermédiaire', min: 1200, max: 1700 },
    { label: 'Avancé', min: 1700, max: 2100 },
    { label: 'Expert', min: 2100, max: 2500 },
  ]

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100">
      <div className="flex items-center gap-3 px-4 py-3 bg-gray-800 border-b border-gray-700 flex-shrink-0">
        <button onClick={onClose} className="text-gray-400 hover:text-amber-500 text-2xl w-9 h-9 flex items-center justify-center rounded-lg hover:bg-gray-700 transition-colors">←</button>
        <h2 className="font-bold text-amber-500 text-base flex-1">Base de connaissances ouvertures</h2>
        {cacheSize !== null && (
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cacheSize > 0 ? 'bg-green-900/60 text-green-300' : 'bg-gray-700 text-gray-400'}`}>
            <span className={`w-2 h-2 rounded-full ${cacheSize > 0 ? 'bg-green-400' : 'bg-gray-500'}`} />
            {cacheSize > 0 ? `${cacheSize.toLocaleString()} pos. en cache` : 'Cache vide'}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">

        {/* DB volume check */}
        <div className="bg-gray-800 rounded-lg p-3 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-300">Volume Railway (SQLite)</span>
            <button
              onClick={checkDbInfo}
              disabled={dbInfoLoading}
              className="text-xs px-2.5 py-1 rounded bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 transition-colors"
            >
              {dbInfoLoading ? 'Vérification…' : 'Vérifier'}
            </button>
          </div>
          {dbInfo && (
            <div className="text-xs font-mono space-y-1">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dbInfo.env_override ? 'bg-green-400' : 'bg-yellow-400'}`} />
                <span className="text-gray-400">Chemin :</span>
                <span className="text-white break-all">{dbInfo.db_path}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dbInfo.file_exists ? 'bg-green-400' : 'bg-red-400'}`} />
                <span className="text-gray-400">Fichier :</span>
                <span className={dbInfo.file_exists ? 'text-green-300' : 'text-red-300'}>
                  {dbInfo.file_exists
                    ? `${((dbInfo.file_size_bytes ?? 0) / 1024).toFixed(0)} Ko`
                    : 'introuvable'}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dbInfo.env_override ? 'bg-green-400' : 'bg-yellow-400'}`} />
                <span className="text-gray-400">Variable OPENING_BOOK_DB :</span>
                <span className={dbInfo.env_override ? 'text-green-300' : 'text-yellow-300'}>
                  {dbInfo.env_override ? 'définie ✓' : 'non définie (chemin par défaut)'}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dbInfo.positions > 0 ? 'bg-green-400' : 'bg-amber-400'}`} />
                <span className="text-gray-400">Positions :</span>
                <span className={dbInfo.positions > 0 ? 'text-green-300' : 'text-amber-300'}>
                  {dbInfo.positions.toLocaleString()} ({dbInfo.evaluated.toLocaleString()} évaluées)
                </span>
              </div>
            </div>
          )}

          {/* Re-evaluate interrupted Scan job */}
          {dbInfo && dbInfo.positions > 0 && dbInfo.evaluated < dbInfo.positions && (
            <div className="border-t border-gray-700 pt-2 mt-1 flex flex-col gap-1.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs text-amber-300 flex-1">
                  {(dbInfo.positions - dbInfo.evaluated).toLocaleString()} positions sans évaluation Scan
                </span>
                <button
                  onClick={handleReeval}
                  disabled={reevalRunning || isRunning}
                  className="text-xs px-2.5 py-1 rounded bg-amber-700 hover:bg-amber-600 disabled:opacity-50 transition-colors whitespace-nowrap"
                >
                  {reevalRunning ? 'Lancement…' : '▶ Reprendre l\'évaluation'}
                </button>
              </div>
              {reevalMessage && (
                <p className={`text-xs font-mono ${reevalMessage.startsWith('✓') ? 'text-green-300' : 'text-amber-300'}`}>
                  {reevalMessage}
                </p>
              )}
            </div>
          )}

          {/* Migration from old local DB */}
          {dbInfo && dbInfo.env_override && (
            <div className="border-t border-gray-700 pt-2 mt-1 flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">Récupérer l'ancienne DB locale&nbsp;→&nbsp;volume</span>
                <button
                  onClick={migrateLocalDb}
                  disabled={migrating}
                  className="text-xs px-2.5 py-1 rounded bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 transition-colors whitespace-nowrap"
                >
                  {migrating ? 'Migration…' : '📦 Migrer'}
                </button>
              </div>
              {migrateResult && (
                <div className="text-xs font-mono">
                  {migrateResult.status === 'ok' ? (
                    <span className="text-green-300">
                      ✓ {migrateResult.source_positions?.toLocaleString()} positions source · +{migrateResult.new_positions_added?.toLocaleString()} nouvelles · {migrateResult.continuations_merged?.toLocaleString()} continuations
                    </span>
                  ) : (
                    <span className="text-yellow-300">{migrateResult.message ?? migrateResult.status}</span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Mode toggle */}
        <div className="flex gap-1 bg-gray-800 p-1 rounded-lg">
          {(['manual', 'elo'] as SelectionMode[]).map(m => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`flex-1 py-1.5 rounded-md text-sm font-medium transition-colors ${
                mode === m ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              {m === 'manual' ? '✏️ Manuel' : '📊 Par niveau Elo'}
            </button>
          ))}
        </div>

        {/* Manual mode */}
        {mode === 'manual' && (
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Pseudos Lidraughts (un par ligne)</label>
            <textarea
              value={usernames}
              onChange={e => setUsernames(e.target.value)}
              disabled={isRunning}
              rows={4}
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white font-mono resize-none disabled:opacity-40"
              placeholder="el-negron&#10;pbp7055&#10;..."
            />
          </div>
        )}

        {/* Elo mode */}
        {mode === 'elo' && (
          <div className="flex flex-col gap-3">
            {/* Presets */}
            <div className="grid grid-cols-2 gap-2">
              {ELO_PRESETS.map(p => (
                <button
                  key={p.label}
                  onClick={() => { setRatingMin(p.min); setRatingMax(p.max) }}
                  className={`py-1.5 px-2 rounded-lg text-xs font-medium border transition-colors ${
                    ratingMin === p.min && ratingMax === p.max
                      ? 'bg-indigo-700 border-indigo-500 text-white'
                      : 'bg-gray-800 border-gray-600 text-gray-300 hover:border-indigo-500'
                  }`}
                >
                  {p.label}<br />
                  <span className="text-gray-400 font-normal">{p.min}–{p.max}</span>
                </button>
              ))}
            </div>

            {/* Custom range */}
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Elo min</label>
                <input
                  type="number"
                  value={ratingMin}
                  onChange={e => setRatingMin(Number(e.target.value))}
                  min={500} max={2800} step={50}
                  className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm text-white"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Elo max</label>
                <input
                  type="number"
                  value={ratingMax}
                  onChange={e => setRatingMax(Number(e.target.value))}
                  min={500} max={2800} step={50}
                  className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm text-white"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Nb joueurs</label>
                <input
                  type="number"
                  value={playerCount}
                  onChange={e => setPlayerCount(Number(e.target.value))}
                  min={1} max={500}
                  className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm text-white"
                />
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => handleSearch(false)}
                disabled={isRunning}
                className="flex-1 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm text-white font-medium disabled:opacity-40 transition-colors"
              >
                🔍 Échantillon aléatoire
              </button>
              <button
                onClick={() => handleSearch(true)}
                disabled={isRunning}
                className="flex-1 py-2 rounded-lg bg-indigo-800 hover:bg-indigo-700 text-sm text-white font-medium disabled:opacity-40 transition-colors"
              >
                📋 Tous les joueurs
              </button>
            </div>

            {searchDone && foundPlayers.length === 0 && (
              <p className="text-sm text-red-400 text-center">Aucun joueur trouvé dans cette plage. Essaie une plage plus large.</p>
            )}

            {foundPlayers.length > 0 && (
              <div className="bg-gray-800 rounded-xl p-3 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-gray-400">
                    {foundPlayers.length} joueur(s) sélectionné(s) aléatoirement
                  </p>
                  {poolSize !== null && (
                    <span className="text-xs text-gray-500">
                      pool : {poolSize} joueurs
                    </span>
                  )}
                </div>
                {poolSize !== null && poolSize < playerCount && (
                  <p className="text-xs text-amber-400">
                    ⚠️ Seulement {poolSize} joueurs disponibles dans cette tranche — agrandis la plage Elo ou réduis le nombre demandé.
                  </p>
                )}
                <div className="flex flex-wrap gap-1.5">
                  {foundPlayers.map(p => (
                    <span key={p.username} className="bg-gray-700 rounded-full px-2.5 py-0.5 text-xs text-white flex items-center gap-1">
                      {p.username}
                      <span className="text-indigo-400 font-mono">{p.rating}</span>
                    </span>
                  ))}
                </div>
                <button
                  onClick={() => handleSearch(false)}
                  className="text-xs text-gray-500 hover:text-gray-300 underline self-start"
                >
                  ↺ Piocher d'autres joueurs
                </button>
              </div>
            )}
          </div>
        )}

        {/* Shared config */}
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Parties/joueur</label>
            <select value={maxGames} onChange={e => setMaxGames(Number(e.target.value))} disabled={isRunning}
              className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm text-white disabled:opacity-40">
              {[50, 100, 200, 300, 500].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Coups max</label>
            <select value={maxMoves} onChange={e => setMaxMoves(Number(e.target.value))} disabled={isRunning}
              className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm text-white disabled:opacity-40">
              {[8, 10, 12, 15].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Temps/pos</label>
            <select value={msPerPos} onChange={e => setMsPerPos(Number(e.target.value))} disabled={isRunning}
              className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm text-white disabled:opacity-40">
              <option value={3000}>3s</option>
              <option value={5000}>5s</option>
              <option value={8000}>8s</option>
              <option value={10000}>10s</option>
            </select>
          </div>
        </div>

        {!isRunning && activeNames.length > 0 && (
          <p className="text-xs text-gray-500 text-center">
            {activeNames.length} joueur(s) · ~{estMinutes} min estimées (arrière-plan)
          </p>
        )}

        {/* Fetch progress */}
        {fetchMessage && (
          <p className="text-xs text-indigo-300 text-center animate-pulse">{fetchMessage}</p>
        )}

        {/* Start button */}
        <button
          onClick={handleStart}
          disabled={isRunning || starting || activeNames.length === 0}
          className="w-full py-3 rounded-lg bg-indigo-700 hover:bg-indigo-600 text-white font-semibold text-sm disabled:opacity-40 transition-colors"
        >
          {starting && fetchMessage ? '⬇️ Téléchargement…' : starting ? 'Démarrage…' : isRunning ? 'Calcul en cours…' : '🚀 Lancer le calcul'}
        </button>

        {/* Status */}
        {(status || cacheSize !== null) && (
          <div className="bg-gray-800 rounded-xl p-4 flex flex-col gap-3">
            {status && (
              <div className="flex items-center gap-2">
                {isRunning && <span className="w-3 h-3 rounded-full bg-indigo-400 animate-pulse flex-shrink-0" />}
                {isDone && <span className="text-green-400">✓</span>}
                {isError && <span className="text-red-400">✗</span>}
                {!isRunning && !isDone && !isError && <span className="text-gray-500">○</span>}
                <p className={`text-sm font-medium ${isDone ? 'text-green-300' : isError ? 'text-red-300' : 'text-gray-200'}`}>
                  {status.message || (cacheSize !== null && cacheSize > 0 ? `Cache actif — ${cacheSize.toLocaleString()} positions stockées` : 'Prêt')}
                </p>
              </div>
            )}
            {!status && cacheSize !== null && cacheSize > 0 && (
              <p className="text-sm font-medium text-green-300">✓ {cacheSize.toLocaleString()} positions en cache (serveur redémarré)</p>
            )}
            {progress !== null && (
              <div>
                <div className="flex justify-between text-xs text-gray-400 mb-1">
                  <span>Évaluation Scan</span>
                  <span>{status.computed} / {status.total_to_compute}</span>
                </div>
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-500 rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
                </div>
              </div>
            )}
            <div className="grid grid-cols-2 gap-2 text-xs">
              {([
                ['Parties téléchargées', status?.fetched_games ?? '—', 'text-white'],
                ['Positions uniques', status?.unique_positions ?? '—', 'text-white'],
                ['Calculées', status?.computed ?? '—', 'text-indigo-300'],
                ['Cache total', cacheSize ?? status?.cache_size ?? '—', 'text-amber-300'],
              ] as [string, number | string, string][]).map(([label, value, color]) => (
                <div key={label} className="bg-gray-900 rounded-lg px-3 py-2">
                  <div className="text-gray-500">{label}</div>
                  <div className={`font-bold text-base ${color}`}>{typeof value === 'number' ? value.toLocaleString() : value}</div>
                </div>
              ))}
            </div>
            {status && status.errors > 0 && <p className="text-xs text-red-400">{status.errors} erreur(s) ignorée(s)</p>}
          </div>
        )}

        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-3 text-xs text-gray-400 flex flex-col gap-1">
          <p>• Le calcul tourne en <strong className="text-gray-300">arrière-plan</strong> — tu peux utiliser l'app normalement</p>
          <p>• Les positions déjà en cache sont <strong className="text-gray-300">skippées</strong> automatiquement</p>
          <p>• Le cache est <strong className="text-gray-300">persistant</strong> sur le volume Railway</p>
          <p>• Plus tu ajoutes de joueurs, plus la base est riche</p>
        </div>

        {/* NNUE Corpus */}
        <div className="bg-gray-800 rounded-xl p-3 flex flex-col gap-2.5">
          <span className="text-xs font-semibold text-gray-300">Corpus NNUE (parties complètes)</span>

          {/* Step 1 — discovery params */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">
              Seeds (optionnel — vide = auto depuis lidraughts.org/player)
            </label>
            <input
              type="text"
              value={topSeeds}
              onChange={e => { setTopSeeds(e.target.value); setTopFetchDone(false) }}
              disabled={topFetching}
              placeholder="Laisser vide pour découverte automatique…"
              className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1.5 text-sm text-white font-mono disabled:opacity-40"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Elo min</label>
              <input type="number" value={topMinRating}
                onChange={e => { setTopMinRating(Number(e.target.value)); setTopFetchDone(false) }}
                min={800} max={2800} step={50} disabled={topFetching}
                className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1.5 text-sm text-white disabled:opacity-40" />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Nb joueurs max</label>
              <select value={topNb} onChange={e => { setTopNb(Number(e.target.value)); setTopFetchDone(false) }}
                disabled={topFetching}
                className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1.5 text-xs text-white disabled:opacity-40">
                <option value={100}>100</option>
                <option value={200}>200</option>
                <option value={300}>300</option>
                <option value={400}>400</option>
                <option value={500}>500</option>
              </select>
            </div>
          </div>

          <div className="flex gap-2">
          <button
            onClick={handleFetchTopPlayers}
            disabled={topFetching || pdnDownloading}
            className="flex-1 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium disabled:opacity-40 transition-colors"
          >
            {topFetching ? '⏳ Découverte en cours…' : topPlayers.length > 0 ? '🔍 Découvrir + cumuler' : '🔍 Découvrir les joueurs forts'}
          </button>
          {topPlayers.length > 0 && (
            <button
              onClick={() => { setTopPlayers([]); setTopFetchDone(false); setTopFetchError('') }}
              disabled={topFetching || pdnDownloading}
              className="px-3 py-2 rounded-lg bg-gray-700 hover:bg-red-900/60 text-gray-400 hover:text-red-300 text-sm disabled:opacity-40 transition-colors"
              title="Réinitialiser la liste"
            >
              ✕
            </button>
          )}
          </div>

          {topFetchDone && (
            <div className={`rounded-lg px-3 py-2 text-xs ${topPlayers.length > 0 ? 'bg-indigo-900/40 border border-indigo-700/50' : 'bg-red-900/30 border border-red-700/50'}`}>
              {topPlayers.length > 0 ? (
                <div className="flex flex-col gap-0.5 text-indigo-200">
                  <div>
                    <strong className="text-white">{topPlayers.length}</strong> joueurs ≥ {topMinRating} Elo
                    {topPlayers.some(p => p.rating !== null) && (
                      <span className="text-gray-400"> · {Math.min(...topPlayers.map(p => p.rating ?? 9999).filter(r => r < 9999))}–{Math.max(...topPlayers.map(p => p.rating ?? 0))}</span>
                    )}
                  </div>
                  <div className="text-emerald-300 font-medium">
                    {filteredTotalGames > 0
                      ? `~${filteredTotalGames.toLocaleString()} parties à télécharger${corpusMaxGames > 0 ? ` (max ${corpusMaxGames}/joueur)` : ''}`
                      : `Volume inconnu — comptes non encore récupérés`}
                  </div>
                </div>
              ) : (
                <span className="text-red-300">{topFetchError || 'Aucun joueur trouvé.'}</span>
              )}
            </div>
          )}

          {/* Step 2 — optional max Elo cap */}
          {topFetchDone && topPlayers.length > 0 && (
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-400 flex-shrink-0">Elo max (0 = sans limite)</label>
              <input type="number" value={corpusRatingMax}
                onChange={e => setCorpusRatingMax(Number(e.target.value))}
                min={0} max={2800} step={50}
                className="w-32 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-white" />
              {corpusRatingMax > 0 && (
                <span className="text-xs text-indigo-300">{filteredCorpusPlayers.length} joueurs</span>
              )}
            </div>
          )}

          {/* Step 3 — download */}
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 flex-shrink-0">Parties/joueur</label>
            <select value={corpusMaxGames} onChange={e => setCorpusMaxGames(Number(e.target.value))}
              disabled={pdnDownloading}
              className="flex-1 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-white disabled:opacity-40">
              <option value={0}>Toutes</option>
              <option value={500}>500</option>
              <option value={1000}>1 000</option>
              <option value={2000}>2 000</option>
            </select>
          </div>

          {pdnMsg && (
            <p className={`text-xs font-mono ${pdnMsg.startsWith('✓') ? 'text-green-300' : 'text-indigo-300 animate-pulse'}`}>
              {pdnMsg}
            </p>
          )}

          {(() => {
            const players = topFetchDone && filteredCorpusPlayers.length > 0
              ? filteredCorpusPlayers
              : topFetchDone && topPlayers.length > 0
                ? topPlayers
                : activeNames.map(n => ({ username: n, rating: null }))
            return (
              <button
                onClick={handleDownloadPdn}
                disabled={pdnDownloading || players.length === 0}
                className="w-full py-2 rounded-lg bg-indigo-700 hover:bg-indigo-600 text-white font-medium text-sm disabled:opacity-40 transition-colors"
              >
                {pdnDownloading
                  ? '⬇️ Téléchargement…'
                  : filteredTotalGames > 0
                    ? `⬇️ Télécharger .pdn (${players.length} joueurs · ~${filteredTotalGames.toLocaleString()} parties)`
                    : `⬇️ Télécharger .pdn (${players.length} joueurs · toutes leurs parties)`}
              </button>
            )
          })()}
          <p className="text-xs text-gray-500">
            Les parties sont téléchargées directement depuis Lidraughts et exportées en un seul fichier .pdn.
          </p>
        </div>

        {/* Export FENs */}
        <a
          href="/api/opening-book/export-fens"
          download="positions.fen"
          className="w-full flex items-center justify-center gap-2 bg-gray-700 hover:bg-gray-600 border border-gray-600 text-sm text-gray-200 rounded-xl px-4 py-2.5 transition-colors"
        >
          ⬇️ Exporter toutes les positions (.fen)
        </a>
      </div>
    </div>
  )
}
