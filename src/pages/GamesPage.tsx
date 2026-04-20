import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { fmt } from '../utils/format';
import type { GameState, MpGame, SoloStats } from '../types';
import { GAMES } from '../data/games';
import {
  apiCocktailGuess,
  apiCreateMpGame,
  apiGetOpenGames,
  apiGetSoloStats,
  apiJoinMpGame,
  apiStartSoloGame,
} from '../api';

type GamesTab = 'solo' | 'multi' | 'cocktail' | 'basketball';

/* ─── RLottie bootstrap ────────────────────────────────────────────────── */
declare global {
  interface Window {
    RLottie?: {
      init: (el: HTMLElement, opts?: Record<string, unknown>) => void;
      destroy: (el: HTMLElement) => void;
    };
  }
}

let _rlottiePromise: Promise<void> | null = null;
function loadRLottie(): Promise<void> {
  if (window.RLottie) return Promise.resolve();
  if (!_rlottiePromise) {
    _rlottiePromise = new Promise<void>((resolve, reject) => {
      const s = document.createElement('script');
      s.src = '/tgsticker/tgsticker.js';
      s.onload = () => resolve();
      s.onerror = () => reject(new Error('RLottie load failed'));
      document.head.appendChild(s);
    });
  }
  return _rlottiePromise;
}

/* ─── TGS Player ───────────────────────────────────────────────────────── */
interface TgsHandle {
  playAnimation(src: string): Promise<void>;
}

const TgsPlayer = forwardRef<TgsHandle, { size?: number }>(({ size = 180 }, ref) => {
  const picRef = useRef<HTMLPictureElement>(null);
  const srcRef = useRef<HTMLSourceElement>(null);

  useImperativeHandle(ref, () => ({
    async playAnimation(src: string): Promise<void> {
      await loadRLottie();
      const el = picRef.current;
      const srcEl = srcRef.current;
      if (!el || !srcEl || !window.RLottie) return;

      window.RLottie.destroy(el);
      srcEl.setAttribute('srcset', src);

      await new Promise<void>((resolve) => {
        const onPause = () => { el.removeEventListener('tg:pause', onPause); resolve(); };
        el.addEventListener('tg:pause', onPause);
        window.RLottie!.init(el, { playUntilEnd: true });
      });
    },
  }), []);

  useEffect(() => {
    return () => { if (picRef.current && window.RLottie) window.RLottie.destroy(picRef.current); };
  }, []);

  return (
    <picture ref={picRef} style={{ width: size, height: size, display: 'block' }}>
      <source ref={srcRef} type="application/x-tgsticker" srcSet="" />
      <img alt="" style={{ width: size, height: size }} />
    </picture>
  );
});
TgsPlayer.displayName = 'TgsPlayer';
type BetAmount = 100 | 1_000 | 10_000;
type CocktailClueStatus = 'correct' | 'present' | 'absent';

const BET_AMOUNTS: BetAmount[] = [100, 1_000, 10_000];

const FRUITS = ['🍓', '🫐', '🍏', '🍐', '🍇', '🍒'];

const GAME_COLORS: Record<string, { from: string; to: string; glow: string }> = {
  darts:    { from: 'var(--c-orange)', to: 'var(--c-red)', glow: 'rgba(var(--c-orange-rgb),0.35)' },
  bowling:  { from: 'var(--c-green)', to: 'var(--c-teal)', glow: 'rgba(var(--c-green-rgb),0.35)' },
  dice:     { from: 'var(--c-blue)', to: 'var(--c-cyan)', glow: 'rgba(var(--c-blue-rgb),0.35)' },
  football: { from: 'var(--c-gold)', to: 'var(--c-amber)', glow: 'rgba(var(--c-gold-rgb),0.35)' },
};

function getGameDef(gameType: string) {
  return GAMES.find((game) => game.id === gameType);
}

/* ──────────────────────────── COCKTAIL ──────────────────────────────── */
function CocktailTab({ onRefresh }: { onRefresh: () => void }) {
  const [slots, setSlots] = useState<(string | null)[]>([null, null, null, null]);
  const [attemptsLeft, setAttemptsLeft] = useState(10);
  const [guessing, setGuessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ won: boolean; message: string } | null>(null);
  const [history, setHistory] = useState<Array<{ fruits: string[]; clues: Array<{ pos: number; status: CocktailClueStatus }> }>>([]);

  const gameFinished = attemptsLeft <= 0 || Boolean(result?.won);

  const addFruit = (fruit: string) => {
    if (gameFinished || guessing) return;
    setSlots(s => {
      const idx = s.indexOf(null);
      if (idx === -1) return s;
      const next = [...s];
      next[idx] = fruit;
      return next;
    });
  };
  const removeAtIdx = (i: number) => {
    if (guessing || gameFinished) return;
    setSlots(s => { const next = [...s]; next[i] = null; return next; });
  };
  const clear = () => {
    if (guessing || gameFinished) return;
    setSlots([null, null, null, null]);
  };

  const guess = async () => {
    if (slots.some(s => s === null) || guessing || gameFinished) return;
    setGuessing(true);
    setError(null);

    try {
      const response = await apiCocktailGuess(slots as string[]);
      setAttemptsLeft(response.attempts_left);
      setHistory((current) => [...current, { fruits: slots as string[], clues: response.clues }]);

      if (response.won) {
        setResult({ won: true, message: `Рецепт угадан. Награда: ${response.reward_paw ?? 0} 🐾` });
        onRefresh();
      } else if (response.attempts_left === 0) {
        setResult({ won: false, message: 'Попытки закончились. Завтра будет новый рецепт.' });
      } else {
        setResult({ won: false, message: 'Есть зацепки. Используй подсказки ниже и попробуй ещё раз.' });
      }

      setSlots([null, null, null, null]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка игры');
    } finally {
      setGuessing(false);
    }
  };

  return (
    <div className="px-[14px] pt-[14px] pb-4 flex flex-col gap-[14px]">

      {/* Hero */}
      <div
        className="rounded-2xl p-5 text-center relative overflow-hidden"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid rgba(var(--c-teal-rgb),0.25)' }}
      >
        <div
          className="absolute inset-0 opacity-20"
          style={{ background: 'radial-gradient(ellipse at 50% 0%, rgba(var(--c-teal-rgb),0.5) 0%, transparent 70%)' }}
        />
        <div className="relative">
          <div className="text-[48px] mb-2">🥤</div>
          <p className="m-0 mb-1 text-[18px] font-extrabold">Коктейль дня</p>
          <p className="m-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Угадай секретный рецепт из 4 фруктов — получи <span style={{ color: 'var(--c-gold)', fontWeight: 700 }}>150 🐾</span>
          </p>
        </div>
      </div>

      {/* Attempt counter */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-[6px] rounded-full" style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 15%, transparent)' }}>
          <div
            className="h-full rounded-full transition-all duration-300"
            style={{
              width: `${(attemptsLeft / 10) * 100}%`,
              background: attemptsLeft > 5 ? 'var(--c-green)' : attemptsLeft > 2 ? 'var(--c-gold)' : 'var(--c-red)',
            }}
          />
        </div>
        <span className="text-[13px] font-bold shrink-0" style={{ color: 'var(--tg-theme-hint-color)' }}>
          {10 - attemptsLeft}/10
        </span>
      </div>

      {/* Slots */}
      <div className="flex gap-2 justify-center">
        {[0, 1, 2, 3].map(i => (
          <div
            key={i}
            onClick={() => slots[i] && removeAtIdx(i)}
            className="w-[64px] h-[64px] rounded-2xl grid place-items-center text-[30px] transition-all duration-150"
            style={{
              background: slots[i] ? 'rgba(var(--c-blue-rgb),0.12)' : 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)',
              border: slots[i] ? '1px solid rgba(var(--c-blue-rgb),0.4)' : '1.5px dashed color-mix(in srgb, var(--tg-theme-hint-color) 28%, transparent)',
              cursor: slots[i] && !guessing && !gameFinished ? 'pointer' : 'default',
              boxShadow: slots[i] ? '0 0 12px rgba(var(--c-blue-rgb),0.2)' : 'none',
              opacity: guessing || gameFinished ? 0.75 : 1,
            }}
          >
            {slots[i] ?? <span style={{ fontSize: 18, color: 'var(--tg-theme-hint-color)' }}>?</span>}
          </div>
        ))}
      </div>

      <p className="m-0 text-xs text-center" style={{ color: 'var(--tg-theme-hint-color)' }}>
        Нажми фрукт — добавить · Нажми ячейку — убрать
      </p>

      {/* Fruit picker */}
      <div className="flex gap-2 justify-center py-1">
        {FRUITS.map(f => (
          <button
            key={f}
            onClick={() => addFruit(f)}
            type="button"
            disabled={gameFinished || guessing}
            className="text-[36px] cursor-pointer select-none transition-transform duration-100 active:scale-90 rounded-2xl"
            style={{
              border: '2px solid rgba(var(--c-teal-rgb), 0.4)',
              background: 'rgba(var(--c-teal-rgb), 0.07)',
              padding: '6px 8px',
              lineHeight: 1,
              filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))',
              opacity: gameFinished || guessing ? 0.4 : 1,
            }}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Buttons */}
      <div className="flex gap-2">
        <button
          onClick={clear}
          disabled={guessing || gameFinished}
          className="flex-1 py-[13px] rounded-[14px] border-none font-bold text-sm"
          style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)', color: 'var(--tg-theme-text-color)' }}
        >
          Очистить
        </button>
        <button
          onClick={() => void guess()}
          disabled={slots.some(s => s === null) || guessing || gameFinished}
          className="flex-[2] py-[13px] rounded-[14px] border-none font-extrabold text-sm"
          style={{
            background: slots.every(s => s !== null) && !guessing && !gameFinished
              ? 'linear-gradient(135deg, var(--c-blue), #0066dd)'
              : 'color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)',
            color: slots.every(s => s !== null) && !guessing && !gameFinished ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)',
            boxShadow: slots.every(s => s !== null) && !guessing && !gameFinished ? '0 4px 16px rgba(var(--c-blue-rgb),0.35)' : 'none',
          }}
        >
          {guessing ? 'Проверяем...' : gameFinished ? 'Игра завершена' : 'Угадать! 🔮'}
        </button>
      </div>

      {/* Legend */}
      <div className="flex gap-4 justify-center">
        <span className="text-xs flex items-center gap-1" style={{ color: 'var(--tg-theme-hint-color)' }}>
          <span className="w-2 h-2 rounded-full bg-[var(--c-green)] inline-block" />
          верная позиция
        </span>
        <span className="text-xs flex items-center gap-1" style={{ color: 'var(--tg-theme-hint-color)' }}>
          <span className="w-2 h-2 rounded-full bg-[var(--c-blue)] inline-block" />
          есть, но не там
        </span>
      </div>

      {result && (
        <div
          className="rounded-2xl p-4"
          style={{
            background: result.won ? 'rgba(var(--c-green-rgb),0.1)' : 'rgba(var(--c-orange-rgb),0.1)',
            border: `1px solid ${result.won ? 'rgba(var(--c-green-rgb),0.35)' : 'rgba(var(--c-orange-rgb),0.35)'}`,
          }}
        >
          <p className="m-0 font-bold text-base">{result.won ? '🎉 Победа!' : '😢 Попробуй снова'}</p>
          <p className="mt-1 mb-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>{result.message}</p>
        </div>
      )}

      {error && (
        <div className="rounded-2xl p-4" style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.25)' }}>
          <p className="m-0 text-[13px] font-semibold" style={{ color: 'var(--c-red-soft)' }}>{error}</p>
        </div>
      )}

      {gameFinished && !result?.won && (
        <button
          type="button"
          onClick={() => {
            setSlots([null, null, null, null]);
            setAttemptsLeft(10);
            setHistory([]);
            setResult(null);
            setError(null);
          }}
          className="py-[13px] rounded-[14px] border-none font-bold text-sm"
          style={{ background: 'var(--surface-subtle)', color: 'var(--tg-theme-text-color)' }}
        >
          Начать заново
        </button>
      )}

      {history.length > 0 && (
        <div className="card flex flex-col gap-2">
          <p className="m-0 font-bold text-[13px]">История попыток</p>
          {history.slice().reverse().map((entry, index) => (
            <div key={`${entry.fruits.join('')}-${index}`} className="flex items-center justify-between gap-3 rounded-xl px-3 py-2 surface-subtle">
              <div className="flex gap-1 text-[20px] shrink-0">
                {entry.fruits.map((fruit, i) => <span key={`${fruit}-${i}`}>{fruit}</span>)}
              </div>
              <div className="flex gap-1 shrink-0">
                {entry.clues.map((clue) => {
                  const color = clue.status === 'correct'
                    ? 'var(--c-green)'
                    : clue.status === 'present'
                      ? 'var(--c-blue)'
                      : 'var(--tg-theme-hint-color)';
                  return <span key={clue.pos} className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />;
                })}
              </div>
            </div>
          ))}
        </div>
      )}

    </div>
  );
}

/* ──────────────────────────── MULTI ────────────────────────────────── */
function MultiTab({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [games, setGames] = useState<MpGame[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selectedGame, setSelectedGame] = useState<string>('dice');
  const [bet, setBet] = useState<BetAmount>(100);
  const [message, setMessage] = useState<string | null>(null);

  const loadGames = () => {
    setLoading(true);
    apiGetOpenGames()
      .then(r => setGames(r.games))
      .catch(e => setError((e as Error).message ?? 'Ошибка загрузки игр'))
      .finally(() => setLoading(false));
  };

  useEffect(loadGames, []);

  const createGame = async () => {
    if (busy || gs.rub < bet) return;
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await apiCreateMpGame(selectedGame, bet);
      setMessage('Игра создана. Ждём второго игрока.');
      onRefresh();
      loadGames();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка создания игры');
    } finally {
      setBusy(false);
    }
  };

  const joinGame = async (gameId: number) => {
    if (busy) return;
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await apiJoinMpGame(gameId);
      setMessage('Ты присоединился к игре.');
      onRefresh();
      loadGames();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка входа в игру');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="p-[14px] flex flex-col gap-3">
      <div className="card flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <p className="m-0 font-bold text-[15px]">Создать игру</p>
          <span className="text-[12px] text-tg-hint">Баланс: ₽{fmt(gs.rub)}</span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {GAMES.map((game) => {
            const active = game.id === selectedGame;
            return (
              <button
                key={game.id}
                onClick={() => setSelectedGame(game.id)}
                className="px-3 py-2 rounded-xl border-none text-left"
                style={{
                  background: active ? 'rgba(var(--c-blue-rgb),0.15)' : 'var(--surface-subtle)',
                  color: active ? 'var(--tg-theme-text-color)' : 'var(--tg-theme-hint-color)',
                  border: `1px solid ${active ? 'rgba(var(--c-blue-rgb),0.35)' : 'var(--surface-overlay-border)'}`,
                }}
              >
                <span className="block font-semibold text-[13px]">{game.emoji} {game.name}</span>
              </button>
            );
          })}
        </div>

        <div className="flex gap-2">
          {BET_AMOUNTS.map((amount) => {
            const active = amount === bet;
            return (
              <button
                key={amount}
                onClick={() => setBet(amount)}
                className="flex-1 py-2 rounded-xl border-none font-bold text-[13px]"
                style={{
                  background: active ? 'rgba(var(--c-green-rgb),0.15)' : 'var(--surface-subtle)',
                  color: active ? 'var(--c-green)' : 'var(--tg-theme-hint-color)',
                  border: `1px solid ${active ? 'rgba(var(--c-green-rgb),0.3)' : 'var(--surface-overlay-border)'}`,
                }}
              >
                ₽{fmt(amount)}
              </button>
            );
          })}
        </div>

        <button
          onClick={() => void createGame()}
          disabled={busy || gs.rub < bet}
          className="py-[15px] rounded-2xl border-none font-extrabold text-base disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, var(--c-green), #30b34e)', color: 'var(--tg-theme-button-text-color)', boxShadow: '0 4px 16px rgba(var(--c-green-rgb),0.3)' }}
        >
          {busy ? 'Создаём...' : '+ Создать игру'}
        </button>
      </div>

      {message && <div className="card" style={{ background: 'rgba(var(--c-green-rgb),0.1)', borderColor: 'rgba(var(--c-green-rgb),0.25)' }}><p className="m-0 text-[13px]" style={{ color: 'var(--c-green)' }}>{message}</p></div>}

      {loading && (
        <div className="flex justify-center py-6">
          <div className="spinner" />
        </div>
      )}
      {error && (
        <p className="text-center text-sm" style={{ color: 'var(--c-red-soft)' }}>Ошибка загрузки игр</p>
      )}

      {!loading && !error && games.length === 0 && (
        <div className="text-center py-10">
          <div className="text-[48px] mb-3">🏆</div>
          <p className="m-0 font-bold">Нет открытых игр</p>
          <p className="mt-1 mb-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Создай первую и пригласи друга!
          </p>
        </div>
      )}

      {games.map(g => {
        const gameDef = getGameDef(g.game_type);
        return (
        <div key={g.id} className="card flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl grid place-items-center text-xl shrink-0"
            style={{ background: 'rgba(var(--c-blue-rgb),0.15)', border: '1px solid rgba(var(--c-blue-rgb),0.25)' }}
          >
            {gameDef?.emoji ?? '🎲'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="m-0 font-bold text-sm truncate">{gameDef ? `${gameDef.emoji} ${gameDef.name}` : g.game_type}</p>
            <p className="mt-[2px] mb-0 text-xs" style={{ color: 'var(--tg-theme-hint-color)' }}>
              {g.creator_nickname} · ставка ₽{fmt(g.bet_rub)}
            </p>
          </div>
          <button
            onClick={() => void joinGame(g.id)}
            disabled={busy}
            className="px-4 py-2 rounded-xl border-none font-bold text-[13px] shrink-0"
            style={{ background: 'linear-gradient(135deg, var(--c-blue), #0066dd)', color: 'var(--tg-theme-button-text-color)', boxShadow: '0 2px 8px rgba(var(--c-blue-rgb),0.3)' }}
          >
            Войти
          </button>
        </div>
      )})}
    </div>
  );
}

/* ──────────────────────────── SOLO ─────────────────────────────────── */
function SoloTab({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [selectedGame, setSelectedGame] = useState<string>('dice');
  const [bet, setBet] = useState<BetAmount>(100);
  const [stats, setStats] = useState<SoloStats | null>(null);
  const [showStats, setShowStats] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [result, setResult] = useState<{ won: boolean; result: string; score: number; rub_delta: number; new_rub: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (showStats) {
      apiGetSoloStats().then(setStats).catch(() => {});
    }
  }, [showStats]);

  const winRate = stats && stats.games_played > 0
    ? Math.round((stats.wins / stats.games_played) * 100)
    : 0;

  const playSolo = async () => {
    if (playing || gs.rub < bet) return;
    setPlaying(true);
    setError(null);
    try {
      const response = await apiStartSoloGame(selectedGame, bet);
      setResult(response);
      if (showStats) {
        apiGetSoloStats().then(setStats).catch(() => {});
      }
      onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка запуска игры');
    } finally {
      setPlaying(false);
    }
  };

  return (
    <div className="p-[14px] flex flex-col gap-[10px]">

      {/* Stats toggle */}
      <button
        onClick={() => setShowStats(s => !s)}
        className="flex items-center gap-3 px-[14px] py-[12px] rounded-2xl border-none text-left w-full"
        style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 15%, transparent)' }}
      >
        <span className="text-lg">📊</span>
        <span className="flex-1 font-semibold text-sm">Моя статистика</span>
        <span className="text-xs" style={{ color: 'var(--tg-theme-hint-color)' }}>{showStats ? '▲' : '▼'}</span>
      </button>

      {showStats && stats && (
        <div className="card flex flex-col gap-3">
          <div className="grid grid-cols-3 gap-2">
            <div className="text-center rounded-xl py-3" style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 7%, transparent)' }}>
              <p className="m-0 text-[20px] font-extrabold">{stats.games_played}</p>
              <p className="m-0 text-[11px] mt-1" style={{ color: 'var(--tg-theme-hint-color)' }}>Игр</p>
            </div>
            <div className="text-center rounded-xl py-3" style={{ background: 'rgba(var(--c-green-rgb),0.08)' }}>
              <p className="m-0 text-[20px] font-extrabold" style={{ color: 'var(--c-green)' }}>{stats.wins}</p>
              <p className="m-0 text-[11px] mt-1" style={{ color: 'var(--tg-theme-hint-color)' }}>Победы</p>
            </div>
            <div className="text-center rounded-xl py-3" style={{ background: 'rgba(var(--c-orange-rgb),0.08)' }}>
              <p className="m-0 text-[20px] font-extrabold" style={{ color: 'var(--c-orange)' }}>{stats.losses}</p>
              <p className="m-0 text-[11px] mt-1" style={{ color: 'var(--tg-theme-hint-color)' }}>Поражения</p>
            </div>
          </div>

          {stats.games_played > 0 && (
            <div>
              <div className="flex justify-between text-[12px] mb-1">
                <span style={{ color: 'var(--tg-theme-hint-color)' }}>Процент побед</span>
                <span className="font-bold" style={{ color: winRate >= 50 ? 'var(--c-green)' : 'var(--c-orange)' }}>
                  {winRate}%
                </span>
              </div>
              <div className="h-[6px] rounded-full" style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 15%, transparent)' }}>
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${winRate}%`,
                    background: winRate >= 50
                      ? 'linear-gradient(90deg, var(--c-green), var(--c-teal))'
                      : 'linear-gradient(90deg, var(--c-amber), var(--c-red))',
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Game list */}
      {GAMES.map(g => {
        const isSelected = selectedGame === g.id;
        const colors = GAME_COLORS[g.id] ?? GAME_COLORS.dice;
        return (
          <div
            key={g.id}
            onClick={() => setSelectedGame(g.id)}
            className="rounded-2xl p-[14px] flex items-center gap-[14px] cursor-pointer"
            style={{
              background: isSelected
                ? `linear-gradient(135deg, color-mix(in srgb, ${colors.from} 10%, transparent), color-mix(in srgb, ${colors.to} 6%, transparent))`
                : 'color-mix(in srgb, var(--tg-theme-hint-color) 7%, transparent)',
              border: isSelected
                ? `1.5px solid color-mix(in srgb, ${colors.from} 33%, transparent)`
                : '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)',
              boxShadow: isSelected ? `0 4px 20px ${colors.glow}` : 'none',
              transition: 'box-shadow 200ms, border 200ms',
            }}
          >
            <div
              className="w-[48px] h-[48px] rounded-xl grid place-items-center text-[24px] shrink-0"
              style={{
                background: `linear-gradient(135deg, color-mix(in srgb, ${colors.from} 15%, transparent), color-mix(in srgb, ${colors.to} 8%, transparent))`,
                border: `1px solid color-mix(in srgb, ${colors.from} 19%, transparent)`,
                boxShadow: isSelected ? `0 0 12px ${colors.glow}` : 'none',
              }}
            >
              {g.emoji}
            </div>
            <div className="flex-1 min-w-0">
              <p className="m-0 font-bold text-[15px]">{g.name}</p>
              <p className="mt-[3px] mb-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                {g.description}
              </p>
              <p className="mt-[1px] mb-0 text-[11px]" style={{ color: isSelected ? colors.from : 'var(--tg-theme-hint-color)', opacity: 0.8 }}>
                {g.detail}
              </p>
            </div>
            {isSelected && (
              <div
                className="w-6 h-6 rounded-full grid place-items-center shrink-0 text-[14px]"
                style={{ background: `linear-gradient(135deg, ${colors.from}, ${colors.to})` }}
              >
                ✓
              </div>
            )}
          </div>
        );
      })}

      <div className="flex gap-2 mt-1">
        {BET_AMOUNTS.map((amount) => {
          const active = amount === bet;
          return (
            <button
              key={amount}
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

      {selectedGame && (() => {
        const colors = GAME_COLORS[selectedGame] ?? GAME_COLORS.dice;
        return (
          <button
            onClick={() => void playSolo()}
            disabled={playing || gs.rub < bet}
            className="mt-1 py-[15px] rounded-2xl border-none font-extrabold text-[16px]"
            style={{
              background: `linear-gradient(135deg, ${colors.from}, ${colors.to})`,
              color: 'var(--tg-theme-button-text-color)',
              boxShadow: `0 6px 20px ${colors.glow}`,
              opacity: playing || gs.rub < bet ? 0.6 : 1,
            }}
          >
            {playing ? 'Играем...' : `Играть — ставка ₽${fmt(bet)}`}
          </button>
        );
      })()}

      {error && (
        <div className="rounded-2xl p-4" style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.25)' }}>
          <p className="m-0 text-[13px] font-semibold" style={{ color: 'var(--c-red-soft)' }}>{error}</p>
        </div>
      )}

      {result && (
        <div className="card" style={{ background: result.won ? 'rgba(var(--c-green-rgb),0.1)' : 'rgba(var(--c-orange-rgb),0.1)', borderColor: result.won ? 'rgba(var(--c-green-rgb),0.25)' : 'rgba(var(--c-orange-rgb),0.25)' }}>
          <p className="m-0 font-bold text-[15px]">{result.won ? 'Победа' : 'Поражение'}</p>
          <p className="mt-1 mb-0 text-[13px] text-tg-hint">{result.result} · Счёт {result.score}</p>
          <p className="mt-2 mb-0 text-[13px] font-semibold" style={{ color: result.won ? 'var(--c-green)' : 'var(--c-orange)' }}>
            {result.rub_delta >= 0 ? '+' : ''}{fmt(result.rub_delta)} ₽
          </p>
        </div>
      )}
    </div>
  );
}

/* ──────────────────────────── BASKETBALL ───────────────────────────── */
const BBALL_ROUNDS = 5;
const rollScore = (r: number) => r >= 3 ? 2 : 0;
const rollResult = (r: number) => r >= 3
  ? { label: 'Гол!', icon: '🏀', color: 'var(--c-green)' }
  : { label: 'Мимо', icon: '❌', color: 'var(--tg-theme-hint-color)' };

interface ThrowRecord { round: number; playerRoll: number; aiRoll: number }
type BballPhase = 'idle' | 'player-anim' | 'ai-anim' | 'game-over';

function BasketballTab() {
  const [phase, setPhase] = useState<BballPhase>('idle');
  const [history, setHistory] = useState<ThrowRecord[]>([]);
  const [animLabel, setAnimLabel] = useState('');
  const tgsRef = useRef<TgsHandle>(null);

  const round = history.length + 1;
  const gameOver = phase === 'game-over';
  const playerScore = history.reduce((s, h) => s + rollScore(h.playerRoll), 0);
  const aiScore = history.reduce((s, h) => s + rollScore(h.aiRoll), 0);

  const handleThrow = async () => {
    if (phase !== 'idle' || history.length >= BBALL_ROUNDS) return;
    const currentRound = history.length + 1;
    const pr = Math.floor(Math.random() * 6);
    const ar = Math.floor(Math.random() * 6);

    setAnimLabel('Ваш бросок');
    setPhase('player-anim');
    await tgsRef.current?.playAnimation(`/telegram-dice/basketball/${pr}.tgs`);

    setAnimLabel('Бросок ИИ');
    setPhase('ai-anim');
    await tgsRef.current?.playAnimation(`/telegram-dice/basketball/${ar}.tgs`);

    const record: ThrowRecord = { round: currentRound, playerRoll: pr, aiRoll: ar };
    setHistory(prev => [...prev, record]);
    setPhase(currentRound >= BBALL_ROUNDS ? 'game-over' : 'idle');
  };

  const resetGame = () => {
    setPhase('idle');
    setHistory([]);
    setAnimLabel('');
  };

  const isAnimating = phase === 'player-anim' || phase === 'ai-anim';
  const lastRecord = history[history.length - 1];

  let winner: 'player' | 'ai' | 'draw' | null = null;
  if (gameOver) winner = playerScore > aiScore ? 'player' : playerScore < aiScore ? 'ai' : 'draw';

  return (
    <div className="px-[14px] pt-[14px] pb-6 flex flex-col gap-[14px]">

      {/* Scoreboard */}
      <div
        className="rounded-2xl overflow-hidden relative"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid rgba(var(--c-orange-rgb),0.22)' }}
      >
        <div className="absolute inset-0 pointer-events-none" style={{ background: 'radial-gradient(ellipse at 50% -10%, rgba(var(--c-orange-rgb),0.15) 0%, transparent 65%)' }} />
        <div className="relative flex items-center justify-between px-5 py-4">
          <div className="text-center flex-1">
            <p className="m-0 text-[11px] font-semibold uppercase tracking-wide" style={{ color: 'var(--tg-theme-hint-color)' }}>Вы</p>
            <p className="m-0 text-[36px] font-extrabold leading-none mt-1" style={{ color: 'var(--c-orange)' }}>{playerScore}</p>
          </div>
          <div className="text-center px-4">
            <p className="m-0 text-[13px] font-bold" style={{ color: 'var(--tg-theme-hint-color)' }}>
              {gameOver ? 'Конец' : `Раунд ${Math.min(round, BBALL_ROUNDS)}/${BBALL_ROUNDS}`}
            </p>
            <p className="m-0 text-[22px]">🏀</p>
          </div>
          <div className="text-center flex-1">
            <p className="m-0 text-[11px] font-semibold uppercase tracking-wide" style={{ color: 'var(--tg-theme-hint-color)' }}>ИИ</p>
            <p className="m-0 text-[36px] font-extrabold leading-none mt-1" style={{ color: 'var(--c-blue)' }}>{aiScore}</p>
          </div>
        </div>
      </div>

      {/* Animation area */}
      <div
        className="rounded-2xl flex flex-col items-center justify-center gap-2 py-4"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)', minHeight: 220 }}
      >
        {/* Label row — always rendered, empty when idle */}
        <p
          className="m-0 text-[13px] font-semibold"
          style={{ color: 'var(--tg-theme-hint-color)', visibility: isAnimating ? 'visible' : 'hidden', minHeight: 20 }}
        >
          {animLabel}
        </p>

        {/* TgsPlayer always at the same position; emoji overlay covers it when idle */}
        <div style={{ position: 'relative', width: 180, height: 180, flexShrink: 0 }}>
          <TgsPlayer ref={tgsRef} size={180} />
          {!isAnimating && (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              {gameOver ? (
                <>
                  <span style={{ fontSize: 64 }}>
                    {winner === 'player' ? '🎉' : winner === 'ai' ? '😢' : '🤝'}
                  </span>
                </>
              ) : (
                <span style={{ fontSize: 72 }}>🏀</span>
              )}
            </div>
          )}
        </div>

        {/* Status text below animation box */}
        {!isAnimating && !gameOver && (
          <div className="text-center mt-1">
            {lastRecord ? (
              <div className="flex gap-6">
                <span className="text-[13px]" style={{ color: rollResult(lastRecord.playerRoll).color }}>
                  Вы {rollResult(lastRecord.playerRoll).icon} +{rollScore(lastRecord.playerRoll)}
                </span>
                <span className="text-[13px]" style={{ color: rollResult(lastRecord.aiRoll).color }}>
                  ИИ {rollResult(lastRecord.aiRoll).icon} +{rollScore(lastRecord.aiRoll)}
                </span>
              </div>
            ) : (
              <p className="m-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>Нажми «Бросок» чтобы начать</p>
            )}
          </div>
        )}

        {gameOver && (
          <div className="text-center mt-1">
            <p className="m-0 font-extrabold text-[18px]">
              {winner === 'player' ? 'Вы победили!' : winner === 'ai' ? 'ИИ победил' : 'Ничья!'}
            </p>
            <p className="m-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
              Итог: {playerScore} — {aiScore}
            </p>
          </div>
        )}
      </div>

      {/* Throw / Reset button */}
      {gameOver ? (
        <button
          onClick={resetGame}
          className="py-[15px] rounded-2xl border-none font-extrabold text-[16px]"
          style={{ background: 'linear-gradient(135deg, var(--c-orange), var(--c-red))', color: 'var(--tg-theme-button-text-color)', boxShadow: '0 6px 20px rgba(var(--c-orange-rgb),0.35)' }}
        >
          Играть снова 🔄
        </button>
      ) : (
        <button
          onClick={() => void handleThrow()}
          disabled={isAnimating}
          className="py-[15px] rounded-2xl border-none font-extrabold text-[16px] transition-opacity"
          style={{
            background: isAnimating
              ? 'color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)'
              : 'linear-gradient(135deg, var(--c-orange), var(--c-red))',
            color: isAnimating ? 'var(--tg-theme-hint-color)' : 'var(--tg-theme-button-text-color)',
            boxShadow: isAnimating ? 'none' : '0 6px 20px rgba(var(--c-orange-rgb),0.35)',
          }}
        >
          {isAnimating ? animLabel + '...' : '🏀 Бросок'}
        </button>
      )}

      {/* History */}
      {history.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="m-0 text-[12px] font-bold uppercase tracking-wide" style={{ color: 'var(--tg-theme-hint-color)' }}>История бросков</p>
          {history.slice().reverse().map((h) => {
            const pr = rollResult(h.playerRoll);
            const ar = rollResult(h.aiRoll);
            return (
              <div
                key={h.round}
                className="flex items-center gap-2 rounded-xl px-3 py-2"
                style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 10%, transparent)' }}
              >
                <span className="text-[11px] font-bold w-[44px] shrink-0" style={{ color: 'var(--tg-theme-hint-color)' }}>
                  Р{h.round}
                </span>
                <div className="flex-1 flex items-center gap-1">
                  <span className="text-[11px]" style={{ color: pr.color }}>{pr.icon} Вы +{rollScore(h.playerRoll)}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-[11px]" style={{ color: ar.color }}>{ar.icon} ИИ +{rollScore(h.aiRoll)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ──────────────────────────── MAIN PAGE ────────────────────────────── */
export function GamesPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [tab, setTab] = useState<GamesTab>('solo');

  const tabs: { id: GamesTab; emoji: string; label: string }[] = [
    { id: 'solo',       emoji: '🤖', label: 'Соло' },
    { id: 'multi',      emoji: '🏆', label: 'Мульти' },
    { id: 'cocktail',   emoji: '🥤', label: 'Коктейль' },
    { id: 'basketball', emoji: '🏀', label: 'Баскет' },
  ];

  return (
    <div className="page-content-safe">

      {/* Header */}
      <div
        className="relative overflow-hidden"
        style={{ paddingTop: '16px', paddingBottom: 20 }}
      >
        {/* Background glow */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse at 50% -20%, rgba(var(--c-blue-rgb),0.12) 0%, transparent 65%)' }}
        />
        <div className="relative px-[14px]">
          <div className="flex items-center gap-3 mb-1">
            <div
              className="w-10 h-10 rounded-xl grid place-items-center text-[20px]"
              style={{ background: 'rgba(var(--c-blue-rgb),0.15)', border: '1px solid rgba(var(--c-blue-rgb),0.25)' }}
            >
              🎮
            </div>
            <p className="m-0 text-[22px] font-extrabold tracking-tight">Игры</p>
          </div>
          <p className="m-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)', paddingLeft: 52 }}>
            Играй против ИИ или соревнуйся с друзьями!
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div
        className="flex mx-[14px] rounded-2xl p-1 mb-1"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 18%, transparent)' }}
      >
        {tabs.map(t => {
          const isActive = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className="flex-1 flex items-center justify-center gap-[6px] py-[9px] rounded-xl border-none transition-all duration-200"
              style={{
                background: isActive ? 'color-mix(in srgb, var(--tg-theme-button-color) 15%, transparent)' : 'transparent',
                color: isActive ? 'var(--tg-theme-text-color)' : 'var(--tg-theme-hint-color)',
                boxShadow: isActive ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
              }}
            >
              <span className="text-[15px]">{t.emoji}</span>
              <span className="text-[12px] font-bold">{t.label}</span>
            </button>
          );
        })}
      </div>

      <div>
        {tab === 'solo'       && <SoloTab gs={gs} onRefresh={onRefresh} />}
        {tab === 'multi'      && <MultiTab gs={gs} onRefresh={onRefresh} />}
        {tab === 'cocktail'   && <CocktailTab onRefresh={onRefresh} />}
        {tab === 'basketball' && <BasketballTab />}
      </div>
    </div>
  );
}
