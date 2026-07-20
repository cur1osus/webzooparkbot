import { useEffect, useState } from 'react';
import { apiGetCurrentSoloGame } from '@/api';
import type { GameDef } from '@/data/games';
import type { SoloBetPercent, SoloGameResult } from '@/types';
import { fmt } from '@/utils/format';
import { BasketballSoloPanel } from './BasketballSoloPanel';

type SoloFlowScreen = 'setup' | 'match';

const BET_OPTIONS: readonly SoloBetPercent[] = [5, 10, 15];

function getBetAmount(balance: number, percent: SoloBetPercent) {
  if (balance <= 0) return 0;
  return Math.max(1, Math.floor(balance * percent / 100));
}

const GAME_ACCENTS: Record<string, { border: string; from: string; to: string; glow: string }> = {
  basketball: { border: 'rgba(var(--c-orange-rgb),0.25)', from: 'var(--c-orange)', to: 'var(--c-red)', glow: 'rgba(var(--c-orange-rgb),0.35)' },
  darts: { border: 'rgba(var(--c-purple-rgb),0.25)', from: 'var(--c-purple)', to: 'var(--c-blue)', glow: 'rgba(var(--c-purple-rgb),0.35)' },
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
  const [betPercent, setBetPercent] = useState<SoloBetPercent>(5);
  const [screen, setScreen] = useState<SoloFlowScreen>('setup');
  const [currentMatch, setCurrentMatch] = useState<SoloGameResult | null>(null);
  const [matchChecked, setMatchChecked] = useState(false);

  useEffect(() => {
    let mounted = true;
    void apiGetCurrentSoloGame()
      .then(({ game: match }) => {
        if (!mounted) return;
        setCurrentMatch(match);
        if (match?.kind === game.id) setScreen('match');
      })
      .catch(() => {
        // A failed check must not prevent starting a regular game; the start endpoint
        // still enforces the active-match lock on the server.
      })
      .finally(() => {
        if (mounted) setMatchChecked(true);
      });
    return () => {
      mounted = false;
    };
  }, [game.id]);

  const accents = GAME_ACCENTS[game.id] ?? GAME_ACCENTS.dice;
  const bet = getBetAmount(availableRub, betPercent);
  const canStart = bet > 0 && availableRub >= bet;

  if (screen === 'match') {
    return (
      <div className="p-[14px] flex flex-col gap-3">
        <FlowHeader
          title={game.name}
          subtitle={`Матч со ставкой ${betPercent}%`}
          onBack={() => setScreen('setup')}
        />
        <BasketballSoloPanel gameId={game.id} gameEmoji={game.emoji} bet={bet} betPercent={betPercent} canStart={canStart} initialSession={currentMatch?.kind === game.id ? currentMatch : null} onMatchFinished={() => setCurrentMatch(null)} onRefresh={onRefresh} />
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

      {matchChecked && currentMatch && currentMatch.kind !== game.id && (
        <div className="card flex flex-col gap-2" style={{ border: '1px solid color-mix(in srgb, var(--c-orange) 35%, transparent)' }}>
          <p className="m-0 font-bold text-[15px]">Есть незавершённый матч</p>
          <p className="m-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Сначала продолжи игру «{currentMatch.kind}». Новую игру открыть нельзя, пока текущая не завершена.
          </p>
        </div>
      )}

      {matchChecked && currentMatch?.kind === game.id && (
        <div className="card flex flex-col gap-2" style={{ border: '1px solid color-mix(in srgb, var(--c-orange) 35%, transparent)' }}>
          <p className="m-0 font-bold text-[15px]">Матч восстановлен</p>
          <p className="m-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Он уже оплачен и продолжится с сохранённым количеством ходов.
          </p>
          <button
            type="button"
            onClick={() => setScreen('match')}
            className="py-3 rounded-xl border-none font-bold"
            style={{ background: 'var(--c-orange)', color: 'var(--tg-theme-button-text-color)' }}
          >
            Продолжить матч
          </button>
        </div>
      )}

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
              <div className="w-full h-full flex items-center justify-center text-[72px] leading-none">
                {game.emoji}
              </div>
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
          <p className="m-0 font-bold text-[15px]">Процент ставки</p>
          <span className="text-[12px] tabular-nums" style={{ color: 'var(--tg-theme-hint-color)' }}>Выбрано: {betPercent}% · ₽{fmt(bet)}</span>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {BET_OPTIONS.map((percent) => {
            const amount = getBetAmount(availableRub, percent);
            const active = percent === betPercent;
            return (
              <button
                key={percent}
                type="button"
                onClick={() => setBetPercent(percent)}
                className="min-h-[64px] rounded-xl border-none font-bold text-[13px] flex flex-col items-center justify-center gap-1"
                style={{
                  background: active ? `color-mix(in srgb, ${accents.from} 16%, transparent)` : 'var(--surface-subtle)',
                  color: active ? accents.from : 'var(--tg-theme-hint-color)',
                  border: `1px solid ${active ? `color-mix(in srgb, ${accents.from} 42%, transparent)` : 'var(--surface-overlay-border)'}`,
                }}
              >
                <span className="text-[16px] leading-none">{percent}%</span>
                <span className="text-[11px] font-semibold tabular-nums">₽{fmt(amount)}</span>
              </button>
            );
          })}
        </div>

        <p className="m-0 text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
          Сумма рассчитывается от текущего баланса. Для маленького баланса действует минимальная ставка ₽1.
        </p>

        {!canStart && (
          <p className="m-0 text-[13px]" style={{ color: 'var(--c-red-soft)' }}>
            Недостаточно рублей для ставки ₽{fmt(bet)}
          </p>
        )}

        <button
          type="button"
          onClick={() => setScreen('match')}
          disabled={!canStart || Boolean(currentMatch)}
          className="py-[15px] rounded-2xl border-none font-extrabold text-[16px]"
          style={{
            background: canStart && !currentMatch
              ? `linear-gradient(135deg, ${accents.from}, ${accents.to})`
              : 'color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)',
            color: canStart && !currentMatch ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)',
            boxShadow: canStart && !currentMatch ? `0 6px 20px ${accents.glow}` : 'none',
          }}
        >
          {currentMatch ? 'Матч уже идёт' : 'Начать игру'}
        </button>
      </div>
    </div>
  );
}
