import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fmt } from '@/utils/format';
import type { GameState } from '@/types';
import { apiGetBank, apiExchange } from '@/api';
import { useZooStore } from '@/store';

/**
 * The bank buys dollars with rubles and never sells them back. Waiting for a cheap minute
 * is the whole game; there is no round trip to arbitrage.
 */
export function BankPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const patchState = useZooStore(s => s.patchState);
  const [amount, setAmount] = useState('');
  const [exchLoading, setExchLoading] = useState(false);
  const [exchResult, setExchResult] = useState<string | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data: bankInfo = null, error, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ['bank'],
    queryFn: apiGetBank,
    staleTime: 55_000,
    refetchInterval: 65_000,
  });

  // The rate update is global (aligned to a server-side period boundary), so the
  // countdown must be derived from a fixed absolute deadline, not from the relative
  // `next_update_in` snapshot. `dataUpdatedAt` is when the server value was actually
  // observed; anchoring to it keeps the timer stable across re-mounts and cache hits.
  const deadline =
    bankInfo?.next_update_in != null ? dataUpdatedAt + bankInfo.next_update_in * 1000 : null;

  useEffect(() => {
    if (deadline === null) {
      setCountdown(null);
      return;
    }
    const tick = () => {
      const remaining = Math.max(0, Math.round((deadline - Date.now()) / 1000));
      setCountdown(remaining);
      if (remaining <= 0) {
        void queryClient.invalidateQueries({ queryKey: ['bank'] });
      }
    };
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [deadline, queryClient]);

  const handleExchange = async (all: boolean) => {
    if (!all) {
      const n = parseInt(amount, 10);
      if (!n || n <= 0) return;
    }
    setExchLoading(true);
    setExchResult(null);
    try {
      const res = all ? await apiExchange(0, true) : await apiExchange(parseInt(amount, 10));
      setExchResult(`Куплено $${fmt(res.received_usd)} за ₽${fmt(res.spent_rub)}`);
      patchState({ rub: res.new_rub, usd: res.new_usd });
      setAmount('');
      // The fee just landed in the treasury, so the card above is stale.
      await queryClient.invalidateQueries({ queryKey: ['bank'] });
      void onRefresh();
    } catch (e) {
      setExchResult(e instanceof Error ? e.message : 'Ошибка');
    } finally {
      setExchLoading(false);
    }
  };

  const rate = bankInfo?.rate_rub_per_usd ?? 0;
  const baseRate = bankInfo?.base_rate_rub_per_usd ?? 0;
  const feePercent = bankInfo?.fee_percent ?? 0;
  const discounted = bankInfo != null && rate < baseRate;
  const minExchange = bankInfo?.min_exchange_rub ?? 0;

  // Mirrors `_bank_fee` on the server: a percentage of the dollars bought, at least one
  // once more than one is bought.
  const feeFor = (grossUsd: number) => {
    if (grossUsd <= 1) return 0;
    return Math.max(Math.floor((grossUsd * feePercent) / 100), 1);
  };

  const parsed = parseInt(amount, 10);
  const grossUsd = rate && parsed > 0 ? Math.floor(parsed / rate) : null;
  const fee = grossUsd != null ? feeFor(grossUsd) : null;
  const previewUsd = grossUsd != null && fee != null ? grossUsd - fee : null;

  // Meaningful, visibly-distinct presets below the full balance ("Всё" covers 100%).
  // Dedupe by the *displayed* value so two amounts never render as the same label.
  const seenLabels = new Set<string>();
  const quickAmounts = [minExchange, Math.floor(gs.rub * 0.25), Math.floor(gs.rub * 0.5)]
    .filter(v => v >= minExchange && v < gs.rub)
    .filter(v => { const k = fmt(v); if (seenLabels.has(k)) return false; seenLabels.add(k); return true; });

  const history = bankInfo?.history ?? [];
  const spark = (() => {
    if (history.length < 2) return null;
    const rates = history.map(p => p.rate);
    const min = Math.min(...rates);
    const max = Math.max(...rates);
    const span = max - min || 1;
    const points = rates
      .map((r, i) => `${(i / (rates.length - 1)) * 100},${28 - ((r - min) / span) * 26}`)
      .join(' ');
    return { points, min, max };
  })();

  return (
    <div className="px-[14px] pt-4 flex flex-col gap-3">
      <p className="m-0 text-[13px] text-tg-hint">
        Рубли приносят животные, доллары нужны в кузнице. Курс меняется каждую минуту — лови выгодный.
      </p>

      <div className="flex gap-2">
        <div className="flex-1 card text-center" style={{ borderColor: 'rgba(var(--c-green-rgb),0.3)' }}>
          <p className="m-0 text-[11px] text-tg-hint">Рубли</p>
          <p className="mt-1 mb-0 text-lg font-extrabold text-[var(--c-green)]">₽ {fmt(gs.rub)}</p>
        </div>
        <div className="flex-1 card text-center" style={{ borderColor: 'rgba(var(--c-blue-rgb),0.3)' }}>
          <p className="m-0 text-[11px] text-tg-hint">Доллары</p>
          <p className="mt-1 mb-0 text-lg font-extrabold text-[var(--c-blue)]">$ {fmt(gs.usd)}</p>
        </div>
        <div className="flex-1 card text-center" style={{ borderColor: 'rgba(var(--c-orange-rgb),0.3)' }}>
          <p className="m-0 text-[11px] text-tg-hint">Обновление через</p>
          <p className="mt-1 mb-0 text-lg font-extrabold text-[var(--c-orange)]">
            {countdown != null ? `${countdown}с` : '—'}
          </p>
        </div>
      </div>

      {bankInfo && (
        <div className="card">
          <p className="m-0 mb-2 text-[13px] text-tg-hint">Твой курс</p>
          <p className="m-0 mb-1 text-[28px] font-extrabold text-[var(--c-blue)]">1$ = ₽ {fmt(rate)}</p>
          {discounted && (
            <p className="m-0 mb-3 text-[12px] text-tg-hint">
              Без предметов: ₽ {fmt(baseRate)} · экономия {Math.round((1 - rate / baseRate) * 100)}%
            </p>
          )}

          {spark && (
            <svg viewBox="0 0 100 30" preserveAspectRatio="none" className="w-full h-[36px] my-2" aria-label="Курс за последний час">
              <polyline points={spark.points} fill="none" stroke="var(--c-blue)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
            </svg>
          )}

          <div className="flex gap-2">
            <div className="flex-1 py-2 px-3 rounded-lg bg-[rgba(var(--c-blue-rgb),0.1)]">
              <p className="m-0 text-[10px] text-tg-hint">Хранилище банка</p>
              <p className="mt-1 mb-0 text-[15px] font-bold text-[var(--c-blue)]">$ {fmt(bankInfo.treasury_usd)}</p>
            </div>
            <div className="flex-1 py-2 px-3 rounded-lg bg-[rgba(var(--c-orange-rgb),0.1)]">
              <p className="m-0 text-[10px] text-tg-hint">Комиссия банка</p>
              <p className="mt-1 mb-0 text-[15px] font-bold text-[var(--c-orange)]">{feePercent}%</p>
            </div>
          </div>

          {bankInfo.referral_percent > 0 && (
            <p className="m-0 mt-2 text-[12px] text-tg-hint">
              Пригласивший тебя получает {bankInfo.referral_percent}% от каждого купленного доллара.
            </p>
          )}
        </div>
      )}

      {isLoading && <p className="text-center text-tg-hint">Загрузка курса...</p>}
      {error && <p className="text-[var(--c-red-soft)]">⚠️ {error instanceof Error ? error.message : 'Ошибка загрузки'}</p>}

      {bankInfo && (
        <div className="flex flex-col gap-3">
          <div>
            <p className="m-0 mb-1 text-[15px] font-bold">Купить доллары</p>
            <p className="m-0 text-[12px] text-tg-hint">Минимальная сумма: ₽ {fmt(minExchange)}</p>
          </div>

          <div className="flex gap-2 flex-wrap">
            {quickAmounts.map(v => (
              <button
                key={v}
                onClick={() => setAmount(String(v))}
                className="px-3 py-2 rounded-lg border bg-transparent text-tg-text text-[13px] font-medium cursor-pointer"
                style={{ borderColor: 'var(--surface-overlay-border)' }}
              >
                ₽ {fmt(v)}
              </button>
            ))}
            {gs.rub > 0 && (
              <button
                onClick={() => setAmount(String(gs.rub))}
                className="px-3 py-2 rounded-lg border-none bg-[rgba(var(--c-green-rgb),0.15)] text-[var(--c-green)] text-[13px] font-bold cursor-pointer"
              >
                Всё
              </button>
            )}
          </div>

          <input
            type="number"
            value={amount}
            onChange={e => setAmount(e.target.value)}
            placeholder="Сумма в рублях"
            className="text-input text-sm"
          />

          {previewUsd != null && fee != null && (
            <p className="m-0 text-[13px] text-tg-hint">
              Получишь: $ {fmt(previewUsd)}
              {fee > 0 && <span className="text-[var(--c-orange)]"> · комиссия $ {fmt(fee)}</span>}
            </p>
          )}

          {exchResult && (
            <p className={`m-0 text-[13px] ${exchResult.startsWith('Куплено') ? 'text-[var(--c-green)]' : 'text-[var(--c-red-soft)]'}`}>
              {exchResult}
            </p>
          )}

          <div className="flex gap-2">
            <button
              onClick={() => void handleExchange(true)}
              disabled={exchLoading || gs.rub < minExchange}
              className="flex-1 py-3 rounded-[10px] border-none cursor-pointer bg-[var(--c-green)] text-[var(--tg-theme-button-text-color)] font-bold text-sm disabled:opacity-60"
            >
              {exchLoading ? 'Обмен...' : 'Обменять всё'}
            </button>
            <button
              onClick={() => void handleExchange(false)}
              disabled={exchLoading || !amount || parsed < minExchange}
              className="flex-1 py-3 rounded-[10px] border bg-transparent text-tg-hint font-bold text-sm disabled:opacity-40 cursor-pointer"
              style={{ borderColor: 'var(--surface-overlay-border)' }}
            >
              Обменять
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
