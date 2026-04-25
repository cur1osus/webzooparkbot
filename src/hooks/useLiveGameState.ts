import { useEffect, useMemo, useRef, useState } from 'react';
import type { GameState } from '@/types';

export function calculateLiveRubBalance(gs: GameState, elapsedMs: number): number {
  const netPerMin = gs.income_rub_per_min - gs.expenses_rub_per_min;
  const accrued = Math.trunc((netPerMin * elapsedMs) / 60_000);
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
          const key = `${current.rub}:${current.balance_seq}:${current.income_rub_per_min}:${current.expenses_rub_per_min}`;
          if (prev.key !== key) return { key, visibleElapsedMs: 1_000 };
          return { key, visibleElapsedMs: prev.visibleElapsedMs + 1_000 };
        });
      }
    }, 1_000);
    return () => clearInterval(id);
  }, []);

  return useMemo(() => {
    if (!gs) return null;
    const key = `${gs.rub}:${gs.balance_seq}:${gs.income_rub_per_min}:${gs.expenses_rub_per_min}`;
    const visibleElapsedMs = timer.key === key ? timer.visibleElapsedMs : 0;
    return calculateLiveRubBalance(gs, visibleElapsedMs);
  }, [gs, timer]);
}

export function useLiveGameState(gs: GameState | null): GameState | null {
  const liveRub = useLiveRubBalance(gs);

  return useMemo(() => {
    if (!gs || liveRub == null) return gs;
    return { ...gs, rub: liveRub };
  }, [gs, liveRub]);
}
