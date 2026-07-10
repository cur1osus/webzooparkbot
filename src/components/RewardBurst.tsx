import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { fmt } from '@/utils/format';

export interface Reward {
  /** Emoji or currency glyph to celebrate with. */
  glyph: string;
  amount: number;
  color: string;
  label?: string;
}

const prefersReduced = () =>
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

/**
 * A one-shot "reward" celebration overlaid on the whole screen: the glyph pops,
 * the amount counts in, particles fly out. Peak-End: make the payoff moment feel
 * good. Auto-dismisses, tap to skip, and stays quiet under reduced-motion.
 */
export function RewardBurst({ reward, onDone }: { reward: Reward | null; onDone: () => void }) {
  useEffect(() => {
    if (!reward) return;
    const t = window.setTimeout(onDone, prefersReduced() ? 1100 : 1900);
    return () => window.clearTimeout(t);
  }, [reward, onDone]);

  if (!reward) return null;
  const reduced = prefersReduced();
  const particles = reduced ? [] : Array.from({ length: 12 });

  return createPortal(
    <div
      className="reward-burst-backdrop"
      onClick={onDone}
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 400,
        display: 'grid',
        placeItems: 'center',
        background: 'color-mix(in srgb, #000 52%, transparent)',
        backdropFilter: 'blur(3px)',
        WebkitBackdropFilter: 'blur(3px)',
      }}
    >
      <div style={{ position: 'relative', display: 'grid', placeItems: 'center' }}>
        {particles.map((_, i) => (
          <span
            key={i}
            aria-hidden
            className="reward-particle"
            style={{
              // radial direction + a little stagger
              ['--angle' as string]: `${(i / particles.length) * 360}deg`,
              ['--delay' as string]: `${(i % 4) * 40}ms`,
            }}
          >
            {reward.glyph}
          </span>
        ))}

        <div style={{ textAlign: 'center', position: 'relative' }}>
          <div
            className="reward-pop"
            style={{ fontSize: 68, lineHeight: 1, filter: `drop-shadow(0 0 26px ${reward.color})` }}
          >
            {reward.glyph}
          </div>
          <p className="reward-amount" style={{ margin: '10px 0 0', fontSize: 36, fontWeight: 800, color: reward.color }}>
            +{fmt(reward.amount)}
          </p>
          {reward.label && (
            <p style={{ margin: '2px 0 0', fontSize: 14, color: 'var(--tg-theme-hint-color)' }}>{reward.label}</p>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
