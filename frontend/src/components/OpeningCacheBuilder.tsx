import React, { useState, useEffect, useRef } from 'react'
import { startOpeningCacheBuild, getOpeningCacheBuildStatus, findPlayersByRating } from '../api/client'

interface Props {
  onClose: () => void
}

type SelectionMode = 'manual' | 'elo'

export default function OpeningCacheBuilder({ onClose }: Props) {
  const [mode, setMode] = useState<SelectionMode>('manual')

  // Manual mode
  const [usernames, setUsernames] = useState('el-negron\npbp7055')

  // Elo mode
  const [ratingMin, setRatingMin] = useState(1800)
  const [ratingMax, setRatingMax] = useState(2300)
  const [playerCount, setPlayerCount] = useState(10)
  const [foundPlayers, setFoundPlayers] = useState<{ username: string; rating: number }[]>([])
  const [searching, setSearching] = useState(false)
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

  const handleSearch = async () => {
    setSearching(true)
    setSearchDone(false)
    setFoundPlayers([])
    try {
      const res = await findPlayersByRating(ratingMin, ratingMax, playerCount)
      setFoundPlayers(res.players)
      setSearchDone(true)
    } catch {
      setFoundPlayers([])
      setSearchDone(true)
    } finally {
      setSearching(false)
    }
  }

  const handleStart = async () => {
    const names = mode === 'manual'
      ? usernames.split('\n').map(u => u.trim()).filter(Boolean)
      : foundPlayers.map(p => p.username)
    if (!names.length) return
    setStarting(true)
    try {
      const res = await startOpeningCacheBuild({
        usernames: names,
        max_games_per_user: maxGames,
        max_moves: maxMoves,
        ms_per_position: msPerPos,
      })
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
              disabled={searching || isRunning}
              className="w-full py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm text-white font-medium disabled:opacity-40 transition-colors"
            >
              {searching ? '🔍 Recherche en cours…' : '🔍 Chercher des joueurs'}
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

        {/* Start button */}
        <button
          onClick={handleStart}
          disabled={isRunning || starting || activeNames.length === 0}
          className="w-full py-3 rounded-lg bg-indigo-700 hover:bg-indigo-600 text-white font-semibold text-sm disabled:opacity-40 transition-colors"
        >
          {starting ? 'Démarrage…' : isRunning ? 'Calcul en cours…' : '🚀 Lancer le calcul'}
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
