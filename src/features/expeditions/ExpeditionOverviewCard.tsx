import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiGetExpeditions } from '@/api';
import type { ExpeditionInfo } from '@/types';
import { formatCountdown } from '@/utils/format';

function expeditionStatusText(info: ExpeditionInfo | null, nowMs: number): string {
  if (!info) return 'Загружаем сводку...';
  const running = info.expeditions ?? [];
  const free = info.localities.filter(locality => !locality.busy).length;
  if (running.length === 0) return `${free} свободных направл. · отряд 3–5 животных`;

  const done = running.filter(e => e.status === 'finished').length;
  if (done > 0) return done === running.length ? `Результатов готово: ${done}` : `${done} готово · ${running.length - done} в пути`;
  if (nowMs === 0) return `В пути: ${running.length}`;

  // Several raids can be out at once, so count down to the one that lands first.
  const remaining = running.map(e => new Date(e.ends_at).getTime() - nowMs);
  const ready = remaining.filter(leftMs => leftMs <= 0).length;
  if (ready > 0) return `Можно завершить: ${ready}`;
  return `В пути: ${running.length} · ближайшая ${formatCountdown(Math.min(...remaining) / 1000)}`;
}

export function ExpeditionOverviewCard({ onOpen }: { onOpen: () => void }) {
  const [nowMs, setNowMs] = useState(0);
  const { data: info = null, error, refetch } = useQuery({
    queryKey: ['expeditions'],
    queryFn: apiGetExpeditions,
    staleTime: 30_000,
  });

  useEffect(() => {
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  // Memoised because the effect below depends on it: a fresh `[]` every render would
  // reschedule the refetch timer on every tick.
  const expeditions = useMemo(() => info?.expeditions ?? [], [info?.expeditions]);
  const anyFinished = expeditions.some(e => e.status === 'finished');
  const anyRunning = expeditions.some(e => e.status === 'active');

  useEffect(() => {
    const pending = expeditions
      .filter(e => e.status === 'active')
      .map(e => new Date(e.ends_at).getTime() - Date.now());
    if (pending.length === 0) return undefined;
    if (pending.some(leftMs => leftMs <= 0)) {
      void refetch();
      return undefined;
    }
    // Wake up for whichever raid lands first, not just the one that started first.
    const timeout = window.setTimeout(() => void refetch(), Math.min(...pending) + 250);
    return () => window.clearTimeout(timeout);
  }, [expeditions, refetch]);

  return (
    <button
      type="button"
      onClick={onOpen}
      className="card flex items-center gap-3 w-full border-none text-left cursor-pointer"
      style={{ border: '1px solid rgba(var(--c-gold-rgb),0.18)' }}
    >
      <div className="icon-box" style={{ background: 'rgba(var(--c-gold-rgb),0.12)' }}>🧭</div>
      <div className="flex-1 min-w-0">
        <p className="m-0 font-bold text-sm">Экспедиции</p>
        <p className="mt-[2px] mb-0 text-xs text-tg-hint">
          {error instanceof Error ? error.message : expeditionStatusText(info, nowMs)}
        </p>
      </div>
      {anyFinished && (
        <span className="text-[11px] font-bold px-2 py-[4px] rounded-full"
              style={{ background: 'rgba(var(--c-green-rgb),0.14)', color: 'var(--c-green)', border: '1px solid rgba(var(--c-green-rgb),0.25)' }}>
          Готово
        </span>
      )}
      {!anyFinished && anyRunning && (
        <span className="text-[11px] font-bold px-2 py-[4px] rounded-full"
              style={{ background: 'rgba(var(--c-blue-rgb),0.14)', color: 'var(--c-cyan)', border: '1px solid rgba(var(--c-cyan-rgb),0.28)' }}>
          В пути
        </span>
      )}
      <span className="text-base text-tg-hint">›</span>
    </button>
  );
}
