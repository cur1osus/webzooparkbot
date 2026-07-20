import { useEffect, useMemo, useRef, useState } from 'react';
import { apiGetSafeState, apiSafeGuess } from '@/api';
import { fmt } from '@/utils/format';
import type { SafeBoardEntry, SafeState } from '@/types';

const DIGITS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'];

function countdown(target: string, nowMs: number): string {
  const seconds = Math.max(0, Math.ceil((new Date(target).getTime() - nowMs) / 1000));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours > 0 ? `${hours} ч ${minutes} мин` : `${minutes} мин ${seconds % 60} с`;
}

function dayLabel(day: string): string {
  return new Date(`${day}T00:00:00`).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
}

/** Published guesses, newest day first, so the freshest clues sit at the top. */
function groupByDay(board: SafeBoardEntry[]): Array<[string, SafeBoardEntry[]]> {
  const days = new Map<string, SafeBoardEntry[]>();
  for (const entry of board) {
    const existing = days.get(entry.day);
    if (existing) existing.push(entry);
    else days.set(entry.day, [entry]);
  }
  return [...days.entries()].reverse();
}

export function SafeTab({ onRefresh }: { onRefresh: () => void }) {
  const [state, setState] = useState<SafeState | null>(null);
  const [slots, setSlots] = useState<string[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const wasOpen = useRef<boolean | null>(null);

  const load = () =>
    apiGetSafeState()
      .then((next) => {
        setState(next);
        // The window flipping is the moment every sealed guess becomes public, so the
        // board must be refetched rather than waiting for the player to navigate away.
        if (wasOpen.current !== null && wasOpen.current !== next.is_open) onRefresh();
        wasOpen.current = next.is_open;
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Не удалось открыть сейф'));

  useEffect(() => {
    void load();
    const timer = setInterval(() => setNowMs(Date.now()), 1000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Poll across the boundary so a player watching the clock sees the reveal land.
  useEffect(() => {
    const poll = setInterval(() => void load(), 30_000);
    return () => clearInterval(poll);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const codeLength = state?.code_length ?? 4;
  const grouped = useMemo(() => groupByDay(state?.board ?? []), [state?.board]);
  const ready = slots.length === codeLength;
  const canGuess = Boolean(state?.is_open) && (state?.attempts_left ?? 0) > 0 && ready && !sending;

  const submit = async () => {
    if (!canGuess) return;
    setSending(true);
    setError(null);
    try {
      const result = await apiSafeGuess(slots.join(''));
      setSlots([]);
      setState((current) =>
        current
          ? { ...current, attempts_left: result.attempts_left, pending_codes: [...current.pending_codes, result.accepted] }
          : current,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось отправить код');
    } finally {
      setSending(false);
    }
  };

  if (!state) {
    return (
      <div className="px-[14px] pt-[14px]">
        <p className="text-center text-tg-hint text-[13px]">{error ?? 'Открываем сейф...'}</p>
      </div>
    );
  }

  const open = state.is_open;

  return (
    <div className="px-[14px] pt-[14px] pb-4 flex flex-col gap-[14px]">

      <div
        className="rounded-2xl p-5 text-center relative overflow-hidden"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid rgba(var(--c-gold-rgb),0.25)' }}
      >
        <div
          className="absolute inset-0 opacity-20"
          style={{ background: 'radial-gradient(ellipse at 50% 0%, rgba(var(--c-gold-rgb),0.5) 0%, transparent 70%)' }}
        />
        <div className="relative">
          <div className="text-[48px] mb-2">{open ? '🔓' : '🔐'}</div>
          <p className="m-0 mb-1 text-[18px] font-extrabold">Сейф банка</p>
          <p className="m-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            В сейфе <span style={{ color: 'var(--c-gold)', fontWeight: 700 }}>$ {fmt(state.prize_usd)}</span> — половина
            всех комиссий банка
          </p>
          <p className="m-0 mt-2 text-[12px] font-semibold" style={{ color: open ? 'var(--c-green)' : 'var(--c-gold)' }}>
            {open
              ? `Открыт ещё ${countdown(state.closes_at, nowMs)}`
              : `Откроется через ${countdown(state.opens_at, nowMs)} · каждый день в 19:00`}
          </p>
        </div>
      </div>

      <div
        className="rounded-2xl px-4 py-3 text-[12px] leading-relaxed"
        style={{ background: 'rgba(var(--c-blue-rgb),0.08)', border: '1px solid rgba(var(--c-blue-rgb),0.22)' }}
      >
        Догадки всех игроков закрыты до конца окна и вскрываются разом. Никто не видит чужие
        подсказки раньше тебя — поэтому заходить последним бессмысленно.
      </div>

      {open && (
        <>
          {/* Ячейки тянутся, а не заданы жёстко: шесть штук по 58px не помещаются в
              375px, и код любой длины должен влезать без горизонтальной прокрутки. */}
          <div className="flex gap-1.5 justify-center">
            {Array.from({ length: codeLength }, (_, index) => (
              <div
                key={index}
                onClick={() => setSlots((current) => current.slice(0, index))}
                className="flex-1 min-w-0 max-w-[58px] h-[64px] rounded-2xl grid place-items-center text-[26px] font-black transition-all duration-150"
                style={{
                  background: slots[index]
                    ? 'rgba(var(--c-gold-rgb),0.12)'
                    : 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)',
                  border: slots[index]
                    ? '1px solid rgba(var(--c-gold-rgb),0.45)'
                    : '1.5px dashed color-mix(in srgb, var(--tg-theme-hint-color) 28%, transparent)',
                  cursor: slots[index] ? 'pointer' : 'default',
                }}
              >
                {slots[index] ?? <span style={{ fontSize: 18, color: 'var(--tg-theme-hint-color)' }}>?</span>}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-5 gap-2">
            {DIGITS.map((digit) => (
              <button
                key={digit}
                type="button"
                onClick={() => setSlots((current) => (current.length < codeLength ? [...current, digit] : current))}
                disabled={state.attempts_left === 0 || sending}
                className="py-3 rounded-[14px] text-[20px] font-black transition-transform duration-100 active:scale-90"
                style={{
                  border: '2px solid rgba(var(--c-gold-rgb),0.35)',
                  background: 'rgba(var(--c-gold-rgb),0.07)',
                  color: 'var(--tg-theme-text-color)',
                  opacity: state.attempts_left === 0 || sending ? 0.4 : 1,
                }}
              >
                {digit}
              </button>
            ))}
          </div>

          <button
            onClick={() => void submit()}
            disabled={!canGuess}
            className="py-[13px] rounded-[14px] border-none font-extrabold text-sm"
            style={{
              background: canGuess ? 'linear-gradient(135deg, var(--c-gold), #d08a00)' : 'color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)',
              color: canGuess ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)',
              boxShadow: canGuess ? '0 4px 16px rgba(var(--c-gold-rgb),0.35)' : 'none',
            }}
          >
            {sending
              ? 'Запечатываем...'
              : state.attempts_left === 0
                ? 'Попытки на сегодня кончились'
                : `Запечатать код · осталось ${state.attempts_left}`}
          </button>

          {state.pending_codes.length > 0 && (
            <div className="card flex flex-col gap-2">
              <p className="m-0 font-bold text-[13px]">Твои коды на сегодня</p>
              <p className="m-0 text-[12px] text-tg-hint">
                Подсказки к ним придут вместе со всеми после закрытия окна.
              </p>
              <div className="flex gap-2 flex-wrap">
                {state.pending_codes.map((code, index) => (
                  <span
                    key={`${code}-${index}`}
                    className="px-3 py-1.5 rounded-xl text-[15px] font-black tracking-[0.2em]"
                    style={{ background: 'rgba(var(--c-gold-rgb),0.12)', color: 'var(--c-gold)' }}
                  >
                    {code}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {error && (
        <div className="rounded-2xl p-4" style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.25)' }}>
          <p className="m-0 text-[13px] font-semibold" style={{ color: 'var(--c-red-soft)' }}>{error}</p>
        </div>
      )}

      <div className="flex gap-4 justify-center">
        <span className="text-xs flex items-center gap-1" style={{ color: 'var(--tg-theme-hint-color)' }}>
          <span className="w-2 h-2 rounded-full bg-[var(--c-green)] inline-block" />
          цифра на месте
        </span>
        <span className="text-xs flex items-center gap-1" style={{ color: 'var(--tg-theme-hint-color)' }}>
          <span className="w-2 h-2 rounded-full bg-[var(--c-blue)] inline-block" />
          есть, но не там
        </span>
      </div>

      {grouped.length === 0 ? (
        <div className="card text-center">
          <p className="m-0 text-[13px] text-tg-hint">
            Доска пуста — этот код ещё никто не пробовал. Первые подсказки появятся после
            закрытия окна.
          </p>
        </div>
      ) : (
        grouped.map(([day, entries]) => (
          <div key={day} className="card flex flex-col gap-2">
            <p className="m-0 font-bold text-[13px]">{dayLabel(day)}</p>
            {entries.map((entry, index) => (
              <div
                key={`${entry.code}-${index}`}
                className="flex items-center justify-between gap-3 rounded-xl px-3 py-2 surface-subtle"
              >
                <span className="text-[17px] font-black tracking-[0.18em] shrink-0">{entry.code}</span>
                <span className="text-[12px] text-tg-hint truncate">{entry.nickname}</span>
                <span className="flex gap-3 shrink-0 text-[13px] font-bold">
                  <span style={{ color: 'var(--c-green)' }}>{entry.exact}</span>
                  <span style={{ color: 'var(--c-blue)' }}>{entry.misplaced}</span>
                </span>
              </div>
            ))}
          </div>
        ))
      )}

    </div>
  );
}
