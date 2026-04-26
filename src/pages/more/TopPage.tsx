import { useQuery } from '@tanstack/react-query';
import type { GameState, TopEntry } from '@/types';
import { apiGetTop } from '@/api';
import { fmt } from '@/utils/format';

const CHART_H = 96; // px — max bar height

function IncomeChart({ entries }: { entries: TopEntry[] }) {
  const top7 = entries.slice(0, 7);
  const maxIncome = Math.max(...top7.map(e => e.income_rub_per_min), 1);

  const rankLabel = (r: number) =>
    r === 1 ? '🥇' : r === 2 ? '🥈' : r === 3 ? '🥉' : `#${r}`;

  return (
    <div className="card" style={{ padding: '12px 10px 10px' }}>
      <p className="m-0 mb-3 text-xs text-tg-hint text-center font-medium tracking-wide uppercase">
        Топ по доходу
      </p>

      <div className="flex items-end gap-[3px]" style={{ height: CHART_H }}>
        {top7.map(entry => {
          const pct = entry.income_rub_per_min / maxIncome;
          const barH = Math.max(Math.round(pct * CHART_H), 6);
          const isMe = entry.is_me;
          const isTop3 = entry.rank <= 3;
          const bg = isMe
            ? 'rgba(var(--c-blue-rgb),0.85)'
            : isTop3
            ? 'var(--c-green)'
            : 'rgba(var(--c-green-rgb),0.45)';

          return (
            <div
              key={entry.tg_id}
              className="flex flex-col items-center flex-1 min-w-0 justify-end"
              style={{ height: '100%' }}
            >
              <span
                className="font-bold leading-none mb-[3px]"
                style={{ fontSize: 7, color: 'var(--c-green)' }}
              >
                {fmt(entry.income_rub_per_min)}
              </span>
              <div
                className="w-full rounded-t-sm"
                style={{ height: barH, background: bg, minHeight: 6 }}
              />
            </div>
          );
        })}
      </div>

      {/* X-axis labels */}
      <div className="flex gap-[3px] mt-1">
        {top7.map(entry => (
          <div
            key={entry.tg_id}
            className="flex flex-col items-center flex-1 min-w-0"
          >
            <span
              className="leading-none"
              style={{ fontSize: 8, color: entry.is_me ? 'var(--c-blue)' : 'var(--tg-theme-hint-color)' }}
            >
              {rankLabel(entry.rank)}
            </span>
            <span
              className="truncate w-full text-center leading-none mt-[2px]"
              style={{
                fontSize: 7,
                color: entry.is_me ? 'var(--c-blue)' : 'var(--tg-theme-hint-color)',
                fontWeight: entry.is_me ? 700 : 400,
              }}
            >
              {entry.nickname.slice(0, 6)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function TopPage({ gs }: { gs: GameState }) {
  const { data, error, isLoading } = useQuery({
    queryKey: ['top'],
    queryFn: apiGetTop,
    staleTime: 30_000,
  });

  const rankEmoji = (r: number) => r === 1 ? '🥇' : r === 2 ? '🥈' : r === 3 ? '🥉' : `${r}.`;

  const list = data?.entries.slice(0, 20) ?? [];

  return (
    <div className="p-[14px] flex flex-col gap-2">
      {isLoading && <p className="text-center text-tg-hint">Загрузка...</p>}
      {error && <p className="text-[var(--c-red-soft)]">⚠️ {error instanceof Error ? error.message : 'Ошибка'}</p>}

      {data && data.entries.length > 0 && <IncomeChart entries={data.entries} />}

      {data?.my_rank && !list.some(e => e.is_me) && (
        <div className="card border border-[rgba(var(--c-blue-rgb),0.3)] bg-[rgba(var(--c-blue-rgb),0.07)]">
          <p className="m-0 text-[13px]">
            Твоё место: <strong>#{data.my_rank}</strong>
          </p>
        </div>
      )}

      {list.map((entry: TopEntry) => (
        <div
          key={entry.tg_id}
          className="card flex items-center gap-3"
          style={{
            border: entry.is_me ? '1px solid rgba(var(--c-blue-rgb),0.4)' : '1px solid var(--surface-overlay-border)',
            background: entry.is_me ? 'rgba(var(--c-blue-rgb),0.07)' : 'var(--tg-theme-secondary-bg-color)',
            padding: '10px 14px',
          }}
        >
          <span className="text-lg shrink-0 min-w-7 text-center">{rankEmoji(entry.rank)}</span>
          <div className="flex-1">
            <p
              className="m-0"
              style={{
                fontWeight: entry.is_me ? 800 : 600,
                color: entry.name_color ?? (entry.is_me ? 'var(--c-blue)' : 'var(--tg-theme-text-color)'),
              }}
            >
              {entry.nickname}
            </p>
          </div>
          <span className="text-[13px] text-[var(--c-green)] font-bold">+{fmt(entry.income_rub_per_min)}/мин</span>
        </div>
      ))}

      {!isLoading && !error && data?.entries.length === 0 && (
        <div className="card text-center">
          <p className="m-0 text-tg-hint">Топ пуст. Будь первым!</p>
        </div>
      )}
    </div>
  );
}
