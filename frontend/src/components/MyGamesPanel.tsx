/**
 * "Analyser mes parties" view (moved out of the profile screen).
 *
 * Hosts everything that's about working *on* the user's games:
 *   - Bulk Lidraughts import + analyses reset (LidraughtsImporter)
 *   - The game list itself (GameHistory)
 *   - Cross-game weakness aggregation (WeaknessPanel)
 *   - The motifs catalog (MotifsCatalogPanel)
 *
 * Profile screen is now strictly identity (pseudo + delete) + raw
 * stat numbers; this panel takes the rest so the analyse-menu
 * funnel ("Analyser") is a single discoverable entry point for
 * post-game work.
 */

import LidraughtsImporter from './LidraughtsImporter'
import GameHistory from './GameHistory'
import WeaknessPanel from './WeaknessPanel'
import MotifsCatalogPanel from './MotifsCatalogPanel'

interface Props {
  /** Bumped externally to force GameHistory + WeaknessPanel +
   *  MotifsCatalogPanel to drop cached data and refetch. Same signal
   *  the profile card used to consume. */
  refreshKey: number
  /** Called when any sub-panel mutates the user's analyses (import,
   *  reset, post-replay analyse). Caller bumps refreshKey in
   *  response. */
  onChanged: () => void
  /** Hand-off to App.tsx's motif drill page. */
  onMotifClick: (slug: string) => void
  /** Hand-off to App.tsx's import-game flow (used by GameHistory
   *  rows on click). */
  onReplay: (detail: { id: string; pdn?: string | null; user_side?: string }) => void
}

export default function MyGamesPanel({
  refreshKey, onChanged, onMotifClick, onReplay,
}: Props) {
  return (
    <div className="h-full overflow-y-auto px-4 py-4 max-w-3xl mx-auto flex flex-col gap-3">
      <h2 className="text-xl font-bold text-amber-500">Analyser mes parties</h2>
      {/* Insight panels first — both default-collapsed drop-downs, so
          the user sees their weakness/motif headlines BEFORE the
          list of games they need to dig into. */}
      <WeaknessPanel onMotifClick={onMotifClick} refreshKey={refreshKey} />
      <MotifsCatalogPanel onMotifClick={onMotifClick} refreshKey={refreshKey} />
      {/* Lidraughts import is also a drop-down — most of the time
          the user just wants to see the list, not import. */}
      <LidraughtsImporter onChanged={onChanged} />
      {/* The game list (with its own internal "Analyser mes parties"
          drop-down for the bulk-analyse action). */}
      <GameHistory
        refreshKey={refreshKey}
        onBatchAnalyzed={onChanged}
        onReplay={onReplay}
      />
    </div>
  )
}
