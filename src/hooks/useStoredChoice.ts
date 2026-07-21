import { useCallback, useState } from 'react';

const STORAGE_PREFIX = 'zoopark-choice-v1:';

function storageKey(name: string, tgId: number): string {
  return `${STORAGE_PREFIX}${name}:${tgId}`;
}

/**
 * Remember one of a fixed set of choices (a sort/filter tab) per player, so the
 * list opens the way it was left instead of resetting to the default every time.
 */
export function useStoredChoice<T extends string>(
  name: string,
  tgId: number,
  options: readonly T[],
  fallback: T,
): readonly [T, (next: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = window.localStorage.getItem(storageKey(name, tgId));
      return options.includes(stored as T) ? (stored as T) : fallback;
    } catch {
      // Storage can be unavailable in a restricted Telegram/browser context.
      return fallback;
    }
  });

  const select = useCallback((next: T) => {
    setValue(next);
    try {
      window.localStorage.setItem(storageKey(name, tgId), next);
    } catch {
      // Same restricted-storage case: the choice still applies for this session.
    }
  }, [name, tgId]);

  return [value, select] as const;
}
