import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiFinishSoloGame, apiStartSoloGame } from '@/api';
import type { SoloBetPercent, SoloGameResult, SoloThrowRound } from '@/types';
import { fmt } from '@/utils/format';
import { TgsPlayer, type TgsHandle } from '@/components/TgsPlayer';

type BasketballPhase = 'idle' | 'loading' | 'player-anim' | 'ai-anim' | 'result';

const GAME_RULES: Record<string, {
  assetDir: string;
  accent: string;
  playerIcon: string;
  successIcon: string;
  failIcon: string;
  scoreRoll: (roll: number) => number;
}> = {
  basketball: {
    assetDir: 'basketball',
    accent: 'var(--c-orange)',
    playerIcon: '🏀',
    successIcon: '🏀',
    failIcon: '❌',
    scoreRoll: (roll) => (roll >= 3 ? 2 : 0),
  },
  football: {
    assetDir: 'football',
    accent: 'var(--c-gold)',
    playerIcon: '⚽',
    successIcon: '⚽',
    failIcon: '❌',
    scoreRoll: (roll) => (roll >= 3 ? 1 : 0),
  },
  dice: {
    assetDir: 'dice',
    accent: 'var(--c-blue)',
    playerIcon: '🎲',
    successIcon: '🎲',
    failIcon: '🎲',
    scoreRoll: (roll) => roll,
  },
  darts: {
    assetDir: 'dart',
    accent: 'var(--c-purple)',
    playerIcon: '🎯',
    successIcon: '🎯',
    failIcon: '🎯',
    scoreRoll: (roll) => roll,
  },
  bowling: {
    assetDir: 'bowling',
    accent: 'var(--c-green)',
    playerIcon: '🎳',
    successIcon: '🎳',
    failIcon: '🎳',
    scoreRoll: (roll) => roll,
  },
};

function getGameRule(gameId: string) {
  return GAME_RULES[gameId] ?? GAME_RULES.dice;
}

function getRollScore(gameId: string, roll: number) {
  return getGameRule(gameId).scoreRoll(roll);
}

function getRollResult(gameId: string, roll: number) {
  const rule = getGameRule(gameId);
  const delta = getRollScore(gameId, roll);
  const success = delta > 0;

  return {
    icon: success ? rule.successIcon : rule.failIcon,
    color: success ? rule.accent : 'var(--tg-theme-hint-color)',
    delta,
  };
}

interface BasketballSoloPanelProps {
  gameId: string;
  gameEmoji: string;
  bet: number;
  betPercent: SoloBetPercent;
  canStart: boolean;
  autoStart?: boolean;
  initialSession?: SoloGameResult | null;
  onMatchStarted?: (match: SoloGameResult) => void;
  onMatchFinished?: () => void;
  onRefresh: () => void;
}

function getVisibleScore(gameId: string, history: SoloThrowRound[]) {
  return history.reduce(
    (acc, item) => ({
      player: acc.player + getRollScore(gameId, item.player_roll),
      ai: acc.ai + getRollScore(gameId, item.ai_roll),
    }),
    { player: 0, ai: 0 },
  );
}

export function BasketballSoloPanel({ gameId, gameEmoji, bet, betPercent, canStart, autoStart = false, initialSession = null, onMatchStarted, onMatchFinished, onRefresh }: BasketballSoloPanelProps) {
  const [phase, setPhase] = useState<BasketballPhase>('idle');
  const [animLabel, setAnimLabel] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<SoloGameResult | null>(null);
  const [sessionBet, setSessionBet] = useState<number | null>(null);
  const [visibleHistory, setVisibleHistory] = useState<SoloThrowRound[]>([]);
  const tgsRef = useRef<TgsHandle>(null);
  const finishSentRef = useRef(false);
  const autoStartRequestedRef = useRef(false);

  const sessionHistory = session?.history ?? [];
  const hasPendingRounds = visibleHistory.length < sessionHistory.length;
  const isAnimating = phase === 'player-anim' || phase === 'ai-anim';
  const finished = Boolean(session && !hasPendingRounds && phase === 'result');
  const gameRule = getGameRule(gameId);

  useEffect(() => {
    if (!initialSession) return;
    setSession(initialSession);
    setSessionBet(initialSession.stake_rub);
    setVisibleHistory([]);
    setPhase('idle');
    setAnimLabel('');
    setError(null);
    finishSentRef.current = false;
  }, [initialSession]);

  useEffect(() => {
    if (!finished || finishSentRef.current) return;
    finishSentRef.current = true;
    void apiFinishSoloGame().then(() => {
      onMatchFinished?.();
    }).catch(() => {
      // Keep the match active on the server if the acknowledgement was lost. A
      // refresh will restore it and allow the acknowledgement to be retried.
      finishSentRef.current = false;
    });
  }, [finished, onMatchFinished]);

  const visibleScore = useMemo(() => getVisibleScore(gameId, visibleHistory), [gameId, visibleHistory]);
  const lastRound = visibleHistory[visibleHistory.length - 1];

  const resetSession = () => {
    setPhase('idle');
    setAnimLabel('');
    setError(null);
    setSession(null);
    setSessionBet(null);
    setVisibleHistory([]);
    finishSentRef.current = false;
  };

  const playRound = useCallback(async (round: SoloThrowRound, isLastRound: boolean) => {
    setAnimLabel('Ваш бросок');
    setPhase('player-anim');
    await tgsRef.current?.playAnimation(`/telegram-dice/${gameRule.assetDir}/${round.player_roll}.tgs`);

    setAnimLabel('Бросок ИИ');
    setPhase('ai-anim');
    await tgsRef.current?.playAnimation(`/telegram-dice/${gameRule.assetDir}/${round.ai_roll}.tgs`);

    setVisibleHistory((current) => [...current, round]);
    if (isLastRound) {
      tgsRef.current?.clearAnimation();
    }
    setAnimLabel('');
    setPhase(isLastRound ? 'result' : 'idle');
  }, [gameRule.assetDir]);

  const startMatch = useCallback(async () => {
    if (!canStart) return;
    setError(null);
    setPhase('loading');

    try {
      const result = await apiStartSoloGame(gameId, betPercent);
      if (!result.history?.length) {
        throw new Error('Сервер не вернул историю матча');
      }

      setSession(result);
      setSessionBet(result.stake_rub);
      setVisibleHistory([]);
      onMatchStarted?.(result);
      onRefresh();

      await playRound(result.history[0], result.history.length === 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка запуска игры');
      setPhase('idle');
    }
  }, [betPercent, canStart, gameId, onMatchStarted, onRefresh, playRound]);

  useEffect(() => {
    if (!autoStart || initialSession || autoStartRequestedRef.current || !canStart) return;
    autoStartRequestedRef.current = true;
    void startMatch();
  }, [autoStart, canStart, initialSession, startMatch]);

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
        : 'Бросок';

  const resultTitle = session?.won ? 'Победа' : 'Поражение';
  // The server never returns a draw: it reruns the match until someone wins.
  const resultColor = session?.won ? 'var(--c-green)' : 'var(--c-orange)';
  const displayBet = sessionBet ?? bet;
  const currentRound = session
    ? Math.min(sessionHistory.length, Math.max(visibleHistory.length + (isAnimating ? 1 : 0), 1))
    : null;
  const lastPlayer = lastRound ? getRollResult(gameId, lastRound.player_roll) : null;
  const lastAi = lastRound ? getRollResult(gameId, lastRound.ai_roll) : null;

  return (
    <div className="flex flex-col gap-[14px] mt-2">
      <div
        className="rounded-2xl overflow-hidden relative"
        style={{
          background: 'var(--tg-theme-secondary-bg-color)',
          border: `1px solid color-mix(in srgb, ${gameRule.accent} 24%, transparent)`,
        }}
      >
        <div className="absolute inset-0 pointer-events-none" style={{ background: `radial-gradient(ellipse at 50% -10%, color-mix(in srgb, ${gameRule.accent} 18%, transparent) 0%, transparent 65%)` }} />
        <div className="relative flex items-center justify-between px-5 py-4">
          <div className="text-center flex-1">
            <p className="m-0 text-[11px] font-semibold uppercase tracking-wide" style={{ color: 'var(--tg-theme-hint-color)' }}>Вы</p>
            <p className="m-0 text-[36px] font-extrabold leading-none mt-1" style={{ color: gameRule.accent }}>{visibleScore.player}</p>
          </div>
          <div className="text-center px-4">
            <p className="m-0 text-[13px] font-bold" style={{ color: 'var(--tg-theme-hint-color)' }}>
              Ставка ₽{fmt(displayBet)}
            </p>
            <p className="m-0 mt-1 text-[11px] font-semibold tabular-nums" style={{ color: gameRule.accent }}>
              {currentRound ? `Ход ${currentRound} из ${sessionHistory.length}` : 'Ходов: 2–7'}
            </p>
            <p className="m-0 text-[22px]">{gameEmoji}</p>
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
          {!isAnimating && (!lastRound || finished) && (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              {finished ? (
                <span style={{ fontSize: 64 }}>
                  {session?.won ? '🎉' : '😢'}
                </span>
              ) : (
                <span style={{ fontSize: 72 }}>{gameEmoji}</span>
              )}
            </div>
          )}
        </div>

        {!isAnimating && !finished && (
          <div className="text-center mt-1">
            {lastRound && lastPlayer && lastAi ? (
              <div className="flex gap-6">
                <span className="text-[13px]" style={{ color: lastPlayer.color }}>
                  Вы {lastPlayer.icon} +{lastPlayer.delta}
                </span>
                <span className="text-[13px]" style={{ color: lastAi.color }}>
                  ИИ {lastAi.icon} +{lastAi.delta}
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
            : `linear-gradient(135deg, ${gameRule.accent}, var(--c-red))`,
          color: actionDisabled ? 'var(--tg-theme-hint-color)' : 'var(--tg-theme-button-text-color)',
          boxShadow: actionDisabled ? 'none' : '0 6px 20px rgba(0,0,0,0.18)',
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
            const player = getRollResult(gameId, item.player_roll);
            const ai = getRollResult(gameId, item.ai_roll);

            return (
              <div
                key={item.round}
                className="flex items-center gap-2 rounded-xl px-3 py-2"
                style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 10%, transparent)' }}
              >
                <span className="text-[11px] font-bold w-[44px] shrink-0" style={{ color: 'var(--tg-theme-hint-color)' }}>
                  {item.round}
                </span>
                <div className="flex-1 flex items-center gap-1">
                  <span className="text-[11px]" style={{ color: player.color }}>{player.icon} Вы +{player.delta}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-[11px]" style={{ color: ai.color }}>{ai.icon} ИИ +{ai.delta}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
