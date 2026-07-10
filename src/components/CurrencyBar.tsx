import { fmtRub, fmtUsd } from '@/utils/format';
import type { GameState } from '@/types';

export function CurrencyBar({ gs, showSeats = false }: { gs: GameState; showSeats?: boolean }) {
  return (
    <div className="flex items-center gap-[6px] px-3 py-[6px] bg-tg-bg border-b border-white/[0.06] overflow-x-auto shrink-0">
      <Chip color="var(--c-green)">{fmtRub(gs.rub)}</Chip>
      <Chip color="var(--c-gold)">{fmtUsd(gs.usd)}</Chip>
      <Chip color="var(--c-purple)">🐾 {gs.paw_coins}</Chip>
      {showSeats && (
        <Chip color="var(--tg-theme-hint-color)">🌍 {gs.localities_count} местн.</Chip>
      )}
    </div>
  );
}

function Chip({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span
      className="px-[11px] py-[5px] rounded-full text-[13px] font-extrabold tabular-nums whitespace-nowrap shrink-0"
      style={{
        background: `color-mix(in srgb, ${color} 13%, var(--tg-theme-secondary-bg-color))`,
        color,
        border: `1px solid color-mix(in srgb, ${color} 26%, transparent)`,
        boxShadow: `inset 0 1px 0 color-mix(in srgb, ${color} 20%, transparent)`,
      }}
    >
      {children}
    </span>
  );
}
