import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { GameState, MerchantAnimal } from '@/types';
import { apiGetMerchant, apiBuyFromMerchant } from '@/api';
import { fmt } from '@/utils/format';
import { ANIMALS } from '@/data/animals';

export function MerchantPage({ gs, onBuy }: { gs: GameState; onBuy: () => void }) {
  const [buying, setBuying] = useState<number | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ['merchant'],
    queryFn: apiGetMerchant,
    staleTime: 30_000,
  });

  const handleBuy = async (slot: 1 | 2 | 3) => {
    setBuying(slot);
    setMsg(null);
    try {
      const res = await apiBuyFromMerchant(slot);
      if (res.ok) {
        setMsg('Куплено!');
        onBuy();
        void refetch();
      } else {
        setMsg(res.message ?? 'Ошибка');
      }
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Ошибка покупки');
    } finally {
      setBuying(null);
    }
  };

  return (
    <div className="p-[14px] flex flex-col gap-3">
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
          <p className="m-0 text-[13px] text-tg-hint">
            Обновится: {new Date(data.refreshes_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })}
          </p>

          {data.animals.map((offer: MerchantAnimal) => {
            const def = ANIMALS.find(a => a.id === offer.animal_id);
            const affordable = gs.rub >= offer.final_price;
            return (
              <div key={offer.slot} className="card">
                <div className="flex items-center gap-3 mb-[10px]">
                  <span className="text-[36px] shrink-0">{def?.emoji ?? '🐾'}</span>
                  <div className="flex-1">
                    <p className="m-0 font-bold text-sm">{def?.name ?? offer.animal_id}</p>
                    <p className="mt-[2px] mb-0 text-xs text-tg-hint">
                      {offer.quantity} шт. · +{fmt(def?.income_rub_per_min ?? 0)}₽/мин
                    </p>
                  </div>
                  <div className="bg-[rgba(var(--c-green-rgb),0.15)] rounded-lg px-[10px] py-1 text-[var(--c-green)] font-extrabold text-[15px]">
                    -{offer.discount_pct}%
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs text-tg-hint line-through">₽ {fmt(offer.original_price)}</span>
                    <span className="ml-2 text-[15px] font-extrabold">₽ {fmt(offer.final_price)}</span>
                  </div>
                  <button
                    onClick={() => void handleBuy(offer.slot)}
                    disabled={buying === offer.slot || !affordable}
                    className="px-4 py-2 rounded-[10px] border-none cursor-pointer font-bold text-sm disabled:opacity-60"
                    style={{
                      background: affordable ? 'var(--c-green)' : 'var(--surface-subtle)',
                      color: affordable ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)',
                    }}
                  >
                    {buying === offer.slot ? '...' : 'Купить'}
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
