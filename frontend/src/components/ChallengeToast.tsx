/**
 * Global notification surface for live PvP cross-screen events (J6).
 *
 * Mounted once at the App.tsx top level. Listens on the singleton WS
 * via `useLiveWS` for events that need user attention regardless of
 * which tab they're currently on:
 *
 *   challenge_received      → "Alice te défie ⚔️"  + Accepter / Refuser
 *   challenge_cancelled     → "Bob a annulé son défi"
 *   kicked_by_other_session → "Connexion reprise sur un autre onglet"
 *
 * Accepter posts to the REST endpoint then routes the user into the
 * Live tab — the game_started push will be handled by <LivePlayPanel>
 * which is already subscribed.
 *
 * The component renders nothing while no toast is pending, so it's
 * cheap to keep mounted. One toast slot at a time — successive
 * pushes replace the visible one rather than stacking (a stack would
 * need more layout work + dismiss-all UX for a feature that fires at
 * most once per few minutes).
 */

import { useCallback, useEffect, useState } from 'react'
import {
  respondLiveChallenge,
} from '../api/client'
import type { LiveChallenge } from '../api/client'
import { useLiveWS } from '../hooks/useLiveWS'

interface Props {
  /** Routes the user to the live tab when they accept a challenge. */
  onGoToLive: () => void
}

type ToastState =
  | { kind: 'challenge'; challenge: LiveChallenge }
  | { kind: 'info'; message: string }
  | null

export default function ChallengeToast({ onGoToLive }: Props) {
  const [toast, setToast] = useState<ToastState>(null)
  const [busy, setBusy] = useState(false)

  useLiveWS({
    on: {
      challenge_received: (m) => {
        const c = (m as unknown as { challenge: LiveChallenge }).challenge
        setToast({ kind: 'challenge', challenge: c })
      },
      challenge_cancelled: (m) => {
        const c = (m as unknown as { challenge: LiveChallenge }).challenge
        // Drop the challenge toast if it was for this exact challenge.
        setToast(prev =>
          prev?.kind === 'challenge' && prev.challenge.id === c.id
            ? { kind: 'info', message: `${c.challenger_username} a annulé son défi` }
            : prev,
        )
      },
      kicked_by_other_session: () => {
        setToast({
          kind: 'info',
          message: 'Connexion reprise sur un autre onglet ou appareil',
        })
      },
    },
  })

  // Auto-dismiss info toasts after 4 s. Challenge toasts stay until
  // the user explicitly accepts or refuses — they require action.
  useEffect(() => {
    if (toast?.kind !== 'info') return
    const id = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(id)
  }, [toast])

  const handleAccept = useCallback(async () => {
    if (toast?.kind !== 'challenge' || busy) return
    setBusy(true)
    try {
      await respondLiveChallenge(toast.challenge.id, true)
      setToast(null)
      onGoToLive()
    } catch {
      // Leave the toast up so the user can retry; the WS will likely
      // also push challenge_cancelled or similar to refresh state.
    } finally {
      setBusy(false)
    }
  }, [toast, busy, onGoToLive])

  const handleDecline = useCallback(async () => {
    if (toast?.kind !== 'challenge' || busy) return
    setBusy(true)
    try {
      await respondLiveChallenge(toast.challenge.id, false)
    } catch {
      // Same logic as accept — best-effort, leave the user a way out.
    } finally {
      setBusy(false)
      setToast(null)
    }
  }, [toast, busy])

  if (toast === null) return null

  // Common container: bottom-right floating card. Use inline styles +
  // the few app-wide Tailwind utilities so the toast doesn't depend
  // on the existing .toast class which is more terse than this needs.
  const containerStyle: React.CSSProperties = {
    position: 'fixed',
    bottom: 16,
    right: 16,
    maxWidth: 360,
    zIndex: 1000,
  }

  if (toast.kind === 'info') {
    return (
      <div
        style={containerStyle}
        className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 shadow-xl"
        role="status"
      >
        {toast.message}
      </div>
    )
  }

  // Challenge toast — needs action buttons.
  const c = toast.challenge
  return (
    <div
      style={containerStyle}
      className="bg-gray-800 border border-amber-600 rounded-lg p-3 shadow-xl flex flex-col gap-2"
      role="alertdialog"
      aria-label="Défi reçu"
    >
      <p className="text-sm text-gray-100">
        ⚔️ <span className="font-bold text-amber-300">{c.challenger_username}</span> te défie
      </p>
      <div className="flex gap-2 justify-end">
        <button
          onClick={handleDecline}
          disabled={busy}
          className="px-2 py-0.5 rounded text-xs bg-gray-700 hover:bg-gray-600 disabled:opacity-40 text-gray-200 cursor-pointer"
        >
          Refuser
        </button>
        <button
          onClick={handleAccept}
          disabled={busy}
          className="px-2 py-0.5 rounded text-xs bg-green-600 hover:bg-green-500 disabled:opacity-40 text-white cursor-pointer"
        >
          Accepter
        </button>
      </div>
    </div>
  )
}
