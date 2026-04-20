import { useState } from 'react';
import type { GameDef } from '../data/games';
import { fmt } from '../utils/format';
import { BasketballSoloPanel } from './BasketballSoloPanel';

type BetAmount = 100 | 1_000 | 10_000;
type SoloFlowScreen = 'setup' | 'match';

const BET_OPTIONS: readonly BetAmount[] = [100, 1_000, 10_000];

const GAME_POSTERS: Record<string, string> = {
  basketball: '/telegram-dice/stills/basketball.png',
  bowling: '/telegram-dice/stills/bowling.png',
  darts: '/telegram-dice/stills/darts.png',
  dice: '/telegram-dice/stills/dice.png',
  football: '/telegram-dice/stills/football.png',
};

const GAME_ACCENTS: Record<string, { border: string; from: string; to: string; glow: string }> = {
  basketball: { border: 'rgba(var(--c-orange-rgb),0.25)', from: 'var(--c-orange)', to: 'var(--c-red)', glow: 'rgba(var(--c-orange-rgb),0.35)' },
  darts: { border: 'rgba(var(--c-orange-rgb),0.25)', from: 'var(--c-orange)', to: 'var(--c-red)', glow: 'rgba(var(--c-orange-rgb),0.35)' },
  bowling: { border: 'rgba(var(--c-green-rgb),0.25)', from: 'var(--c-green)', to: 'var(--c-teal)', glow: 'rgba(var(--c-green-rgb),0.35)' },
  dice: { border: 'rgba(var(--c-blue-rgb),0.25)', from: 'var(--c-blue)', to: 'var(--c-cyan)', glow: 'rgba(var(--c-blue-rgb),0.35)' },
  football: { border: 'rgba(var(--c-gold-rgb),0.25)', from: 'var(--c-gold)', to: 'var(--c-amber)', glow: 'rgba(var(--c-gold-rgb),0.35)' },
};

interface SoloGameFlowProps {
  game: GameDef;
  availableRub: number;
  onBack: () => void;
  onRefresh: () => void;
}

function FlowHeader({ title, subtitle, onBack }: { title: string; subtitle: string; onBack: () => void }) {
  return (
    <div className="flex items-center gap-3 mb-1">
      <button
        type="button"
        onClick={onBack}
        className="w-10 h-10 rounded-xl border-none text-[18px] shrink-0"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', color: 'var(--tg-theme-text-color)' }}
      >
        ←
      </button>
      <div className="min-w-0">
        <p className="m-0 text-[18px] font-extrabold">{title}</p>
        <p className="m-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>{subtitle}</p>
      </div>
    </div>
  );
}

export function SoloGameFlow({ game, availableRub, onBack, onRefresh }: SoloGameFlowProps) {
  const [bet, setBet] = useState<BetAmount>(100);
  const [screen, setScreen] = useState<SoloFlowScreen>('setup');

  const accents = GAME_ACCENTS[game.id] ?? GAME_ACCENTS.dice;
  const canStart = availableRub >= bet;

  if (screen === 'match') {
    return (
      <div className="p-[14px] flex flex-col gap-3">
        <FlowHeader
          title={game.name}
          subtitle={`Матч со ставкой ₽${fmt(bet)}`}
          onBack={() => setScreen('setup')}
        />
        <BasketballSoloPanel gameId={game.id} gameEmoji={game.emoji} bet={bet} canStart={canStart} onRefresh={onRefresh} />
      </div>
    );
  }

  return (
    <div className="p-[14px] flex flex-col gap-3">
      <FlowHeader
        title={game.name}
        subtitle="Сначала выбери ставку, затем начни матч"
        onBack={onBack}
      />

      <div
        className="rounded-2xl p-5 text-center relative overflow-hidden"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: `1px solid ${accents.border}` }}
      >
        <div
          className="absolute inset-0 opacity-20"
          style={{ background: `radial-gradient(ellipse at 50% 0%, ${accents.glow} 0%, transparent 70%)` }}
        />
        <div className="relative">
          <div className="mb-3 flex justify-center">
            <div
              className="w-[132px] h-[132px] rounded-2xl overflow-hidden"
              style={{
                background: 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)',
                border: `1px solid ${accents.border}`,
                boxShadow: `0 10px 30px ${accents.glow}`,
              }}
            >
              <img
                src={GAME_POSTERS[game.id]}
                alt={game.name}
                className="w-full h-full block"
                style={{ objectFit: 'contain' }}
              />
            </div>
          </div>
          <p className="m-0 mb-1 text-[18px] font-extrabold">{game.name}</p>
          <p className="m-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            {game.description}
          </p>
          <p className="m-0 mt-2 text-[12px] font-semibold" style={{ color: accents.from }}>
            {game.detail}
          </p>
        </div>
      </div>

      <div className="card flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <p className="m-0 font-bold text-[15px]">Ставка игры</p>
          <span className="text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>Выбрано: ₽{fmt(bet)}</span>
        </div>

        <div className="flex gap-2">
          {BET_OPTIONS.map((amount) => {
            const active = amount === bet;
            return (
              <button
                key={amount}
                type="button"
                onClick={() => setBet(amount)}
                className="flex-1 py-2 rounded-xl border-none font-bold text-[13px]"
                style={{
                  background: active ? 'rgba(var(--c-gold-rgb),0.18)' : 'var(--surface-subtle)',
                  color: active ? 'var(--c-gold)' : 'var(--tg-theme-hint-color)',
                  border: `1px solid ${active ? 'rgba(var(--c-gold-rgb),0.3)' : 'var(--surface-overlay-border)'}`,
                }}
              >
                ₽{fmt(amount)}
              </button>
            );
          })}
        </div>

        {!canStart && (
          <p className="m-0 text-[13px]" style={{ color: 'var(--c-red-soft)' }}>
            Недостаточно рублей для ставки ₽{fmt(bet)}
          </p>
        )}

        <button
          type="button"
          onClick={() => setScreen('match')}
          disabled={!canStart}
          className="py-[15px] rounded-2xl border-none font-extrabold text-[16px]"
          style={{
            background: canStart
              ? `linear-gradient(135deg, ${accents.from}, ${accents.to})`
              : 'color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)',
            color: canStart ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)',
            boxShadow: canStart ? `0 6px 20px ${accents.glow}` : 'none',
          }}
        >
          Начать игру
        </button>
      </div>
    </div>
  );
}
