import { useMemo, useRef, useState } from 'react';
import { apiStartSoloGame } from '../api';
import type { SoloBasketballThrow, SoloGameResult } from '../types';
import { fmt } from '../utils/format';
import { TgsPlayer, type TgsHandle } from './TgsPlayer';

type BasketballPhase = 'idle' | 'loading' | 'player-anim' | 'ai-anim' | 'result';

const rollScore = (roll: number) => (roll >= 3 ? 2 : 0);
const rollResult = (roll: number) => roll >= 3
  ? { icon: '🏀', color: 'var(--c-green)' }
  : { icon: '❌', color: 'var(--tg-theme-hint-color)' };

interface BasketballSoloPanelProps {
  bet: number;
  canStart: boolean;
  onRefresh: () => void;
}

function getVisibleScore(history: SoloBasketballThrow[]) {
  return history.reduce(
    (acc, item) => ({
      player: acc.player + rollScore(item.player_roll),
      ai: acc.ai + rollScore(item.ai_roll),
    }),
    { player: 0, ai: 0 },
  );
}

export function BasketballSoloPanel({ bet, canStart, onRefresh }: BasketballSoloPanelProps) {
  const [phase, setPhase] = useState<BasketballPhase>('idle');
  const [animLabel, setAnimLabel] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<SoloGameResult | null>(null);
  const [sessionBet, setSessionBet] = useState<number | null>(null);
  const [visibleHistory, setVisibleHistory] = useState<SoloBasketballThrow[]>([]);
  const tgsRef = useRef<TgsHandle>(null);

  const sessionHistory = session?.history ?? [];
  const hasPendingRounds = visibleHistory.length < sessionHistory.length;
  const isAnimating = phase === 'player-anim' || phase === 'ai-anim';
  const finished = Boolean(session && !hasPendingRounds && phase === 'result');

  const visibleScore = useMemo(() => getVisibleScore(visibleHistory), [visibleHistory]);
  const lastRound = visibleHistory[visibleHistory.length - 1];

  const resetSession = () => {
    setPhase('idle');
    setAnimLabel('');
    setError(null);
    setSession(null);
    setSessionBet(null);
    setVisibleHistory([]);
  };

  const playRound = async (round: SoloBasketballThrow, isLastRound: boolean) => {
    setAnimLabel('Ваш бросок');
    setPhase('player-anim');
    await tgsRef.current?.playAnimation(`/telegram-dice/basketball/${round.player_roll}.tgs`);

    setAnimLabel('Бросок ИИ');
    setPhase('ai-anim');
    await tgsRef.current?.playAnimation(`/telegram-dice/basketball/${round.ai_roll}.tgs`);

    setVisibleHistory((current) => [...current, round]);
    setAnimLabel('');
    setPhase(isLastRound ? 'result' : 'idle');
  };

  const startMatch = async () => {
    if (!canStart) return;
    setError(null);
    setPhase('loading');

    try {
      const result = await apiStartSoloGame('basketball', bet);
      if (!result.history?.length) {
        throw new Error('Сервер не вернул историю баскетбольного матча');
      }

      setSession(result);
      setSessionBet(bet);
      setVisibleHistory([]);
      onRefresh();

      await playRound(result.history[0], result.history.length === 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка запуска игры');
      setPhase('idle');
    }
  };

  const continueMatch = async () => {
    if (!session || !hasPendingRounds) return;
    const nextRound = sessionHistory[visibleHistory.length];
    if (!nextRound) return;
    await playRound(nextRound, visibleHistory.length + 1 === sessionHistory.length);
  };

  const handleThrow = async () => {
    if (phase === 'loading' || isAnimating) return;

    if (!session) {
      await startMatch();
      return;
    }

    if (finished) {
      resetSession();
      await startMatch();
      return;
    }

    await continueMatch();
  };

  const actionDisabled = phase === 'loading' || isAnimating || (!session && !canStart);
  const actionLabel = finished
    ? 'Играть снова 🔄'
    : phase === 'loading'
      ? 'Готовим матч...'
      : isAnimating
        ? `${animLabel}...`
        : '🏀 Бросок';

  const resultTitle = session?.is_draw ? 'Ничья' : session?.won ? 'Победа' : 'Поражение';
  const resultColor = session?.is_draw
    ? 'var(--c-blue)'
    : session?.won
      ? 'var(--c-green)'
      : 'var(--c-orange)';
  const displayBet = sessionBet ?? bet;

  return (
    <div className="flex flex-col gap-[14px] mt-2">
      <div
        className="rounded-2xl overflow-hidden relative"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid rgba(var(--c-orange-rgb),0.22)' }}
      >
        <div className="absolute inset-0 pointer-events-none" style={{ background: 'radial-gradient(ellipse at 50% -10%, rgba(var(--c-orange-rgb),0.15) 0%, transparent 65%)' }} />
        <div className="relative flex items-center justify-between px-5 py-4">
          <div className="text-center flex-1">
            <p className="m-0 text-[11px] font-semibold uppercase tracking-wide" style={{ color: 'var(--tg-theme-hint-color)' }}>Вы</p>
            <p className="m-0 text-[36px] font-extrabold leading-none mt-1" style={{ color: 'var(--c-orange)' }}>{visibleScore.player}</p>
          </div>
          <div className="text-center px-4">
            <p className="m-0 text-[13px] font-bold" style={{ color: 'var(--tg-theme-hint-color)' }}>
              Ставка ₽{fmt(displayBet)}
            </p>
            <p className="m-0 text-[22px]">🏀</p>
          </div>
          <div className="text-center flex-1">
            <p className="m-0 text-[11px] font-semibold uppercase tracking-wide" style={{ color: 'var(--tg-theme-hint-color)' }}>ИИ</p>
            <p className="m-0 text-[36px] font-extrabold leading-none mt-1" style={{ color: 'var(--c-blue)' }}>{visibleScore.ai}</p>
          </div>
        </div>
      </div>

      <div
        className="rounded-2xl flex flex-col items-center justify-center gap-2 py-4"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)', minHeight: 220 }}
      >
        <p
          className="m-0 text-[13px] font-semibold"
          style={{ color: 'var(--tg-theme-hint-color)', visibility: isAnimating ? 'visible' : 'hidden', minHeight: 20 }}
        >
          {animLabel}
        </p>

        <div style={{ position: 'relative', width: 180, height: 180, flexShrink: 0 }}>
          <TgsPlayer ref={tgsRef} size={180} />
          {!isAnimating && (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              {finished ? (
                <span style={{ fontSize: 64 }}>
                  {session?.is_draw ? '🤝' : session?.won ? '🎉' : '😢'}
                </span>
              ) : (
                <span style={{ fontSize: 72 }}>🏀</span>
              )}
            </div>
          )}
        </div>

        {!isAnimating && !finished && (
          <div className="text-center mt-1">
            {lastRound ? (
              <div className="flex gap-6">
                <span className="text-[13px]" style={{ color: rollResult(lastRound.player_roll).color }}>
                  Вы {rollResult(lastRound.player_roll).icon} +{rollScore(lastRound.player_roll)}
                </span>
                <span className="text-[13px]" style={{ color: rollResult(lastRound.ai_roll).color }}>
                  ИИ {rollResult(lastRound.ai_roll).icon} +{rollScore(lastRound.ai_roll)}
                </span>
              </div>
            ) : (
              <p className="m-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>Нажми «Бросок», чтобы начать матч</p>
            )}
          </div>
        )}

        {finished && session && (
          <div className="text-center mt-1 px-4">
            <p className="m-0 font-extrabold text-[18px]">{resultTitle}</p>
            <p className="m-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>{session.result}</p>
            <p className="mt-2 mb-0 text-[14px] font-semibold" style={{ color: resultColor }}>
              {session.rub_delta > 0 ? '+' : ''}{fmt(session.rub_delta)} ₽
            </p>
          </div>
        )}
      </div>

      <button
        onClick={() => void handleThrow()}
        disabled={actionDisabled}
        className="py-[15px] rounded-2xl border-none font-extrabold text-[16px] transition-opacity"
        style={{
          background: actionDisabled
            ? 'color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)'
            : 'linear-gradient(135deg, var(--c-orange), var(--c-red))',
          color: actionDisabled ? 'var(--tg-theme-hint-color)' : 'var(--tg-theme-button-text-color)',
          boxShadow: actionDisabled ? 'none' : '0 6px 20px rgba(var(--c-orange-rgb),0.35)',
        }}
      >
        {actionLabel}
      </button>

      {!session && !canStart && (
        <p className="m-0 text-[13px] text-center" style={{ color: 'var(--c-red-soft)' }}>
          Недостаточно рублей для ставки ₽{fmt(displayBet)}
        </p>
      )}

      {error && (
        <div className="rounded-2xl p-4" style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.25)' }}>
          <p className="m-0 text-[13px] font-semibold" style={{ color: 'var(--c-red-soft)' }}>{error}</p>
        </div>
      )}

      {visibleHistory.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="m-0 text-[12px] font-bold uppercase tracking-wide" style={{ color: 'var(--tg-theme-hint-color)' }}>История бросков</p>
          {visibleHistory.slice().reverse().map((item) => {
            const player = rollResult(item.player_roll);
            const ai = rollResult(item.ai_roll);

            return (
              <div
                key={item.round}
                className="flex items-center gap-2 rounded-xl px-3 py-2"
                style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 10%, transparent)' }}
              >
                <span className="text-[11px] font-bold w-[44px] shrink-0" style={{ color: 'var(--tg-theme-hint-color)' }}>
                  Р{item.round}
                </span>
                <div className="flex-1 flex items-center gap-1">
                  <span className="text-[11px]" style={{ color: player.color }}>{player.icon} Вы +{rollScore(item.player_roll)}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-[11px]" style={{ color: ai.color }}>{ai.icon} ИИ +{rollScore(item.ai_roll)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
