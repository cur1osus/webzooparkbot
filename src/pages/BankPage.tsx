import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fmt } from '@/utils/format';
import type { GameState } from '@/types';
import { apiGetBank, apiExchange } from '@/api';
import { useZooStore } from '@/store';

export function BankPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const patchState = useZooStore(s => s.patchState);
  const [amount, setAmount] = useState('');
  const [exchLoading, setExchLoading] = useState(false);
  const [exchResult, setExchResult] = useState<string | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data: bankInfo = null, error, isLoading } = useQuery({
    queryKey: ['bank'],
    queryFn: apiGetBank,
    staleTime: 55_000,
    refetchInterval: 65_000,
  });

  // Reset countdown when new bank data arrives
  useEffect(() => {
    if (bankInfo?.next_update_in != null) {
      setCountdown(bankInfo.next_update_in);
    }
  }, [bankInfo?.next_update_in]);

  // Tick countdown every second
  useEffect(() => {
    if (countdown === null) return;
    if (countdown <= 0) {
      void queryClient.invalidateQueries({ queryKey: ['bank'] });
      return;
    }
    const timer = setTimeout(() => setCountdown(c => (c ?? 1) - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown, queryClient]);

  const handleExchange = async (all: boolean) => {
    if (!all) {
      const n = parseFloat(amount);
      if (!n || n <= 0) return;
    }
    setExchLoading(true);
    setExchResult(null);
    try {
      const res = all
        ? await apiExchange('rub', 0, true)
        : await apiExchange('rub', parseFloat(amount));
      if (res.ok) {
        setExchResult('Обмен выполнен!');
        patchState({ rub: res.new_rub, usd: res.new_usd });
        void onRefresh();
      } else {
        setExchResult(res.message ?? 'Ошибка');
      }
    } catch (e) {
      setExchResult(e instanceof Error ? e.message : 'Ошибка');
    } finally {
      setExchLoading(false);
    }
  };

  const rate = bankInfo?.rub_rate ?? 0;
  const minExchange = bankInfo?.min_exchange_rub ?? 0;

  const calcCommission = (gain: number) => {
    if (gain <= 1) return 0;
    const c = Math.floor(gain * 0.01);
    return c > 0 ? c : 1;
  };

  const grossUsd = rate && amount ? Math.floor(parseFloat(amount) / rate) : null;
  const commission = grossUsd != null ? calcCommission(grossUsd) : null;
  const previewAmount = grossUsd != null && commission != null ? grossUsd - commission : null;

  const quickAmounts = [
    minExchange,
    Math.min(1000, gs.rub),
    Math.min(1000000, gs.rub),
  ].filter((v, i, a) => a.indexOf(v) === i && v > 0 && v <= gs.rub);

  return (
    <div className="px-[14px] pt-4 flex flex-col gap-3">
      <p className="m-0 text-[13px] text-tg-hint">Обмен рублей на доллары по текущему курсу</p>

      {/* Balance tiles */}
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

      {/* Rate card */}
      {bankInfo && (
        <div className="card">
          <p className="m-0 mb-2 text-[13px] text-tg-hint">Твой курс</p>
          <p className="m-0 mb-3 text-[28px] font-extrabold text-[var(--c-blue)]">1$ = ₽ {fmt(rate)}</p>
          
          <div className="flex gap-2">
            <div className="flex-1 py-2 px-3 rounded-lg bg-[rgba(var(--c-blue-rgb),0.1)]">
              <p className="m-0 text-[10px] text-tg-hint">Хранилище банка</p>
              <p className="mt-1 mb-0 text-[15px] font-bold text-[var(--c-blue)]">$ {fmt(bankInfo.vault_usd)}</p>
            </div>
            <div className="flex-1 py-2 px-3 rounded-lg bg-[rgba(var(--c-orange-rgb),0.1)]">
              <p className="m-0 text-[10px] text-tg-hint">Комиссия банка</p>
              <p className="mt-1 mb-0 text-[15px] font-bold text-[var(--c-orange)]">1% (мин. $1)</p>
            </div>
          </div>
        </div>
      )}

      {/* Exchange section */}
      {isLoading && <p className="text-center text-tg-hint">Загрузка курса...</p>}
      {error && <p className="text-[var(--c-red-soft)]">⚠️ {error instanceof Error ? error.message : 'Ошибка загрузки'}</p>}

      {bankInfo && (
        <div className="flex flex-col gap-3">
          <div>
            <p className="m-0 mb-1 text-[15px] font-bold">Обменять рубли</p>
            <p className="m-0 text-[12px] text-tg-hint">Минимальная сумма для обмена: ₽ {fmt(minExchange)}</p>
          </div>

          {/* Quick buttons */}
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

          {/* Input */}
          <input
            type="number"
            value={amount}
            onChange={e => setAmount(e.target.value)}
            placeholder="Сумма в рублях"
            className="text-input text-sm"
          />

          {previewAmount != null && grossUsd != null && commission != null && (
            <p className="m-0 text-[13px] text-tg-hint">
              Получите: $ {fmt(previewAmount)}
              {commission > 0 && <span className="text-[var(--c-orange)]"> · комиссия $ {fmt(commission)}</span>}
            </p>
          )}

          {exchResult && (
            <p className={`m-0 text-[13px] ${exchResult === 'Обмен выполнен!' ? 'text-[var(--c-green)]' : 'text-[var(--c-red-soft)]'}`}>
              {exchResult}
            </p>
          )}

          {/* Buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => void handleExchange(true)}
              disabled={exchLoading || gs.rub <= 0}
              className="flex-1 py-3 rounded-[10px] border-none cursor-pointer bg-[var(--c-green)] text-[var(--tg-theme-button-text-color)] font-bold text-sm disabled:opacity-60"
            >
              {exchLoading ? 'Обмен...' : 'Обменять всё'}
            </button>
            <button
              onClick={() => void handleExchange(false)}
              disabled={exchLoading || !amount || parseFloat(amount) < minExchange}
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
