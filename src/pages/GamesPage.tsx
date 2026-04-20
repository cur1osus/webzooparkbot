import { useEffect, useState } from 'react';
import { fmt } from '../utils/format';
import type { GameState, MpGame, SoloStats } from '../types';
import { GAMES } from '../data/games';
import { apiGetOpenGames, apiGetSoloStats } from '../api';

type GamesTab = 'solo' | 'multi' | 'cocktail';

const FRUITS = ['🍓', '🫐', '🍏', '🍐', '🍇', '🍒'];

const GAME_COLORS: Record<string, { from: string; to: string; glow: string }> = {
  darts:    { from: 'var(--c-orange)', to: 'var(--c-red)', glow: 'rgba(var(--c-orange-rgb),0.35)' },
  bowling:  { from: 'var(--c-green)', to: 'var(--c-teal)', glow: 'rgba(var(--c-green-rgb),0.35)' },
  dice:     { from: 'var(--c-blue)', to: 'var(--c-cyan)', glow: 'rgba(var(--c-blue-rgb),0.35)' },
  football: { from: 'var(--c-gold)', to: 'var(--c-amber)', glow: 'rgba(var(--c-gold-rgb),0.35)' },
};

/* ──────────────────────────── COCKTAIL ──────────────────────────────── */
function CocktailTab({ gs: _gs }: { gs: GameState }) {
  const [slots, setSlots] = useState<string[]>([]);
  const [attempt, setAttempt] = useState(1);
  const [attemptsLeft, setAttemptsLeft] = useState(10);
  const [result, setResult] = useState<{ won: boolean; message: string } | null>(null);

  const addFruit = (fruit: string) => {
    if (slots.length < 4) setSlots(s => [...s, fruit]);
  };
  const removeAtIdx = (i: number) => setSlots(s => s.filter((_, idx) => idx !== i));
  const clear = () => setSlots([]);

  const guess = async () => {
    if (slots.length !== 4) return;
    setAttempt(a => a + 1);
    setAttemptsLeft(a => Math.max(0, a - 1));
    void setResult;
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
          <div className="text-[48px] mb-2">🍹</div>
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
          {attempt}/10
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
              cursor: slots[i] ? 'pointer' : 'default',
              boxShadow: slots[i] ? '0 0 12px rgba(var(--c-blue-rgb),0.2)' : 'none',
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
      <div className="flex gap-3 justify-center py-1">
        {FRUITS.map(f => (
          <span
            key={f}
            onClick={() => addFruit(f)}
            className="text-[32px] cursor-pointer select-none transition-transform duration-100 active:scale-90"
            style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))' }}
          >
            {f}
          </span>
        ))}
      </div>

      {/* Buttons */}
      <div className="flex gap-2">
        <button
          onClick={clear}
          className="flex-1 py-[13px] rounded-[14px] border-none font-bold text-sm"
          style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)', color: 'var(--tg-theme-text-color)' }}
        >
          Очистить
        </button>
        <button
          onClick={() => void guess()}
          disabled={slots.length !== 4}
          className="flex-[2] py-[13px] rounded-[14px] border-none font-extrabold text-sm"
          style={{
            background: slots.length === 4
              ? 'linear-gradient(135deg, var(--c-blue), #0066dd)'
              : 'color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)',
            color: slots.length === 4 ? '#fff' : 'var(--tg-theme-hint-color)',
            boxShadow: slots.length === 4 ? '0 4px 16px rgba(var(--c-blue-rgb),0.35)' : 'none',
          }}
        >
          Угадать! 🔮
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

      {/* How to play */}
      <div className="card">
        <p className="m-0 mb-[6px] font-bold text-[13px]">Как играть:</p>
        <p className="m-0 text-xs leading-relaxed" style={{ color: 'var(--tg-theme-hint-color)' }}>
          Каждый день — новый секретный коктейль из 4 фруктов 🍓🫐🍏🍐🍇🍒. Фрукты могут повторяться.
          У тебя 10 попыток. После каждой — подсказка. Угадаешь — получи 150 🐾!
        </p>
      </div>
    </div>
  );
}

/* ──────────────────────────── MULTI ────────────────────────────────── */
function MultiTab({ gs: _gs }: { gs: GameState }) {
  const [games, setGames] = useState<MpGame[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGetOpenGames()
      .then(r => setGames(r.games))
      .catch(e => setError((e as Error).message ?? 'Ошибка загрузки игр'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-[14px] flex flex-col gap-3">
      <button
        className="py-[15px] rounded-2xl border-none font-extrabold text-base"
        style={{ background: 'linear-gradient(135deg, var(--c-green), #30b34e)', color: '#fff', boxShadow: '0 4px 16px rgba(var(--c-green-rgb),0.3)' }}
      >
        + Создать игру
      </button>

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

      {games.map(g => (
        <div key={g.id} className="card flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl grid place-items-center text-xl shrink-0"
            style={{ background: 'rgba(var(--c-blue-rgb),0.15)', border: '1px solid rgba(var(--c-blue-rgb),0.25)' }}
          >
            🎲
          </div>
          <div className="flex-1 min-w-0">
            <p className="m-0 font-bold text-sm truncate">{g.game_type}</p>
            <p className="mt-[2px] mb-0 text-xs" style={{ color: 'var(--tg-theme-hint-color)' }}>
              {g.creator_nickname} · ставка ₽{fmt(g.bet_rub)}
            </p>
          </div>
          <button
            className="px-4 py-2 rounded-xl border-none font-bold text-[13px] shrink-0"
            style={{ background: 'linear-gradient(135deg, var(--c-blue), #0066dd)', color: '#fff', boxShadow: '0 2px 8px rgba(var(--c-blue-rgb),0.3)' }}
          >
            Войти
          </button>
        </div>
      ))}
    </div>
  );
}

/* ──────────────────────────── SOLO ─────────────────────────────────── */
function SoloTab({ gs: _gs }: { gs: GameState }) {
  const [selectedGame, setSelectedGame] = useState<string>('dice');
  const [stats, setStats] = useState<SoloStats | null>(null);
  const [showStats, setShowStats] = useState(false);

  useEffect(() => {
    if (showStats) {
      apiGetSoloStats().then(setStats).catch(() => {});
    }
  }, [showStats]);

  const winRate = stats && stats.games_played > 0
    ? Math.round((stats.wins / stats.games_played) * 100)
    : 0;

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
            className="rounded-2xl p-[14px] flex items-center gap-[14px] cursor-pointer transition-all duration-200"
            style={{
              background: isSelected
                ? `linear-gradient(135deg, ${colors.from}18, ${colors.to}10)`
                : 'color-mix(in srgb, var(--tg-theme-hint-color) 7%, transparent)',
              border: isSelected
                ? `1.5px solid ${colors.from}55`
                : '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)',
              boxShadow: isSelected ? `0 4px 20px ${colors.glow}` : 'none',
            }}
          >
            <div
              className="w-[48px] h-[48px] rounded-xl grid place-items-center text-[24px] shrink-0"
              style={{
                background: `linear-gradient(135deg, ${colors.from}25, ${colors.to}15)`,
                border: `1px solid ${colors.from}30`,
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

      {selectedGame && (() => {
        const colors = GAME_COLORS[selectedGame] ?? GAME_COLORS.dice;
        return (
          <button
            className="mt-1 py-[15px] rounded-2xl border-none font-extrabold text-[16px]"
            style={{
              background: `linear-gradient(135deg, ${colors.from}, ${colors.to})`,
              color: '#fff',
              boxShadow: `0 6px 20px ${colors.glow}`,
            }}
          >
            Играть — ставка ₽{fmt(100)}
          </button>
        );
      })()}
    </div>
  );
}

/* ──────────────────────────── MAIN PAGE ────────────────────────────── */
export function GamesPage({ gs }: { gs: GameState }) {
  const [tab, setTab] = useState<GamesTab>('solo');

  const tabs: { id: GamesTab; emoji: string; label: string }[] = [
    { id: 'solo',     emoji: '🤖', label: 'Соло' },
    { id: 'multi',    emoji: '🏆', label: 'Мульти' },
    { id: 'cocktail', emoji: '🍹', label: 'Коктейль' },
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
        {tab === 'solo'     && <SoloTab gs={gs} />}
        {tab === 'multi'    && <MultiTab gs={gs} />}
        {tab === 'cocktail' && <CocktailTab gs={gs} />}
      </div>
    </div>
  );
}
