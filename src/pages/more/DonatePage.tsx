import { useEffect, useState } from 'react';
import type { GameState } from '../../types';
import { apiGetDonateInfo, apiCreateDonateInvoice } from '../../api';

const STAR_OPTIONS = [1, 5, 10, 25, 50, 100, 250, 500];

export function DonatePage({ gs: _gs }: { gs: GameState }) {
  const [starsToPaw, setStarsToPaw] = useState<number>(10);
  const [stars, setStars] = useState<number | null>(null);
  const [buying, setBuying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGetDonateInfo()
      .then(r => setStarsToPaw(r.stars_to_paw))
      .catch(() => {});
  }, []);

  const handleDonate = async () => {
    if (!stars) return;
    setBuying(true);
    setError(null);
    try {
      const res = await apiCreateDonateInvoice(stars);
      if (res.invoice_link) {
        window.open(res.invoice_link, '_blank');
      }
    } catch (e) {
      setError((e as Error).message ?? 'Ошибка');
    } finally {
      setBuying(false);
    }
  };

  return (
    <div className="p-[14px] flex flex-col gap-3">
      <div className="card text-center">
        <span className="text-[48px]">⭐️</span>
        <p className="mt-[10px] mb-1 text-lg font-extrabold">Донат Telegram Stars</p>
        <p className="m-0 text-[13px] text-tg-hint">
          1 ⭐️ = {starsToPaw} 🐾 PawCoins · Поддержи игру!
        </p>
      </div>

      <div className="card">
        <p className="m-0 mb-[10px] font-bold">Выбери количество звёзд:</p>

        <div className="grid grid-cols-4 gap-2">
          {STAR_OPTIONS.map(s => (
            <button
              key={s}
              onClick={() => setStars(s)}
              className="py-[10px] px-1 rounded-[10px] cursor-pointer text-[13px] transition-all"
              style={{
                background: stars === s ? 'rgba(255,214,10,0.2)' : 'rgba(255,255,255,0.08)',
                color: stars === s ? '#ffd60a' : 'var(--tg-theme-hint-color)',
                fontWeight: stars === s ? 700 : 400,
                border: `1px solid ${stars === s ? 'rgba(255,214,10,0.4)' : 'transparent'}`,
              }}
            >
              ⭐️ {s}
            </button>
          ))}
        </div>

        {stars && (
          <div className="mt-3 px-3 py-[10px] rounded-[10px] bg-black/20">
            <p className="m-0 text-[13px] text-tg-hint">За {stars} ⭐️ получишь:</p>
            <p className="mt-1 mb-0 text-lg font-extrabold text-[#bf5af2]">
              {stars * starsToPaw} 🐾 PawCoins
            </p>
          </div>
        )}

        {error && <p className="mt-2 mb-0 text-[#ff6b63] text-[13px]">⚠️ {error}</p>}

        <button
          onClick={() => void handleDonate()}
          disabled={!stars || buying}
          className="w-full py-[13px] rounded-[10px] border-none cursor-pointer font-extrabold text-[15px] mt-3 disabled:opacity-60 transition-all"
          style={{
            background: stars ? '#ffd60a' : 'rgba(255,255,255,0.08)',
            color: stars ? '#1c1c1e' : 'var(--tg-theme-hint-color)',
          }}
        >
          {buying ? 'Открываем...' : stars ? `⭐️ Задонатить ${stars} звёзд` : 'Выбери количество'}
        </button>
      </div>

      <div className="card">
        <p className="m-0 mb-[6px] font-bold text-[13px]">Что дают PawCoins?</p>
        {[
          '⚒️ Создание предметов в кузнице',
          '💊 Лечение больных животных',
          '🎮 Особые игровые бонусы',
        ].map(item => (
          <p key={item} className="mt-1 mb-0 text-[13px] text-tg-hint">{item}</p>
        ))}
      </div>
    </div>
  );
}
