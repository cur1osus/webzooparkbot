import type { CSSProperties, ElementType } from 'react';
import type { NicknameColor } from '@/types';
import { nicknameColorClass, nicknameColorValue } from '@/data/nicknameColors';

export function TextWave({ text }: { text: string }) {
  return (
    <span className="wave">
      {[...text].map((ch, i) => (
        <span key={`${i}-${ch}`} style={{ animationDelay: `${-i * 0.09}s` }}>
          {ch}
        </span>
      ))}
    </span>
  );
}

function ShimmerText({ children }: { children: string }) {
  return <span className="shimmer-text">{children}</span>;
}

export function GlitchText({ children }: { children: string }) {
  return (
    <span className="glitch" data-text={children}>
      <ShimmerText>{children}</ShimmerText>
    </span>
  );
}

// The Google logo isn't a gradient — it's per-letter brand colours (blue, red, yellow,
// blue, green, red, repeating). Colouring each glyph that way is what makes the name
// read as "Google" rather than a random rainbow sweep.
const GOOGLE_COLORS = ['#4285f4', '#ea4335', '#fbbc05', '#4285f4', '#34a853', '#ea4335'];

export function GoogleText({ text }: { text: string }) {
  return (
    <span className="google-name">
      {[...text].map((ch, i) => {
        const color = GOOGLE_COLORS[i % GOOGLE_COLORS.length];
        return (
          <span key={`${i}-${ch}`} style={{ color, WebkitTextFillColor: color }}>
            {ch === ' ' ? ' ' : ch}
          </span>
        );
      })}
    </span>
  );
}

// Single source of truth for rendering a styled nickname. Every place that shows a
// player's name (home HUD, leaderboard, public profile) routes through this so the
// colour, glow and per-effect quirks (the "wave" bob) stay identical everywhere —
// previously each call site re-implemented this and drifted out of sync.
export function Nickname({
  name,
  color,
  as: Tag = 'span',
  className = '',
  style,
}: {
  name: string;
  color: NicknameColor | string | null | undefined;
  as?: ElementType;
  className?: string;
  style?: CSSProperties;
}) {
  const colorClass = nicknameColorClass(color);
  return (
    <Tag
      className={`nickname ${colorClass} ${className}`.replace(/\s+/g, ' ').trim()}
      style={{ color: nicknameColorValue(color), ...style }}
    >
      {color === 'wave'
        ? <TextWave text={name} />
        : color === 'glitch'
          ? <GlitchText>{name}</GlitchText>
          : color === 'google'
            ? <GoogleText text={name} />
            : name}
    </Tag>
  );
}
