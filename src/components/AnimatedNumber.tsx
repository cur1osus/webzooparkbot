import { useEffect, useRef, useState } from 'react';

const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

const NUMBER_ANIMATION_FPS = 20;

/**
 * Count-up display: whenever `value` changes, the shown number rolls from the
 * current value to the new one. Paired with the per-second income ticker this
 * makes the balance visibly accrue ("juice"); on a discrete gain it rolls up.
 * Honours prefers-reduced-motion by snapping instantly.
 */
export function AnimatedNumber({
  value,
  format,
  className,
  style,
  durationMs = 700,
}: {
  value: number;
  format: (n: number) => string;
  className?: string;
  style?: React.CSSProperties;
  durationMs?: number;
}) {
  const displayRef = useRef(value);
  const [displayValue, setDisplayValue] = useState(value);

  useEffect(() => {
    const from = displayRef.current;
    const to = value;
    if (from === to) return;
    let timer = 0;
    if (prefersReducedMotion()) {
      timer = window.setTimeout(() => {
        displayRef.current = to;
        setDisplayValue(to);
      }, 0);
      return () => window.clearTimeout(timer);
    }
    const start = performance.now();
    const frameMs = 1_000 / NUMBER_ANIMATION_FPS;
    const step = () => {
      const now = performance.now();
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
      displayRef.current = from + (to - from) * eased;
      setDisplayValue(displayRef.current);
      if (t < 1) timer = window.setTimeout(step, frameMs);
      else {
        displayRef.current = to;
        setDisplayValue(to);
      }
    };
    timer = window.setTimeout(step, frameMs);
    return () => window.clearTimeout(timer);
  }, [value, durationMs]);

  return (
    <span className={className} style={style}>
      {format(Math.round(displayValue))}
    </span>
  );
}
