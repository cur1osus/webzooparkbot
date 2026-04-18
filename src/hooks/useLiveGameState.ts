import { useEffect, useMemo, useState } from 'react';
import type { GameState } from '../types';

function useLiveRubBalance(gs: GameState | null): number | null {
  const [visibleElapsedMs, setVisibleElapsedMs] = useState(0);

  useEffect(() => {
    setVisibleElapsedMs(0);
  }, [gs?.rub, gs?.balance_seq, gs?.income_rub_per_min, gs?.expenses_rub_per_min]);

  useEffect(() => {
    const id = setInterval(() => {
      if (!document.hidden) {
        setVisibleElapsedMs(prev => prev + 1_000);
      }
    }, 1_000);
    return () => clearInterval(id);
  }, []);

  return useMemo(() => {
    if (!gs) return null;
    const netPerMin = gs.income_rub_per_min - gs.expenses_rub_per_min;
    const accrued = Math.trunc((netPerMin * visibleElapsedMs) / 60_000);
    return Math.max(0, gs.rub + accrued);
  }, [gs, visibleElapsedMs]);
}

export function useLiveGameState(gs: GameState | null): GameState | null {
  const liveRub = useLiveRubBalance(gs);

  return useMemo(() => {
    if (!gs || liveRub == null) return gs;
    return { ...gs, rub: liveRub };
  }, [gs, liveRub]);
}
