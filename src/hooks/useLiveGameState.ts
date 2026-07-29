import { useEffect, useMemo, useState } from 'react';
import type { GameState } from '@/types';

/** Net of upkeep, which is the number the player actually accrues. */
export function netRubPerMin(gs: GameState): number {
  return gs.income_rub_per_min - gs.upkeep_rub_per_min;
}

export function calculateLiveRubBalance(gs: GameState, elapsedMs: number): number {
  const accrued = Math.trunc((netRubPerMin(gs) * elapsedMs) / 60_000);
  return Math.max(0, gs.rub + accrued);
}

export function calculateLiveRubBalanceAt(gs: GameState, nowMs: number): number {
  const syncedAtMs = Date.parse(gs.income_synced_at);
  if (!Number.isFinite(syncedAtMs)) return gs.rub;
  return calculateLiveRubBalance(gs, Math.max(0, nowMs - syncedAtMs));
}

/**
 * Subscribe only the tiny balance readout that needs a live tick. Keeping this hook out of
 * App prevents a one-second currency update from re-rendering every active page and list.
 */
export function useLiveRubBalance(gs: GameState | null): number | null {
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    const update = () => {
      if (!document.hidden) setNowMs(Date.now());
    };
    const id = setInterval(() => {
      update();
    }, 1_000);
    document.addEventListener('visibilitychange', update);
    return () => {
      clearInterval(id);
      document.removeEventListener('visibilitychange', update);
    };
  }, []);

  return useMemo(() => {
    if (!gs) return null;
    return calculateLiveRubBalanceAt(gs, nowMs);
  }, [gs, nowMs]);
}
