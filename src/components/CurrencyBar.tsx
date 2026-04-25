import { fmtRub, fmtUsd } from '@/utils/format';
import type { GameState } from '@/types';

export function CurrencyBar({ gs, showSeats = false }: { gs: GameState; showSeats?: boolean }) {
  return (
    <div className="flex items-center gap-[6px] px-3 py-[6px] bg-tg-bg border-b border-white/[0.06] overflow-x-auto shrink-0">
      <Chip color="var(--c-green)">{fmtRub(gs.rub)}</Chip>
      <Chip color="var(--c-gold)">{fmtUsd(gs.usd)}</Chip>
      <Chip color="var(--c-purple)">🐾 {gs.paw_coins}</Chip>
      {showSeats && (
        <Chip color="var(--tg-theme-hint-color)">🏗️ {fmtRub(gs.free_seats).replace('₽ ', '')} мест</Chip>
      )}
    </div>
  );
}

function Chip({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span
      className="px-[10px] py-1 rounded-[20px] text-[13px] font-bold whitespace-nowrap shrink-0"
      style={{
        background: `color-mix(in srgb, ${color} 10%, transparent)`,
        color,
        border: `1px solid color-mix(in srgb, ${color} 19%, transparent)`,
      }}
    >
      {children}
    </span>
  );
}
