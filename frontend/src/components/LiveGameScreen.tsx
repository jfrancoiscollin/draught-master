/**
 * Live PvP game screen (J5).
 *
 * Wraps the existing `<Board>` component for an active live game.
 * Receives all state via WebSocket pushes: move_played, game_ended,
 * opponent_disconnected, opponent_reconnected, game_state (resume).
 * Sends `move` / `resign` frames through `sendLiveFrame`.
 *
 * When the game ends, surfaces a "🎓 Analyser cette partie" CTA that
 * pipes the finished game_id straight into the existing ImportGamePanel
 * pedagogy flow.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import Board from './Board'
import type { LiveGameSessionState } from '../api/client'
import { sendLiveFrame, useLiveWS } from '../hooks/useLiveWS'
import { useAuth } from '../contexts/AuthContext'
import { fenToBoard } from '../utils/fen'
import { getPositionLegalMoves } from '../api/client'
import type { MoveData } from '../types'

interface Props {
  session: LiveGameSessionState
  onLeave: () => void
  onAnalyzeFinishedGame: (gameId: string) => void
}

export default function LiveGameScreen({ session, onLeave, onAnalyzeFinishedGame }: Props) {
  const { user } = useAuth()
  const [sess, setSess] = useState<LiveGameSessionState>(session)
  const [legalMoves, setLegalMoves] = useState<MoveData[]>([])
  const [selectedSquare, setSelectedSquare] = useState<number | null>(null)
  const [oppDisconnected, setOppDisconnected] = useState<{ at: number; graceMs: number } | null>(null)
  const [statusMsg, setStatusMsg] = useState<string | null>(null)

  const mySide: 'white' | 'black' | null = user
    ? user.id === sess.white_user_id ? 'white'
    : user.id === sess.black_user_id ? 'black'
    : null
    : null
  const oppId = user?.id === sess.white_user_id ? sess.black_user_id : sess.white_user_id
  const isMyTurn = mySide !== null && mySide === sess.turn && sess.status === 'in_progress'
  const flipped = mySide === 'black'
  const board = useMemo(() => fenToBoard(sess.fen), [sess.fen])

  // Pull legal moves for the current position so the Board component can
  // surface them as clickable targets. Refresh whenever the FEN changes.
  useEffect(() => {
    if (sess.status !== 'in_progress' || !isMyTurn) {
      setLegalMoves([])
      return
    }
    let cancelled = false
    getPositionLegalMoves(sess.fen)
      .then(moves => { if (!cancelled) setLegalMoves(moves) })
      .catch(() => { if (!cancelled) setLegalMoves([]) })
    return () => { cancelled = true }
  }, [sess.fen, sess.status, isMyTurn])

  // WS subscriptions for this game's events.
  useLiveWS({
    on: {
      move_played: (m) => {
        const s = (m as unknown as { session: LiveGameSessionState }).session
        if (s.game_id === sess.game_id) {
          setSess(s)
          setSelectedSquare(null)
          setStatusMsg(null)
        }
      },
      game_ended: (m) => {
        const s = (m as unknown as { session: LiveGameSessionState }).session
        if (s.game_id === sess.game_id) {
          setSess(s)
          setOppDisconnected(null)
        }
      },
      game_state: (m) => {
        // Reconnect bootstrap — server pushes the latest snapshot.
        const s = (m as unknown as { session: LiveGameSessionState }).session
        if (s.game_id === sess.game_id) setSess(s)
      },
      opponent_disconnected: (m) => {
        const grace = (m as { grace_seconds?: number }).grace_seconds ?? 120
        setOppDisconnected({ at: Date.now(), graceMs: grace * 1000 })
      },
      opponent_reconnected: () => {
        setOppDisconnected(null)
        setStatusMsg('Adversaire reconnecté')
        setTimeout(() => setStatusMsg(null), 3000)
      },
      error: (m) => {
        const reason = (m as { reason?: string }).reason
        // Server-side validation errors on a move attempt. Drop the
        // selection so the user can try again.
        setStatusMsg(`Erreur : ${reason ?? 'inconnue'}`)
        setSelectedSquare(null)
        setTimeout(() => setStatusMsg(null), 3000)
      },
    },
  })

  const handleMove = useCallback((move: MoveData) => {
    if (!isMyTurn) return
    // Convert engine `path` to FMJD PDN — `from-to` for a simple move,
    // `from x to` for any capture (multi-jump shares the same shape;
    // only the endpoints feature in the canonical notation that
    // game_engine.move_to_pdn emits server-side).
    const from = move.path[0]
    const to = move.path[move.path.length - 1]
    const sep = move.captures.length > 0 ? 'x' : '-'
    const notation = `${from}${sep}${to}`
    const ok = sendLiveFrame({ type: 'move', move: notation })
    if (!ok) setStatusMsg('Connexion perdue, reconnexion…')
  }, [isMyTurn])

  const handleResign = useCallback(() => {
    if (sess.status !== 'in_progress') return
    if (!window.confirm('Abandonner la partie ?')) return
    const ok = sendLiveFrame({ type: 'resign' })
    if (!ok) setStatusMsg('Connexion perdue — réessaie dans un instant')
  }, [sess.status])

  // Countdown text for the disconnect grace banner.
  const [countdownText, setCountdownText] = useState('')
  useEffect(() => {
    if (oppDisconnected === null) { setCountdownText(''); return }
    const tick = () => {
      const remaining = Math.max(0, oppDisconnected.graceMs - (Date.now() - oppDisconnected.at))
      const s = Math.ceil(remaining / 1000)
      setCountdownText(s > 0 ? `${s}s avant forfait` : 'forfait imminent')
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [oppDisconnected])

  const finished = sess.status !== 'in_progress'
  const winnerLabel =
    sess.result === 'white' ? '⬜ Blancs gagnent'
    : sess.result === 'black' ? '⬛ Noirs gagnent'
    : sess.result === 'draw' ? '½–½ Nulle'
    : ''
  const endReason =
    sess.status === 'abandoned_white' ? 'Abandon des Blancs'
    : sess.status === 'abandoned_black' ? 'Abandon des Noirs'
    : sess.status === 'abandoned_server' ? 'Partie interrompue côté serveur'
    : sess.status === 'finished' ? 'Mat ou blocage'
    : ''

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-800 border-b border-gray-700">
        <button
          onClick={onLeave}
          className="text-gray-400 hover:text-amber-500 w-8 h-8 rounded-lg hover:bg-gray-700 cursor-pointer"
        >←</button>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-bold text-amber-500 truncate">
            Partie en ligne · {mySide === 'white' ? '⬜ tu joues les Blancs' : '⬛ tu joues les Noirs'}
          </p>
          <p className="text-xs text-gray-500 truncate">
            adversaire id {oppId}
          </p>
        </div>
      </div>

      {/* Status banners */}
      {oppDisconnected && (
        <div className="bg-red-900/30 border-b border-red-800/50 px-3 py-1.5 text-xs text-red-300">
          ⚠ Adversaire déconnecté · {countdownText}
        </div>
      )}
      {statusMsg && (
        <div className="bg-amber-900/30 border-b border-amber-800/50 px-3 py-1.5 text-xs text-amber-200">
          {statusMsg}
        </div>
      )}

      {/* Board + side panel */}
      <div className="flex flex-row items-start gap-2 p-2">
        <div className="flex-shrink-0" style={{ width: '60%', maxWidth: 280 }}>
          <Board
            board={board}
            legalMoves={legalMoves}
            onMove={handleMove}
            selectedSquare={selectedSquare}
            onSelectSquare={setSelectedSquare}
            disabled={!isMyTurn}
            flipped={flipped}
          />
        </div>
        <div className="flex-1 min-w-0 flex flex-col gap-2 text-xs">
          {!finished && (
            <div
              className={
                'px-2 py-1 rounded font-semibold text-center ' +
                (isMyTurn ? 'bg-amber-600/40 text-amber-100' : 'bg-gray-700 text-gray-300')
              }
            >
              {isMyTurn ? 'À toi de jouer' : 'Tour de l\'adversaire'}
            </div>
          )}
          {finished && (
            <div className="bg-gray-800 border border-gray-700 rounded px-2 py-2 flex flex-col gap-1.5">
              <span className="font-bold text-base text-amber-300">{winnerLabel}</span>
              <span className="text-gray-500">{endReason}</span>
              <button
                onClick={() => onAnalyzeFinishedGame(sess.game_id)}
                className="mt-1 py-1.5 rounded bg-indigo-700 hover:bg-indigo-600 text-white font-medium cursor-pointer"
              >
                🎓 Analyser cette partie
              </button>
            </div>
          )}
          {!finished && (
            <button
              onClick={handleResign}
              className="py-1 rounded bg-gray-800 hover:bg-red-800 border border-gray-700 text-gray-300 hover:text-red-200 transition-colors cursor-pointer"
            >
              Abandonner
            </button>
          )}
          <div className="text-gray-600 text-xs mt-1 font-mono break-all">
            {sess.pdn || '(début de partie)'}
          </div>
        </div>
      </div>
    </div>
  )
}
