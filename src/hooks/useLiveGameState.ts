import { useEffect, useMemo, useRef, useState } from 'react';
import type { GameState } from '@/types';

/** Net of upkeep, which is the number the player actually accrues. */
export function netRubPerMin(gs: GameState): number {
  return gs.income_rub_per_min - gs.upkeep_rub_per_min;
}

export function calculateLiveRubBalance(gs: GameState, elapsedMs: number): number {
  const accrued = Math.trunc((netRubPerMin(gs) * elapsedMs) / 60_000);
  return Math.max(0, gs.rub + accrued);
}

function useLiveRubBalance(gs: GameState | null): number | null {
  const stateRef = useRef(gs);
  const [timer, setTimer] = useState({ key: '', visibleElapsedMs: 0 });

  useEffect(() => {
    stateRef.current = gs;
  }, [gs]);

  useEffect(() => {
    const id = setInterval(() => {
      if (!document.hidden) {
        setTimer(prev => {
          const current = stateRef.current;
          if (!current) return prev;
          const key = liveKey(current);
          if (prev.key !== key) return { key, visibleElapsedMs: 1_000 };
          return { key, visibleElapsedMs: prev.visibleElapsedMs + 1_000 };
        });
      }
    }, 1_000);
    return () => clearInterval(id);
  }, []);

  return useMemo(() => {
    if (!gs) return null;
    const key = liveKey(gs);
    const visibleElapsedMs = timer.key === key ? timer.visibleElapsedMs : 0;
    return calculateLiveRubBalance(gs, visibleElapsedMs);
  }, [gs, timer]);
}

/** Restart the ticker whenever the server hands us a new balance or a new rate. */
function liveKey(gs: GameState): string {
  return `${gs.rub}:${gs.income_synced_at}:${gs.income_rub_per_min}:${gs.upkeep_rub_per_min}`;
}

export function useLiveGameState(gs: GameState | null): GameState | null {
  const liveRub = useLiveRubBalance(gs);

  return useMemo(() => {
    if (!gs || liveRub == null) return gs;
    return { ...gs, rub: liveRub };
  }, [gs, liveRub]);
}
