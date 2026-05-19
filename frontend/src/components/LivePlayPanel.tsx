/**
 * Live PvP lobby (J5).
 *
 * Shows three queues — defi sent, defi received, partie en cours — plus
 * the "Défier un joueur" input. WebSocket pushes (challenge_received /
 * _resolved / _cancelled, game_started) update the lists live; the
 * pending-challenges endpoint is fetched once on mount for cold-start.
 *
 * When a game_started push arrives, the caller's `onEnterGame` is
 * invoked with the session payload so the parent (App.tsx) can swap to
 * the live game screen.
 */

import { useCallback, useEffect, useState } from 'react'
import {
  cancelLiveChallenge,
  createLiveChallenge,
  getPendingLiveChallenges,
  respondLiveChallenge,
} from '../api/client'
import type { LiveChallenge, LiveGameSessionState, PreferredColor } from '../api/client'
import { useLiveWS } from '../hooks/useLiveWS'

interface Props {
  onEnterGame: (session: LiveGameSessionState) => void
}

const COLOR_LABEL: Record<PreferredColor, string> = {
  white: '⬜ Blancs',
  black: '⬛ Noirs',
  random: '🎲 Aléatoire',
}

export default function LivePlayPanel({ onEnterGame }: Props) {
  const [opponent, setOpponent] = useState('')
  const [preferred, setPreferred] = useState<PreferredColor>('random')
  const [received, setReceived] = useState<LiveChallenge[]>([])
  const [sent, setSent] = useState<LiveChallenge[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Bootstrap from REST so users who land here without an open WS still
  // see their pending challenges. Subsequent updates come over WS.
  useEffect(() => {
    let cancelled = false
    getPendingLiveChallenges()
      .then(data => {
        if (cancelled) return
        setReceived(data.received)
        setSent(data.sent)
      })
      .catch(() => { /* offline / 401 — leave lists empty */ })
    return () => { cancelled = true }
  }, [])

  // Live updates.
  useLiveWS({
    on: {
      challenge_received: (m) => {
        const c = (m as unknown as { challenge: LiveChallenge }).challenge
        setReceived(prev => prev.find(x => x.id === c.id) ? prev : [c, ...prev])
      },
      challenge_resolved: (m) => {
        // I'm the challenger; the row just moved out of pending.
        const c = (m as unknown as { challenge: LiveChallenge }).challenge
        setSent(prev => prev.filter(x => x.id !== c.id))
      },
      challenge_cancelled: (m) => {
        // I'm the opponent; the challenger withdrew.
        const c = (m as unknown as { challenge: LiveChallenge }).challenge
        setReceived(prev => prev.filter(x => x.id !== c.id))
      },
      game_started: (m) => {
        const sess = (m as unknown as { session: LiveGameSessionState }).session
        onEnterGame(sess)
      },
    },
  })

  const handleChallenge = useCallback(async () => {
    const name = opponent.trim()
    if (!name) return
    setBusy(true)
    setError(null)
    try {
      const c = await createLiveChallenge(name, preferred)
      setSent(prev => [c, ...prev])
      setOpponent('')
    } catch (e) {
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'Erreur réseau'
      setError(String(detail))
    } finally {
      setBusy(false)
    }
  }, [opponent, preferred])

  const handleRespond = useCallback(async (id: string, accept: boolean) => {
    setBusy(true)
    setError(null)
    try {
      await respondLiveChallenge(id, accept)
      setReceived(prev => prev.filter(c => c.id !== id))
      // The game_started push (if accept) lands via the WS handler
      // wired above — no need to navigate from here.
    } catch (e) {
      setError(String((e as Error).message ?? e))
    } finally {
      setBusy(false)
    }
  }, [])

  const handleCancel = useCallback(async (id: string) => {
    setBusy(true)
    setError(null)
    try {
      await cancelLiveChallenge(id)
      setSent(prev => prev.filter(c => c.id !== id))
    } catch (e) {
      setError(String((e as Error).message ?? e))
    } finally {
      setBusy(false)
    }
  }, [])

  return (
    <div className="flex flex-col gap-4 p-4 max-w-2xl mx-auto">
      <h2 className="text-lg font-bold text-amber-500">Jouer en ligne</h2>

      {/* Challenge form */}
      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-3 flex flex-col gap-2">
        <span className="text-xs font-semibold text-gray-300">Défier un joueur</span>
        <div className="flex gap-2 flex-wrap">
          <input
            type="text"
            value={opponent}
            onChange={e => setOpponent(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleChallenge() }}
            placeholder="username"
            disabled={busy}
            className="flex-1 min-w-[8rem] bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm text-white"
          />
          <select
            value={preferred}
            onChange={e => setPreferred(e.target.value as PreferredColor)}
            disabled={busy}
            className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm text-white"
          >
            <option value="random">🎲 Aléatoire</option>
            <option value="white">⬜ Blancs</option>
            <option value="black">⬛ Noirs</option>
          </select>
          <button
            onClick={handleChallenge}
            disabled={busy || !opponent.trim()}
            className="px-3 py-1 rounded bg-amber-600 hover:bg-amber-500 disabled:opacity-40 text-white text-sm font-medium cursor-pointer"
          >
            Défier
          </button>
        </div>
        {error && (
          <p className="text-xs text-red-400 break-words">{error}</p>
        )}
      </div>

      {/* Received challenges */}
      <section className="bg-gray-800/50 border border-gray-700 rounded-xl p-3 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-300">Défis reçus</span>
          <span className="text-xs text-gray-500">{received.length}</span>
        </div>
        {received.length === 0 ? (
          <p className="text-xs text-gray-500 italic">Personne ne te défie pour le moment.</p>
        ) : (
          received.map(c => (
            <div key={c.id} className="flex items-center gap-2 text-xs">
              <span className="flex-1 truncate text-gray-200">
                <span className="font-bold text-amber-300">{c.challenger_username}</span>
                <span className="text-gray-500"> · {COLOR_LABEL[c.preferred_color]}</span>
              </span>
              <button
                onClick={() => handleRespond(c.id, true)}
                disabled={busy}
                className="px-2 py-0.5 rounded bg-green-600 hover:bg-green-500 disabled:opacity-40 text-white cursor-pointer"
              >
                Accepter
              </button>
              <button
                onClick={() => handleRespond(c.id, false)}
                disabled={busy}
                className="px-2 py-0.5 rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-40 text-gray-200 cursor-pointer"
              >
                Refuser
              </button>
            </div>
          ))
        )}
      </section>

      {/* Sent challenges */}
      <section className="bg-gray-800/50 border border-gray-700 rounded-xl p-3 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-300">Défis envoyés</span>
          <span className="text-xs text-gray-500">{sent.length}</span>
        </div>
        {sent.length === 0 ? (
          <p className="text-xs text-gray-500 italic">Aucun défi en attente.</p>
        ) : (
          sent.map(c => (
            <div key={c.id} className="flex items-center gap-2 text-xs">
              <span className="flex-1 truncate text-gray-300">
                <span className="text-gray-500">vers </span>
                <span className="font-bold text-amber-300">{c.opponent_username}</span>
                <span className="text-gray-500"> · {COLOR_LABEL[c.preferred_color]}</span>
              </span>
              <button
                onClick={() => handleCancel(c.id)}
                disabled={busy}
                className="px-2 py-0.5 rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-40 text-gray-200 cursor-pointer"
              >
                Annuler
              </button>
            </div>
          ))
        )}
      </section>
    </div>
  )
}
