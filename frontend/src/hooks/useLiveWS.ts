/**
 * Singleton WebSocket connection to /api/live/ws.
 *
 * One socket shared across the whole app. Components subscribe to message
 * types via `useLiveWS({ on: { challenge_received: handler, ... } })` and
 * unsubscribe on unmount. The hook auto-(re)connects whenever the auth
 * token is present in localStorage; reconnects use exponential backoff
 * capped at 30s.
 *
 * Heartbeat: a `ping` is emitted every 25s (server requires a frame
 * within ~30s to keep the connection responsive). The server replies
 * with `pong`, which we silently drop — no point waking the React
 * tree for heartbeat noise.
 *
 * Module-level state, not React state, by design: a per-component WS
 * would mean N connections for N mounted panels. The hook is the
 * subscription surface; the connection itself outlives any single
 * component's lifecycle (it persists across tab navigation in the
 * tab-only app shell).
 */

import { useEffect, useRef } from 'react'

// ── Wire-shape types (mirror backend/live/api.py message frames) ────────

export interface LiveMessage {
  type: string
  [k: string]: unknown
}

export type LiveHandler = (msg: LiveMessage) => void

// ── Module-level singleton state ────────────────────────────────────────

let ws: WebSocket | null = null
let connecting = false
let reconnectAttempts = 0
let pingInterval: ReturnType<typeof setInterval> | null = null
const handlers = new Map<string, Set<LiveHandler>>()
const wildcardHandlers = new Set<LiveHandler>()
let pendingReconnectTimer: ReturnType<typeof setTimeout> | null = null

function _backoffMs(): number {
  // 0.5s, 1s, 2s, 4s, 8s, capped at 30s. Caps the storm if the server
  // is bouncing during a redeploy.
  return Math.min(30_000, 500 * Math.pow(2, reconnectAttempts))
}

function _wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/api/live/ws`
}

function _dispatch(msg: LiveMessage) {
  for (const h of wildcardHandlers) {
    try { h(msg) } catch (e) { console.warn('live wildcard handler threw', e) }
  }
  const set = handlers.get(msg.type)
  if (!set) return
  for (const h of set) {
    try { h(msg) } catch (e) { console.warn(`live handler for ${msg.type} threw`, e) }
  }
}

function _stopHeartbeat() {
  if (pingInterval !== null) {
    clearInterval(pingInterval)
    pingInterval = null
  }
}

function _startHeartbeat() {
  _stopHeartbeat()
  pingInterval = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }))
    }
  }, 25_000)
}

function _scheduleReconnect() {
  if (pendingReconnectTimer !== null) return
  const delay = _backoffMs()
  pendingReconnectTimer = setTimeout(() => {
    pendingReconnectTimer = null
    reconnectAttempts += 1
    _connect()
  }, delay)
}

function _connect() {
  if (connecting || (ws && ws.readyState === WebSocket.OPEN)) return
  const token = localStorage.getItem('auth_token')
  if (!token) return  // no point opening a WS we can't auth
  connecting = true

  const sock = new WebSocket(_wsUrl())
  ws = sock

  sock.onopen = () => {
    sock.send(JSON.stringify({ type: 'auth', token }))
  }
  sock.onmessage = (evt) => {
    let msg: LiveMessage
    try { msg = JSON.parse(evt.data) } catch { return }
    if (msg.type === 'auth_ok') {
      connecting = false
      reconnectAttempts = 0
      _startHeartbeat()
    }
    if (msg.type === 'auth_error') {
      // Token is bad — there's no point retrying with the same one. Drop
      // and wait for whoever owns localStorage to provide a fresh token.
      console.warn('live ws auth_error:', (msg as { reason?: string }).reason)
      connecting = false
      _stopHeartbeat()
      sock.close()
      return
    }
    if (msg.type === 'pong') return  // heartbeat noise
    _dispatch(msg)
  }
  sock.onclose = () => {
    connecting = false
    _stopHeartbeat()
    if (ws === sock) ws = null
    // Don't loop on auth failures (the server closed us after auth_error).
    // For anything else, retry with backoff.
    _scheduleReconnect()
  }
  sock.onerror = () => {
    // The browser fires onerror without a useful payload; rely on
    // onclose to schedule the next attempt.
  }
}

/** Force a reconnect — useful after login when a fresh token lands. */
export function reconnectLiveWS() {
  reconnectAttempts = 0
  if (pendingReconnectTimer !== null) {
    clearTimeout(pendingReconnectTimer)
    pendingReconnectTimer = null
  }
  if (ws && ws.readyState <= WebSocket.OPEN) {
    try { ws.close() } catch { /* ignore */ }
  }
  _connect()
}

/** Send a JSON frame to the server. No-ops when disconnected — callers
 * fall back to REST for anything that's not strictly a hot-path move. */
export function sendLiveFrame(msg: LiveMessage): boolean {
  if (!ws || ws.readyState !== WebSocket.OPEN) return false
  try {
    ws.send(JSON.stringify(msg))
    return true
  } catch {
    return false
  }
}

// ── Hook ────────────────────────────────────────────────────────────────

export interface UseLiveWSOptions {
  /** Per-message-type handlers. Receives the full message. */
  on?: Record<string, LiveHandler>
  /** Catch-all — fires before the per-type handlers. */
  onAny?: LiveHandler
  /** Disable auto-connect for this mount (e.g. tests). */
  disabled?: boolean
}

export function useLiveWS({ on, onAny, disabled }: UseLiveWSOptions = {}) {
  // Stable refs so we can register a single handler per type and dispatch
  // through it; that way callers can pass inline closures without leaking
  // subscriptions on every render.
  const onRef = useRef(on)
  const onAnyRef = useRef(onAny)
  useEffect(() => { onRef.current = on }, [on])
  useEffect(() => { onAnyRef.current = onAny }, [onAny])

  useEffect(() => {
    if (disabled) return
    const types = Object.keys(onRef.current ?? {})
    const localHandlers: Array<[string, LiveHandler]> = types.map(t => [
      t,
      (msg) => onRef.current?.[t]?.(msg),
    ])
    const wildcard: LiveHandler = (msg) => onAnyRef.current?.(msg)
    for (const [t, h] of localHandlers) {
      if (!handlers.has(t)) handlers.set(t, new Set())
      handlers.get(t)!.add(h)
    }
    wildcardHandlers.add(wildcard)

    _connect()

    return () => {
      for (const [t, h] of localHandlers) handlers.get(t)?.delete(h)
      wildcardHandlers.delete(wildcard)
    }
    // Re-subscribe when the message-type set changes (referential
    // identity check on the keys array).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disabled, JSON.stringify(Object.keys(on ?? {}))])
}
