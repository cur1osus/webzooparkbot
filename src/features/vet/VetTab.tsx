import { useState } from 'react';
import { AnimalArt } from '@/components/AnimalArt';
import { apiCureAnimal } from '@/api';
import type { Animal } from '@/types';
import { fmt } from '@/utils/format';

// A sick animal earns half its income until healed. This tab is the only place to cure
// them: pick a patient, pay dollars, income recovers immediately. The price is per-animal
// (10 hours of its healthy income) and arrives on each animal as `cure_cost_usd`.

export function VetTab({
  animals,
  usd,
  onRefresh,
}: {
  animals: Animal[];
  usd: number;
  onRefresh: () => void;
}) {
  const sick = animals.filter(a => a.is_sick);
  const [curingId, setCuringId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cure = async (id: number) => {
    if (curingId !== null) return;
    setCuringId(id);
    setError(null);
    try {
      await apiCureAnimal(id);
      onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось вылечить');
    } finally {
      setCuringId(null);
    }
  };

  if (sick.length === 0) {
    return (
      <div className="px-[14px] pt-3 page-enter">
        <div className="card text-center py-10">
          <p className="m-0 text-[48px]" style={{ animation: 'float 3s ease-in-out infinite' }}>🩺</p>
          <p className="mt-3 mb-1 font-bold text-[15px]">Все звери здоровы</p>
          <p className="m-0 text-tg-hint text-[13px] max-w-[260px] mx-auto leading-snug">
            Заболевших нет. Больное животное приносит вдвое меньше дохода — заглядывай сюда, если кто-то захворает.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="px-[14px] pt-3 page-enter flex flex-col gap-3">
      <div
        className="rounded-2xl px-4 py-3 flex items-center justify-between gap-3"
        style={{ background: 'rgba(var(--c-red-rgb),0.08)', border: '1px solid rgba(var(--c-red-rgb),0.22)' }}
      >
        <div className="min-w-0">
          <p className="m-0 font-extrabold text-[14px]" style={{ color: 'var(--c-red-soft)' }}>
            🤒 Болеют: {sick.length}
          </p>
          <p className="m-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Пока не вылечишь, животное приносит ×0.5 дохода
          </p>
        </div>
        <span
          className="text-[12px] font-bold px-[10px] py-1 rounded-full shrink-0"
          style={{ background: 'rgba(var(--c-gold-rgb),0.14)', color: 'var(--c-gold)', border: '1px solid rgba(var(--c-gold-rgb),0.28)' }}
        >
          $ {fmt(usd)}
        </span>
      </div>

      {error && (
        <div
          className="rounded-xl px-4 py-3 text-[13px]"
          style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.25)', color: 'var(--c-red-soft)' }}
        >
          {error}
        </div>
      )}

      {sick.map(a => {
        const affordable = usd >= a.cure_cost_usd;
        const busy = curingId === a.id;
        return (
          <div
            key={a.id}
            className="rounded-2xl p-3 flex items-center gap-3"
            style={{ background: 'var(--surface-subtle)', border: '1px solid var(--card-border)' }}
          >
            <div
              className="w-12 h-12 rounded-xl grid place-items-center overflow-hidden shrink-0 relative"
              style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.25)' }}
            >
              <AnimalArt animal={a} size={44} />
              <span className="absolute -top-1 -right-1 text-[12px]">🤒</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="m-0 text-[13px] font-bold truncate">
                {a.name} <span className="font-normal" style={{ color: 'var(--tg-theme-hint-color)' }}>· {a.species_name}</span>
              </p>
              <p className="m-0 text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                Сейчас ₽{fmt(a.income)}/мин · болен
              </p>
            </div>
            <button
              onClick={() => void cure(a.id)}
              disabled={busy || !affordable}
              className="shrink-0 px-4 py-[10px] rounded-xl border-none font-extrabold text-[13px] disabled:opacity-45 disabled:cursor-not-allowed"
              style={{
                background: affordable ? 'var(--c-green)' : 'var(--surface-subtle-strong)',
                color: affordable ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)',
              }}
            >
              {busy ? 'Лечим...' : `Вылечить · $${fmt(a.cure_cost_usd)}`}
            </button>
          </div>
        );
      })}
    </div>
  );
}
