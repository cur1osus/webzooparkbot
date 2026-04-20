import { useState } from 'react';
import { fmt } from '../utils/format';
import { BasketballSoloPanel } from './BasketballSoloPanel';

type BasketballFlowScreen = 'setup' | 'match';

interface BasketballSoloFlowProps {
  bet: number;
  betOptions: readonly number[];
  canStart: boolean;
  onBetChange: (bet: number) => void;
  onBack: () => void;
  onRefresh: () => void;
}

function BasketballFlowHeader({ title, subtitle, onBack }: { title: string; subtitle: string; onBack: () => void }) {
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

export function BasketballSoloFlow({ bet, betOptions, canStart, onBetChange, onBack, onRefresh }: BasketballSoloFlowProps) {
  const [screen, setScreen] = useState<BasketballFlowScreen>('setup');

  if (screen === 'match') {
    return (
      <div className="p-[14px] flex flex-col gap-3">
        <BasketballFlowHeader
          title="Баскетбол"
          subtitle={`Матч со ставкой ₽${fmt(bet)}`}
          onBack={() => setScreen('setup')}
        />
        <BasketballSoloPanel bet={bet} canStart={canStart} onRefresh={onRefresh} />
      </div>
    );
  }

  return (
    <div className="p-[14px] flex flex-col gap-3">
      <BasketballFlowHeader
        title="Баскетбол"
        subtitle="Настрой матч перед началом игры"
        onBack={onBack}
      />

      <div
        className="rounded-2xl p-5 text-center relative overflow-hidden"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid rgba(var(--c-orange-rgb),0.25)' }}
      >
        <div
          className="absolute inset-0 opacity-20"
          style={{ background: 'radial-gradient(ellipse at 50% 0%, rgba(var(--c-orange-rgb),0.5) 0%, transparent 70%)' }}
        />
        <div className="relative">
          <div className="text-[52px] mb-2">🏀</div>
          <p className="m-0 mb-1 text-[18px] font-extrabold">Броски против ИИ</p>
          <p className="m-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Сначала выбираешь ставку, потом запускаешь матч, и только после этого открывается экран с бросками.
          </p>
        </div>
      </div>

      <div className="card flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <p className="m-0 font-bold text-[15px]">Ставка матча</p>
          <span className="text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>Выбрано: ₽{fmt(bet)}</span>
        </div>

        <div className="flex gap-2">
          {betOptions.map((amount) => {
            const active = amount === bet;
            return (
              <button
                key={amount}
                type="button"
                onClick={() => onBetChange(amount)}
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
              ? 'linear-gradient(135deg, var(--c-orange), var(--c-red))'
              : 'color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)',
            color: canStart ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)',
            boxShadow: canStart ? '0 6px 20px rgba(var(--c-orange-rgb),0.35)' : 'none',
          }}
        >
          Начать игру
        </button>
      </div>
    </div>
  );
}
