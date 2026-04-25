import { useQuery } from '@tanstack/react-query';
import type { GameState, TopEntry } from '@/types';
import { apiGetTop } from '@/api';
import { fmt } from '@/utils/format';

export function TopPage({ gs }: { gs: GameState }) {
  const { data, error, isLoading } = useQuery({
    queryKey: ['top'],
    queryFn: apiGetTop,
    staleTime: 30_000,
  });

  const rankEmoji = (r: number) => r === 1 ? '🥇' : r === 2 ? '🥈' : r === 3 ? '🥉' : `${r}.`;

  return (
    <div className="p-[14px] flex flex-col gap-2">
      {isLoading && <p className="text-center text-tg-hint">Загрузка...</p>}
      {error && <p className="text-[var(--c-red-soft)]">⚠️ {error instanceof Error ? error.message : 'Ошибка'}</p>}
      {!isLoading && !error && <p className="m-0 text-center text-xs text-tg-hint">Игрок: {gs.nickname}</p>}

      {data?.my_rank && !data.entries.some(e => e.is_me) && (
        <div className="card border border-[rgba(var(--c-blue-rgb),0.3)] bg-[rgba(var(--c-blue-rgb),0.07)]">
          <p className="m-0 text-[13px]">
            Твоё место: <strong>#{data.my_rank}</strong>
          </p>
        </div>
      )}

      {data?.entries.map((entry: TopEntry) => (
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
