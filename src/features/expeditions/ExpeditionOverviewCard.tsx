import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiGetExpeditions } from '@/api';
import type { ExpeditionInfo } from '@/types';
import { formatCountdown } from '@/utils/format';

function expeditionStatusText(info: ExpeditionInfo | null, nowMs: number): string {
  const active = info?.active;
  if (!info) return 'Загружаем сводку...';
  if (!active) return `${info.localities.length} направл. · отряд 3–5 животных`;
  if (active.status === 'finished') return 'Результат готов';
  if (nowMs === 0) return 'В пути';
  const leftMs = new Date(active.ends_at).getTime() - nowMs;
  return leftMs > 0 ? `В пути · ${formatCountdown(leftMs / 1000)}` : 'Можно завершить';
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

  const active = info?.active;

  useEffect(() => {
    if (!active || active.status !== 'active') return undefined;
    const leftMs = new Date(active.ends_at).getTime() - Date.now();
    if (leftMs <= 0) {
      void refetch();
      return undefined;
    }
    const timeout = window.setTimeout(() => void refetch(), leftMs + 250);
    return () => window.clearTimeout(timeout);
  }, [active, refetch]);

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
      {active?.status === 'finished' && (
        <span className="text-[11px] font-bold px-2 py-[4px] rounded-full"
              style={{ background: 'rgba(var(--c-green-rgb),0.14)', color: 'var(--c-green)', border: '1px solid rgba(var(--c-green-rgb),0.25)' }}>
          Готово
        </span>
      )}
      {active?.status === 'active' && (
        <span className="text-[11px] font-bold px-2 py-[4px] rounded-full"
              style={{ background: 'rgba(var(--c-blue-rgb),0.14)', color: 'var(--c-cyan)', border: '1px solid rgba(90,200,250,0.25)' }}>
          В пути
        </span>
      )}
      <span className="text-base text-tg-hint">›</span>
    </button>
  );
}
