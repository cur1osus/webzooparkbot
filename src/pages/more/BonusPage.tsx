import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { fmt } from '@/utils/format';
import type { BonusCurrency } from '@/types';
import { apiClaimBonus, apiGetBonus, apiRerollBonus } from '@/api';
import { RewardBurst, type Reward } from '@/components/RewardBurst';

const CURRENCY: Record<BonusCurrency, { icon: string; name: string; color: string }> = {
  rub: { icon: '₽', name: 'Рубли', color: 'var(--c-green)' },
  usd: { icon: '$', name: 'Доллары', color: 'var(--c-blue)' },
  paw: { icon: '🐾', name: 'PawCoins', color: 'var(--c-orange)' },
};

/**
 * The offer is generated and stored server-side, once per UTC day. A reroll replaces it
 * and spends one of the rerolls the player's `bonus_rerolls` items grant — so neither the
 * offer nor the number of rerolls can be forged from here.
 */
export function BonusPage({ onClaim }: { onClaim: () => void }) {
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [claimed, setClaimed] = useState<string | null>(null);
  const [burst, setBurst] = useState<Reward | null>(null);

  const { data: offer = null, isLoading } = useQuery({ queryKey: ['bonus'], queryFn: apiGetBonus });

  const run = async (action: 'reroll' | 'claim') => {
    setBusy(true);
    setError(null);
    try {
      if (action === 'reroll') {
        const next = await apiRerollBonus();
        queryClient.setQueryData(['bonus'], next);
      } else {
        const res = await apiClaimBonus();
        const meta = CURRENCY[res.currency];
        setClaimed(`Получено ${fmt(res.amount)} ${meta.icon}`);
        setBurst({ glyph: meta.icon, amount: res.amount, color: meta.color, label: meta.name });
        await queryClient.invalidateQueries({ queryKey: ['bonus'] });
        onClaim();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка');
    } finally {
      setBusy(false);
    }
  };

  const meta = offer ? CURRENCY[offer.currency] : null;
  const canClaim = offer != null && !offer.claimed;
  const canReroll = canClaim && offer.rerolls_left > 0;

  return (
    <div className="p-[14px] flex flex-col gap-3">
      <div className="card text-center">
        <span className="text-[48px]">🎁</span>
        <p className="mt-[10px] mb-1 text-lg font-extrabold">Ежедневный бонус</p>
        <p className="m-0 text-[13px] text-tg-hint">Новый бонус каждый день после полуночи UTC.</p>
      </div>

      {isLoading && <p className="text-center text-tg-hint">Загрузка...</p>}

      {offer && meta && (
        <div className="card text-center" style={{ borderColor: `color-mix(in srgb, ${meta.color} 35%, transparent)` }}>
          <p className="m-0 text-[12px] text-tg-hint">Сегодня выпало</p>
          <p className="mt-2 mb-0 text-[32px] font-extrabold" style={{ color: meta.color }}>
            {meta.icon} {fmt(offer.amount)}
          </p>
          <p className="mt-1 mb-0 text-[13px] text-tg-hint">{meta.name}</p>
        </div>
      )}

      {claimed && (
        <div className="card bg-[rgba(var(--c-green-rgb),0.1)] border border-[rgba(var(--c-green-rgb),0.3)]">
          <p className="m-0 font-bold text-[var(--c-green)]">🎉 {claimed}</p>
        </div>
      )}

      {error && (
        <div className="card bg-[rgba(var(--c-red-rgb),0.1)] border border-[rgba(var(--c-red-rgb),0.3)]">
          <p className="m-0 text-[var(--c-red-soft)]">⚠️ {error}</p>
        </div>
      )}

      <button
        onClick={() => void run('claim')}
        disabled={!canClaim || busy}
        className="py-[14px] rounded-xl border-none cursor-pointer font-extrabold text-base disabled:opacity-60 disabled:cursor-not-allowed"
        style={{
          background: canClaim ? 'var(--c-green)' : 'var(--surface-subtle)',
          color: canClaim ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)',
        }}
      >
        {busy ? 'Получаем...' : canClaim ? '🎁 Забрать' : '⏳ Уже получен сегодня'}
      </button>

      {offer && (
        <button
          onClick={() => void run('reroll')}
          disabled={!canReroll || busy}
          className="py-3 rounded-xl border bg-transparent text-tg-text font-bold text-sm disabled:opacity-40 cursor-pointer"
          style={{ borderColor: 'var(--surface-overlay-border)' }}
        >
          {offer.rerolls_left > 0
            ? `🎲 Перебросить (осталось ${offer.rerolls_left})`
            : 'Перебросов нет — их дают предметы кузницы'}
        </button>
      )}

      <RewardBurst reward={burst} onDone={() => setBurst(null)} />

      <div className="card">
        <p className="m-0 mb-2 font-bold">Возможные награды:</p>
        {(Object.keys(CURRENCY) as BonusCurrency[]).map(key => (
          <div key={key} className="flex gap-[10px] mb-[6px]">
            <span className="text-lg shrink-0" style={{ color: CURRENCY[key].color }}>{CURRENCY[key].icon}</span>
            <span className="text-[13px] text-tg-hint">{CURRENCY[key].name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
