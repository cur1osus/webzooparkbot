import { useEffect, useState } from 'react';
import { apiCocktailGuess, apiGetCocktailState } from '@/api';
import type { CocktailHistoryEntry } from '@/types';

// Must stay in sync with COCKTAIL_FRUITS on the backend (catalog.py): the secret is
// drawn from that set, so a mismatch makes the puzzle unsolvable / rejects valid picks.
const FRUITS = ['🍓', '🫐', '🍏', '🍐', '🍇', '🍒'];

export function CocktailTab({ onRefresh }: { onRefresh: () => void }) {
  const [slots, setSlots] = useState<(string | null)[]>([null, null, null, null]);
  const [attemptsLeft, setAttemptsLeft] = useState(10);
  const [guessing, setGuessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ won: boolean; message: string } | null>(null);
  const [history, setHistory] = useState<CocktailHistoryEntry[]>([]);
  const [winnerNickname, setWinnerNickname] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    void apiGetCocktailState()
      .then((state) => {
        if (!mounted) return;
        setAttemptsLeft(state.attempts_left);
        setHistory(state.history);
        setWinnerNickname(state.winner_nickname);
        if (state.solved) {
          setResult({
            won: true,
            message: state.rewarded
              ? 'Рецепт угадан. Награда: 150 🐾'
              : 'Рецепт угадан, но 150 🐾 уже достались первому победителю.',
          });
        } else if (state.attempts_left === 0) {
          setResult({ won: false, message: 'Попытки закончились. Завтра будет новый рецепт.' });
        }
      })
      .catch(() => {
        // The board remains usable if an older server has not deployed the read endpoint.
      });
    return () => { mounted = false; };
  }, []);

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
      setWinnerNickname(response.winner_nickname ?? null);

      if (response.won) {
        setResult({
          won: true,
          message: response.reward_paw
            ? `Рецепт угадан. Награда: ${response.reward_paw} 🐾`
            : 'Рецепт угадан, но 150 🐾 уже достались первому победителю.',
        });
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

      {winnerNickname && (
        <div
          className="rounded-2xl p-4"
          style={{ background: 'rgba(var(--c-gold-rgb),0.1)', border: '1px solid rgba(var(--c-gold-rgb),0.35)' }}
        >
          <p className="m-0 font-bold text-base">🏆 Победитель коктейля</p>
          <p className="mt-1 mb-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            {winnerNickname} первым угадал рецепт и получил 150 🐾
          </p>
        </div>
      )}

      {error && (
        <div className="rounded-2xl p-4" style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.25)' }}>
          <p className="m-0 text-[13px] font-semibold" style={{ color: 'var(--c-red-soft)' }}>{error}</p>
        </div>
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
