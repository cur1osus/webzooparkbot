import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { GameState, MerchantOffer } from '@/types';
import { apiGetMerchant, apiBuyFromMerchant } from '@/api';
import { fmt } from '@/utils/format';
import { geneLabel, HABITAT_INFO } from '@/data/packs';
import { AnimalArt } from '@/components/AnimalArt';

export function MerchantPage({ gs, onBuy }: { gs: GameState; onBuy: () => void }) {
  const [buying, setBuying] = useState<number | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ['merchant'],
    queryFn: apiGetMerchant,
    staleTime: 30_000,
  });

  const handleBuy = async (slot: number) => {
    setBuying(slot);
    setMsg(null);
    try {
      const res = await apiBuyFromMerchant(slot);
      setMsg(`Куплено за ₽${fmt(res.price_paid)}`);
      onBuy();
      void refetch();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Ошибка покупки');
    } finally {
      setBuying(null);
    }
  };

  return (
    <div className="p-[14px] flex flex-col gap-3">
      <div className="merchant-hero">
        <div className="merchant-hero-icon">🧙</div>
        <div className="min-w-0">
          <p className="merchant-kicker">Лавка странника</p>
          <p className="m-0 mt-1 text-[21px] leading-none font-black">Случайный торговец</p>
          <p className="m-0 mt-2 text-[12px] leading-[1.4]" style={{ color: 'rgba(255,248,236,0.68)' }}>
            Редкие животные со скидкой. Успей забрать выгодное предложение.
          </p>
        </div>
      </div>
      {isLoading && <p className="text-center text-tg-hint">Загрузка...</p>}

      {error && (
        <div className="card bg-[rgba(var(--c-red-rgb),0.1)] border border-[rgba(var(--c-red-rgb),0.3)]">
          <p className="m-0 text-[var(--c-red-soft)]">⚠️ {error instanceof Error ? error.message : 'Ошибка загрузки'}</p>
          <p className="mt-1 mb-0 text-xs text-tg-hint">
            Торговец появляется только если у тебя есть животные в зоопарке
          </p>
        </div>
      )}

      {msg && (
        <div className="card bg-[rgba(var(--c-green-rgb),0.1)] border border-[rgba(var(--c-green-rgb),0.3)]">
          <p className="m-0 text-[var(--c-green)]">{msg}</p>
        </div>
      )}

      {data && (
        <>
          <div className="merchant-refresh-bar">
            <span>🕰 Следующая ротация</span>
            <strong>{new Date(data.refreshes_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })}</strong>
          </div>

          {data.animals.map((offer: MerchantOffer) => {
            const habitat = HABITAT_INFO[offer.habitat];
            const affordable = gs.rub >= offer.final_price && !offer.bought;
            return (
              <div key={offer.slot} className={`card merchant-offer-card${offer.bought ? ' merchant-offer-sold' : ''}`}>
                <div className="merchant-offer-top">
                  <div className="merchant-animal-stage">
                    <AnimalArt animal={offer} size={68} className="shrink-0" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="m-0 text-[16px] font-extrabold">{offer.species_name}</p>
                    <p className="mt-[4px] mb-0 text-xs text-tg-hint">
                      {habitat.emoji} {habitat.name}
                    </p>
                    <span className="merchant-gene-chip">Размножение: {geneLabel('reproduction', offer.reproduction)}</span>
                  </div>
                  {(offer.bought || offer.discount_pct > 0) && (
                    <div className="merchant-discount-badge"
                         style={{ background: offer.bought ? 'var(--surface-subtle)' : 'rgba(var(--c-green-rgb),0.15)', color: offer.bought ? 'var(--tg-theme-hint-color)' : 'var(--c-green)' }}>
                      {offer.bought ? '✓' : `−${offer.discount_pct}%`}
                    </div>
                  )}
                </div>

                <div className="merchant-price-row">
                  <div>
                    {offer.discount_pct > 0 && (
                      <span className="block text-xs text-tg-hint line-through">₽ {fmt(offer.list_price)}</span>
                    )}
                    <span className="text-[18px] font-black">₽ {fmt(offer.final_price)}</span>
                  </div>
                  <button
                    onClick={() => void handleBuy(offer.slot)}
                    disabled={buying === offer.slot || !affordable || offer.bought}
                    className="merchant-buy-button"
                    style={{
                      background: affordable ? 'var(--c-green)' : 'var(--surface-subtle)',
                      color: affordable ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)',
                    }}
                  >
                    {offer.bought ? 'Куплено' : buying === offer.slot ? '...' : 'Купить'}
                  </button>
                </div>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
