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
  animal: { icon: '🐾', name: 'Животное', color: 'var(--c-purple)' },
  locality: { icon: '🗺️', name: 'Местность', color: 'var(--c-teal)' },
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
        const rewardIcon = res.reward_emoji ?? meta.icon;
        const rewardLabel = res.reward_name ?? meta.name;
        setClaimed(res.reward_name ? `Получено ${rewardIcon} ${rewardLabel}` : `Получено ${fmt(res.amount)} ${rewardIcon}`);
        setBurst({ glyph: rewardIcon, amount: res.amount, color: meta.color, label: rewardLabel });
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
  const offerIsObject = Boolean(offer?.reward_name);
  const canClaim = offer != null && !offer.claimed;
  const canReroll = canClaim && offer.rerolls_left > 0;

  return (
    <div className="p-[14px] flex flex-col gap-3">
      <div className="bonus-ticket">
        <div className="bonus-ticket-mark">🎁</div>
        <div className="min-w-0">
          <p className="bonus-kicker">Ежедневный ритуал · UTC</p>
          <p className="m-0 mt-1 text-[22px] leading-none font-black">Подарок ждёт</p>
          <p className="m-0 mt-2 text-[12px] leading-[1.4] text-tg-hint">
            Один бонус после полуночи. Забери его до следующего обновления.
          </p>
        </div>
      </div>

      {isLoading && <p className="text-center text-tg-hint">Загрузка...</p>}

      {offer && meta && (
        <div className="bonus-offer-card" style={{ borderColor: `color-mix(in srgb, ${meta.color} 38%, transparent)` }}>
          <div className="flex items-center justify-between gap-2">
            <p className="bonus-offer-kicker">Твоя награда сегодня</p>
            <span className="bonus-offer-status">{offer.claimed ? 'Получено' : 'Готово'}</span>
          </div>
          <div className="bonus-offer-reward">
            <span className="bonus-offer-icon" style={{ color: meta.color }}>{meta.icon}</span>
            <div>
              <strong style={{ color: meta.color }}>{offerIsObject ? offer.reward_emoji : fmt(offer.amount)}</strong>
              <span>{offerIsObject ? offer.reward_name : meta.name}</span>
            </div>
          </div>
          <p className="m-0 mt-2 text-[12px] text-tg-hint">Забери сейчас или попробуй другой вариант.</p>

          <button
            onClick={() => void run('claim')}
            disabled={!canClaim || busy}
            className="bonus-claim-button"
            style={{
              background: canClaim ? meta.color : 'var(--surface-subtle)',
              color: canClaim ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)',
            }}
          >
            {busy ? 'Получаем...' : canClaim ? `Забрать ${meta.icon}` : '⏳ Уже получен сегодня'}
          </button>

          <button
            onClick={() => void run('reroll')}
            disabled={!canReroll || busy}
            className="bonus-reroll-button"
          >
            {offer.rerolls_left > 0
              ? `🎲 Перебросить · осталось ${offer.rerolls_left}`
              : 'Перебросов нет — их дают предметы кузницы'}
          </button>
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

      <RewardBurst reward={burst} onDone={() => setBurst(null)} />

      <div className="card bonus-pool-card">
        <p className="m-0 text-[11px] font-bold text-tg-hint tracking-[0.8px] uppercase">В пуле наград</p>
        <div className="bonus-pool-grid">
          {(Object.keys(CURRENCY) as BonusCurrency[]).map(key => (
            <div key={key} className="bonus-pool-item">
              <span style={{ color: CURRENCY[key].color }}>{CURRENCY[key].icon}</span>
              <span>{CURRENCY[key].name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
