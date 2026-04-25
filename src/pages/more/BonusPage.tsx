import { useState } from 'react';
import type { GameState } from '@/types';
import { apiClaimBonus } from '@/api';

export function BonusPage({ gs, onClaim }: { gs: GameState; onClaim: () => void }) {
  const [claiming, setClaiming] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const available = gs.bonus === 1;

  const handleClaim = async () => {
    setClaiming(true);
    setResult(null);
    setError(null);
    try {
      const res = await apiClaimBonus();
      if (res.ok) {
        setResult(res.message);
        onClaim();
      } else {
        setError(res.message ?? 'Ошибка');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка получения бонуса');
    } finally {
      setClaiming(false);
    }
  };

  return (
    <div className="p-[14px] flex flex-col gap-3">
      <div className="card text-center">
        <span className="text-[48px]">🎁</span>
        <p className="mt-[10px] mb-1 text-lg font-extrabold">Ежедневный бонус</p>
        <p className="m-0 text-[13px] text-tg-hint">
          Каждый день в 11:00 доступен новый бонус.
          <br />Получи рубли, доллары, лапки, животное или вольер!
        </p>
      </div>

      {result && (
        <div className="card bg-[rgba(var(--c-green-rgb),0.1)] border border-[rgba(var(--c-green-rgb),0.3)]">
          <p className="m-0 font-bold text-[var(--c-green)]">🎉 {result}</p>
        </div>
      )}

      {error && (
        <div className="card bg-[rgba(var(--c-red-rgb),0.1)] border border-[rgba(var(--c-red-rgb),0.3)]">
          <p className="m-0 text-[var(--c-red-soft)]">⚠️ {error}</p>
        </div>
      )}

      <button
        onClick={() => void handleClaim()}
        disabled={!available || claiming}
        className="py-[14px] rounded-xl border-none cursor-pointer font-extrabold text-base disabled:opacity-60 disabled:cursor-not-allowed"
        style={{
          background: available ? 'var(--c-green)' : 'var(--surface-subtle)',
          color: available ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)',
        }}
      >
        {claiming ? 'Получаем...' : available ? '🎁 Получить бонус' : '⏳ Уже получен сегодня'}
      </button>

      <div className="card">
        <p className="m-0 mb-2 font-bold">Возможные награды:</p>
        {[
          ['₽',  'Рубли — основная валюта'],
          ['$',  'Доллары — для обмена в банке'],
          ['🐾', 'PawCoins — для кузницы и лечения'],
          ['🏗️', 'Вольер — дополнительные места'],
          ['🐾', 'Животное — из твоего зоопарка'],
        ].map(([icon, desc]) => (
          <div key={desc} className="flex gap-[10px] mb-[6px]">
            <span className="text-lg shrink-0">{icon}</span>
            <span className="text-[13px] text-tg-hint">{desc}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
