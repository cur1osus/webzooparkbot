import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
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

const GIFT_ART = '/rewards/daily-gift-chest.png';

/**
 * The offer is generated and stored server-side, once per Moscow day starting at 07:00. A reroll replaces it
 * and spends one of the rerolls the player's `bonus_rerolls` items grant — so neither the
 * offer nor the number of rerolls can be forged from here.
 */
export function BonusPage({ onClaim }: { onClaim: () => void }) {
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [burst, setBurst] = useState<Reward | null>(null);
  const [giftRevealed, setGiftRevealed] = useState(false);
  const [openingGift, setOpeningGift] = useState(false);

  const { data: offer = null, isLoading } = useQuery({ queryKey: ['bonus'], queryFn: apiGetBonus });

  useEffect(() => {
    setGiftRevealed(Boolean(offer?.claimed));
    setOpeningGift(false);
  }, [offer]);

  const revealGift = () => {
    if (!offer || offer.claimed || giftRevealed || openingGift) return;
    setGiftRevealed(true);
    setOpeningGift(true);
    window.setTimeout(() => setOpeningGift(false), 720);
  };

  const run = async (action: 'reroll' | 'claim') => {
    setBusy(true);
    setError(null);
    try {
      if (action === 'reroll') {
        const next = await apiRerollBonus();
        queryClient.setQueryData(['bonus'], next);
        setGiftRevealed(false);
        setOpeningGift(false);
      } else {
        setGiftRevealed(true);
        const res = await apiClaimBonus();
        const meta = CURRENCY[res.currency];
        const rewardIcon = res.reward_emoji ?? meta.icon;
        const rewardLabel = res.reward_name ?? meta.name;
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
    <div className="bonus-page p-[14px] flex flex-col gap-3">
      <header className="bonus-page-intro" aria-labelledby="bonus-page-title">
        <div>
          <p className="bonus-kicker">Ежедневный бонус</p>
          <h1 id="bonus-page-title" className="bonus-page-title">Сюрприз на сегодня</h1>
        </div>
        <div className="bonus-schedule" aria-label="Обновление каждый день в 07:00 по Москве">
          <strong>07:00</strong>
          <span>по Москве</span>
        </div>
      </header>

      {isLoading && <p className="text-center text-tg-hint">Загрузка...</p>}

      {offer && meta && (
        <div
          className="bonus-offer-card"
          style={{ borderColor: giftRevealed ? `color-mix(in srgb, ${meta.color} 38%, transparent)` : 'rgba(var(--c-gold-rgb),0.38)' }}
        >
          <div className={`bonus-gift-stage${giftRevealed ? ' is-revealed' : ''}${openingGift ? ' is-opening' : ''}`}>
            <div className="bonus-gift-halo" aria-hidden />
            <img className="bonus-gift-art" src={GIFT_ART} alt="" />
            {!giftRevealed && <span className="bonus-gift-lock">✦ сюрприз внутри</span>}
          </div>

          {!giftRevealed || openingGift ? (
            <div className="bonus-gift-locked-copy">
              <p className="bonus-gift-title">Открой сундук</p>
              <button onClick={revealGift} disabled={busy || openingGift} className="bonus-open-button" type="button">
                {openingGift ? 'Открываем...' : 'Открыть подарок'}
              </button>
              {canReroll && (
                <button onClick={() => void run('reroll')} disabled={busy} className="bonus-reroll-button" type="button">
                  🎲 Перебросить · осталось {offer.rerolls_left}
                </button>
              )}
            </div>
          ) : (
            <div className="bonus-reveal-content">
              <div className="bonus-offer-reward">
                <span className="bonus-offer-icon" style={{ color: meta.color }}>{meta.icon}</span>
                <div className="bonus-reward-copy">
                  <strong style={{ color: meta.color }}>
                    {offerIsObject ? offer.reward_emoji : `+${fmt(offer.amount)}`}
                  </strong>
                  {offerIsObject && <span>{offer.reward_name}</span>}
                </div>
              </div>

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

              {canReroll && (
                <button onClick={() => void run('reroll')} disabled={busy} className="bonus-reroll-button" type="button">
                  🎲 Перебросить · осталось {offer.rerolls_left}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="card bg-[rgba(var(--c-red-rgb),0.1)] border border-[rgba(var(--c-red-rgb),0.3)]">
          <p className="m-0 text-[var(--c-red-soft)]">⚠️ {error}</p>
        </div>
      )}

      <RewardBurst reward={burst} onDone={() => setBurst(null)} />
    </div>
  );
}
