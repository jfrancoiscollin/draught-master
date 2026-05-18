/**
 * Tests for the PedagogyPanel ↔ board two-way binding (commit 6005ac5).
 *
 * The panel renders a list of verdict rows. Two behaviours under test:
 *   (1) clicking a row body calls `onJumpTo(move_number)` so the board
 *       can scrub to that half-move,
 *   (2) `currentHalfMove` highlights the matching row,
 *   (3) the expand chevron only toggles the explanation — clicking it
 *       does NOT call `onJumpTo` (stopPropagation is wired correctly).
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import PedagogyPanel from './PedagogyPanel'
import type { PedagogyAnalysis, VerdictOut } from '../api/client'
import * as client from '../api/client'

// ---------------------------------------------------------------------------
// Fixture — minimal valid PedagogyAnalysis with two verdicts on the same
// side of the board (white) so the layout is deterministic.
// ---------------------------------------------------------------------------

const verdict = (over: Partial<VerdictOut> = {}): VerdictOut => ({
  move_number: 1,
  side: 'white',
  move_notation: '33-28',
  fen_before: 'W:Wxxxx:Bxxxx',
  fen_after: 'B:Wxxxx:Bxxxx',
  score_before: 0,
  score_after: 0,
  delta_winchance: 0,
  verdict: 'best',
  is_forced: false,
  phase: 'opening',
  motifs: [],
  material_balance: 0,
  hanging_pieces_white: [],
  hanging_pieces_black: [],
  isolated_pawns_white: [],
  isolated_pawns_black: [],
  backward_pawns_white: [],
  backward_pawns_black: [],
  holes_white: [],
  holes_black: [],
  outposts_white: [],
  outposts_black: [],
  formations: [],
  ...over,
})

const ANALYSIS: PedagogyAnalysis = {
  game_id: 'g1',
  verdicts: [
    verdict({ move_number: 1, move_notation: '33-28' }),
    verdict({ move_number: 3, move_notation: '37-31', verdict: 'inaccuracy', delta_winchance: 0.05 }),
  ],
  summary: {
    total_half_moves: 2,
    blunders: 0,
    mistakes: 0,
    average_accuracy: 0.92,
    user_side: 'white',
  },
}

// scrollIntoView isn't in jsdom — stub so the highlighted-row effect
// doesn't crash the render.
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

// ---------------------------------------------------------------------------

describe('PedagogyPanel — verdict row ↔ board binding', () => {
  it('clicking a row body calls onJumpTo with the row half-move', async () => {
    const user = userEvent.setup()
    const onJumpTo = vi.fn()

    render(
      <PedagogyPanel
        gameId="g1"
        analysis={ANALYSIS}
        loading={false}
        userSide="white"
        lang="fr"
        onAnalyze={() => {}}
        onJumpTo={onJumpTo}
      />
    )

    // Click on the second row's main body (the "Aller à cette position" button)
    const rowButtons = screen.getAllByTitle('Aller à cette position')
    expect(rowButtons).toHaveLength(2)
    await user.click(rowButtons[1])

    expect(onJumpTo).toHaveBeenCalledTimes(1)
    expect(onJumpTo).toHaveBeenCalledWith(3)
  })

  it('currentHalfMove highlights the matching row', () => {
    render(
      <PedagogyPanel
        gameId="g1"
        analysis={ANALYSIS}
        loading={false}
        userSide="white"
        lang="fr"
        onAnalyze={() => {}}
        currentHalfMove={3}
      />
    )

    // The active row's wrapper carries the amber background class.
    // Pull all row wrappers via their notation cells, then walk up to the
    // outermost div that the panel applies the highlight class to.
    const allRowButtons = screen.getAllByTitle('Aller à cette position')
    const activeRowWrapper = allRowButtons[1].closest('.bg-amber-700\\/30')
    const inactiveRowWrapper = allRowButtons[0].closest('.bg-amber-700\\/30')

    expect(activeRowWrapper).not.toBeNull()
    expect(inactiveRowWrapper).toBeNull()
  })

  it('expanded row surfaces "not-analyzed" message on 404', async () => {
    // Simulate the backend's 404 ("Verdict not yet computed for this
    // move") — e.g. user clicked Expliquer before bulk-analysing the game,
    // or the analysis was reset.
    vi.spyOn(client, 'explainMovePedagogy').mockResolvedValueOnce({
      kind: 'not-analyzed',
    })
    const user = userEvent.setup()

    render(
      <PedagogyPanel
        gameId="g1"
        analysis={ANALYSIS}
        loading={false}
        userSide="white"
        lang="fr"
        onAnalyze={() => {}}
      />
    )

    const chevrons = screen.getAllByTitle('Déplier')
    await user.click(chevrons[0])

    await waitFor(() => {
      expect(
        screen.getByText(/Lance d'abord l'analyse pédagogique/i),
      ).toBeInTheDocument()
    })
  })

  it('chevron click only toggles expand — does not call onJumpTo', async () => {
    const user = userEvent.setup()
    const onJumpTo = vi.fn()

    render(
      <PedagogyPanel
        gameId="g1"
        analysis={ANALYSIS}
        loading={false}
        userSide="white"
        lang="fr"
        onAnalyze={() => {}}
        onJumpTo={onJumpTo}
      />
    )

    // The chevron is the small button with title "Déplier" (collapsed).
    const chevrons = screen.getAllByTitle('Déplier')
    expect(chevrons.length).toBeGreaterThan(0)
    await user.click(chevrons[0])

    expect(onJumpTo).not.toHaveBeenCalled()

    // After clicking the chevron, the row should now show "Replier" — and
    // a second click closes it again. (This indirectly verifies the
    // stopPropagation: if the click bubbled, onJumpTo would have fired.)
    expect(screen.getAllByTitle('Replier').length).toBeGreaterThan(0)
  })
})
