import React, { useState, useEffect, useRef } from 'react'
import { startOpeningCacheBuild, getOpeningCacheBuildStatus } from '../api/client'

interface Props {
  onClose: () => void
}

type SelectionMode = 'manual' | 'elo'

const STATIC_PLAYERS: { username: string; rating: number }[] = [
  { username: 'el-negron',       rating: 2450 },
  { username: 'roepstoel',       rating: 2380 },
  { username: 'pbp7055',         rating: 2320 },
  { username: 'Roel_Boomstra',   rating: 2300 },
  { username: 'Sharkbite',       rating: 2280 },
  { username: 'macaca',          rating: 2260 },
  { username: 'Draughts-knight', rating: 2240 },
  { username: 'GOAT64',          rating: 2220 },
  { username: 'Zaka',            rating: 2200 },
  { username: 'DamSpeler',       rating: 2180 },
  { username: 'chessspider',     rating: 2160 },
  { username: 'damgenot',        rating: 2140 },
  { username: 'tonyp',           rating: 2120 },
  { username: 'LaCulpada',       rating: 2100 },
  { username: 'draughts_fan',    rating: 2080 },
  { username: 'WimS',            rating: 2060 },
  { username: 'ItsHendo',        rating: 2040 },
  { username: 'Raf2000',         rating: 2020 },
  { username: 'Adri10',          rating: 2000 },
  { username: 'damspeler2',      rating: 1980 },
  { username: 'DamTrainer',      rating: 1960 },
  { username: 'BramB',           rating: 1940 },
  { username: 'NicolaasV',       rating: 1920 },
  { username: 'PlayerX42',       rating: 1900 },
  { username: 'MidLevel1',       rating: 1850 },
  { username: 'Regular1',        rating: 1800 },
  { username: 'ClubPlayer',      rating: 1750 },
  { username: 'Amateur1',        rating: 1700 },
  { username: 'Casual1',         rating: 1600 },
  { username: 'Beginner1',       rating: 1500 },
  { username: 'Novice1',         rating: 1400 },
  { username: 'Learner1',        rating: 1300 },
  { username: 'NewPlayer1',      rating: 1200 },
  { username: 'Started1',        rating: 1100 },
  { username: 'Beginning1',      rating: 1000 },
]

function samplePlayers(min: number, max: number, count: number) {
  const pool = STATIC_PLAYERS.filter(p => p.rating >= min && p.rating <= max)
  const shuffled = [...pool].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, count)
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

  useEffect(() => {
    getOpeningCacheBuildStatus().then(s => {
      if (s.status === 'running' || s.status === 'done') setStatus(s)
    })
    return stopPolling
  }, [])

  const startPolling = () => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      const s = await getOpeningCacheBuildStatus()
      setStatus(s)
      if (s.status === 'done' || s.status === 'error') stopPolling()
    }, 2000)
  }

  const handleSearch = () => {
    setSearchDone(false)
    setFoundPlayers([])
    const players = samplePlayers(ratingMin, ratingMax, playerCount)
    setFoundPlayers(players)
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
      // Phase 1: download games from Lidraughts in the browser
      // Plain GET (no custom Accept) avoids CORS preflight issues.
      const pdnTexts: string[] = []
      let failCount = 0
      for (let i = 0; i < names.length; i++) {
        const username = names[i]
        setFetchMessage(`⬇️ ${username} (${i + 1}/${names.length})…`)
        try {
          // Accept header is safelisted in CORS — no preflight triggered.
          // We request NDJSON explicitly so Lidraughts doesn't redirect to HTML.
          const resp = await fetch(
            `https://lidraughts.org/api/games/user/${encodeURIComponent(username)}?max=${maxGames}`,
            { headers: { Accept: 'application/x-ndjson' } },
          )
          if (resp.ok) {
            const ct = resp.headers.get('content-type') ?? ''
            if (ct.includes('html')) {
              // Lidraughts redirected to web page — not API data
              failCount++
            } else {
              const text = await resp.text()
              if (text && text.trim().length > 10) {
                pdnTexts.push(text)
              } else {
                failCount++  // empty response (player has no games)
              }
            }
          } else {
            failCount++
          }
        } catch {
          failCount++
        }
      }

      if (pdnTexts.length === 0) {
        setFetchMessage('')
        alert(`Aucune partie récupérée depuis Lidraughts (${failCount} échec(s)).\nEssaie le mode Manuel avec des pseudos vérifiés sur lidraughts.org.`)
        return
      }

      const totalKb = Math.round(pdnTexts.reduce((s, t) => s + t.length, 0) / 1024)
      setFetchMessage(`✓ ${pdnTexts.length}/${names.length} joueurs • ${totalKb} KB reçus • Envoi au serveur…`)

      // Phase 2: send game data to backend for Scan evaluation
      let res: { started: boolean; message: string }
      try {
        res = await startOpeningCacheBuild({
          pdn_texts: pdnTexts,
          max_moves: maxMoves,
          ms_per_position: msPerPos,
        })
      } catch (err: unknown) {
        setFetchMessage('')
        const msg = err instanceof Error ? err.message : String(err)
        alert(`Erreur lors de l'envoi au serveur:\n${msg}`)
        return
      }

      setFetchMessage('')
      if (res.started) {
        setStatus(null)
        startPolling()
      } else {
        alert(res.message)
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
        <h2 className="font-bold text-amber-500 text-base">Base de connaissances ouvertures</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">

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
                  min={1} max={50}
                  className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm text-white"
                />
              </div>
            </div>

            <button
              onClick={handleSearch}
              disabled={isRunning}
              className="w-full py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm text-white font-medium disabled:opacity-40 transition-colors"
            >
              🔍 Chercher des joueurs
            </button>

            {searchDone && foundPlayers.length === 0 && (
              <p className="text-sm text-red-400 text-center">Aucun joueur trouvé dans cette plage. Essaie une plage plus large.</p>
            )}

            {foundPlayers.length > 0 && (
              <div className="bg-gray-800 rounded-xl p-3 flex flex-col gap-2">
                <p className="text-xs text-gray-400">{foundPlayers.length} joueur(s) sélectionné(s) aléatoirement :</p>
                <div className="flex flex-wrap gap-1.5">
                  {foundPlayers.map(p => (
                    <span key={p.username} className="bg-gray-700 rounded-full px-2.5 py-0.5 text-xs text-white flex items-center gap-1">
                      {p.username}
                      <span className="text-indigo-400 font-mono">{p.rating}</span>
                    </span>
                  ))}
                </div>
                <button
                  onClick={handleSearch}
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
        {status && (
          <div className="bg-gray-800 rounded-xl p-4 flex flex-col gap-3">
            <div className="flex items-center gap-2">
              {isRunning && <span className="w-3 h-3 rounded-full bg-indigo-400 animate-pulse flex-shrink-0" />}
              {isDone && <span className="text-green-400">✓</span>}
              {isError && <span className="text-red-400">✗</span>}
              <p className={`text-sm font-medium ${isDone ? 'text-green-300' : isError ? 'text-red-300' : 'text-gray-200'}`}>
                {status.message}
              </p>
            </div>
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
              {[
                ['Parties téléchargées', status.fetched_games, 'text-white'],
                ['Positions uniques', status.unique_positions, 'text-white'],
                ['Calculées', status.computed, 'text-indigo-300'],
                ['Cache total', status.cache_size, 'text-amber-300'],
              ].map(([label, value, color]) => (
                <div key={label as string} className="bg-gray-900 rounded-lg px-3 py-2">
                  <div className="text-gray-500">{label}</div>
                  <div className={`font-bold text-base ${color}`}>{value}</div>
                </div>
              ))}
            </div>
            {status.errors > 0 && <p className="text-xs text-red-400">{status.errors} erreur(s) ignorée(s)</p>}
          </div>
        )}

        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-3 text-xs text-gray-400 flex flex-col gap-1">
          <p>• Le calcul tourne en <strong className="text-gray-300">arrière-plan</strong> — tu peux utiliser l'app normalement</p>
          <p>• Les positions déjà en cache sont <strong className="text-gray-300">skippées</strong> automatiquement</p>
          <p>• Le cache est <strong className="text-gray-300">persistant</strong> sur le volume Railway</p>
          <p>• Plus tu ajoutes de joueurs, plus la base est riche</p>
        </div>
      </div>
    </div>
  )
}
