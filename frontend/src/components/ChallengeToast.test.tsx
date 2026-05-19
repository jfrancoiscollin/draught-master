/**
 * Tests for the global ChallengeToast (J6).
 *
 * Mocks the singleton `useLiveWS` hook so the test can synthesise
 * WS pushes without spinning a real socket. The component under test
 * is shallow: it renders a fixed-position div whose content depends
 * on the most recent push, plus two action buttons for the
 * challenge-toast variant.
 */
import { describe, it, expect, vi, beforeAll } from 'vitest'
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react'

import ChallengeToast from './ChallengeToast'
import type { LiveChallenge } from '../api/client'
import * as client from '../api/client'

// We capture the most recent options the component passed to useLiveWS
// so tests can fire handlers as if a WS frame had landed.
let lastHandlers: Record<string, (msg: unknown) => void> = {}

vi.mock('../hooks/useLiveWS', () => ({
  useLiveWS: (opts: { on?: Record<string, (msg: unknown) => void> } = {}) => {
    lastHandlers = opts.on ?? {}
  },
}))

const challenge = (over: Partial<LiveChallenge> = {}): LiveChallenge => ({
  id: 'c-1',
  challenger_id: 1,
  challenger_username: 'alice',
  opponent_id: 2,
  opponent_username: 'bob',
  preferred_color: 'random',
  status: 'pending',
  created_at: '2026-05-19T16:00:00Z',
  resolved_at: null,
  game_id: null,
  ...over,
})

beforeAll(() => {
  // The component sets a 4s auto-dismiss timeout for info toasts;
  // tests that touch that path use vi.useFakeTimers locally.
})

describe('ChallengeToast', () => {
  it('renders nothing by default', () => {
    const onGoToLive = vi.fn()
    const { container } = render(<ChallengeToast onGoToLive={onGoToLive} />)
    expect(container.firstChild).toBeNull()
  })

  it('surfaces a challenge_received push as an action toast', () => {
    render(<ChallengeToast onGoToLive={vi.fn()} />)
    act(() => lastHandlers.challenge_received({ type: 'challenge_received', challenge: challenge() }))

    expect(screen.getByText(/alice/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Accepter/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Refuser/i })).toBeInTheDocument()
  })

  it('accept calls respondLiveChallenge then onGoToLive', async () => {
    const respond = vi.spyOn(client, 'respondLiveChallenge').mockResolvedValueOnce(
      challenge({ status: 'accepted' }),
    )
    const onGoToLive = vi.fn()
    render(<ChallengeToast onGoToLive={onGoToLive} />)
    act(() => lastHandlers.challenge_received({ type: 'challenge_received', challenge: challenge() }))

    fireEvent.click(screen.getByRole('button', { name: /Accepter/i }))

    await waitFor(() => expect(respond).toHaveBeenCalledWith('c-1', true))
    await waitFor(() => expect(onGoToLive).toHaveBeenCalledTimes(1))
  })

  it('decline calls respondLiveChallenge with false and dismisses the toast', async () => {
    const respond = vi.spyOn(client, 'respondLiveChallenge').mockResolvedValueOnce(
      challenge({ status: 'declined' }),
    )
    const onGoToLive = vi.fn()
    const { container } = render(<ChallengeToast onGoToLive={onGoToLive} />)
    act(() => lastHandlers.challenge_received({ type: 'challenge_received', challenge: challenge() }))

    fireEvent.click(screen.getByRole('button', { name: /Refuser/i }))

    await waitFor(() => expect(respond).toHaveBeenCalledWith('c-1', false))
    await waitFor(() => expect(container.firstChild).toBeNull())
    expect(onGoToLive).not.toHaveBeenCalled()
  })

  it('challenge_cancelled replaces a matching challenge toast with an info banner', () => {
    render(<ChallengeToast onGoToLive={vi.fn()} />)
    const c = challenge()
    act(() => lastHandlers.challenge_received({ type: 'challenge_received', challenge: c }))
    expect(screen.getByRole('button', { name: /Accepter/i })).toBeInTheDocument()

    act(() => lastHandlers.challenge_cancelled({ type: 'challenge_cancelled', challenge: c }))
    expect(screen.queryByRole('button', { name: /Accepter/i })).toBeNull()
    expect(screen.getByText(/a annulé son défi/i)).toBeInTheDocument()
  })

  it('kicked_by_other_session shows an info banner', () => {
    render(<ChallengeToast onGoToLive={vi.fn()} />)
    act(() => lastHandlers.kicked_by_other_session({ type: 'kicked_by_other_session' }))
    expect(screen.getByText(/Connexion reprise/i)).toBeInTheDocument()
  })
})
