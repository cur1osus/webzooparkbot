import { useState } from 'react';
import { fmt } from '../utils/format';
import type { GameState } from '../types';
import { AVIARIES } from '../data/aviaries';
import { PacksPage } from './PacksPage';
import { LocalitiesPage } from './LocalitiesPage';

type ShopTab = 'packs' | 'localities' | 'aviaries' | 'forge' | 'cosmetics';

const SHOP_TABS: { id: ShopTab; emoji: string; label: string }[] = [
  { id: 'packs',      emoji: '📦', label: 'Паки' },
  { id: 'localities', emoji: '🌍', label: 'Местности' },
  { id: 'aviaries',   emoji: '🏗️', label: 'Вольеры' },
  { id: 'forge',      emoji: '🔨', label: 'Кузница' },
  { id: 'cosmetics',  emoji: '🎨', label: 'Мета' },
];

export function ShopPage({
  gs,
  onBuyAviary,
}: {
  gs: GameState;
  onBuyAviary: (id: string) => void;
}) {
  const [tab, setTab] = useState<ShopTab>('packs');

  const canAfford = (price: number) => gs.rub >= price;

  return (
    <div className="page-content-safe">
      {/* Header */}
      <div className="px-[14px] pt-[14px]">
        <p className="m-0 mb-[10px] text-[22px] font-extrabold">🛒 Зоомаркет</p>

        {/* Balance + seats */}
        <div className="flex gap-[6px] mb-[10px] overflow-x-auto">
          {[
            { label: `₽ ${fmt(gs.rub)}`,    color: '#34c759' },
            { label: `$ ${fmt(gs.usd)}`,    color: '#ffd60a' },
            { label: `🐾 ${gs.paw_coins}`,  color: '#bf5af2' },
          ].map(({ label, color }) => (
            <span key={label} className="px-[10px] py-1 rounded-[20px] text-[13px] font-bold whitespace-nowrap shrink-0"
              style={{ background: `${color}18`, color, border: `1px solid ${color}30` }}>
              {label}
            </span>
          ))}
          <span className="px-[10px] py-1 rounded-[20px] text-[13px] font-bold whitespace-nowrap shrink-0"
            style={{ background: 'rgba(143,149,171,0.15)', color: '#8f95ab', border: '1px solid rgba(143,149,171,0.2)' }}>
            🏗️ {fmt(gs.free_seats)} мест
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div
        className="flex mx-[14px] mb-1 rounded-2xl p-1"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 18%, transparent)' }}
      >
        {SHOP_TABS.map(t => {
          const isActive = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className="flex-1 flex items-center justify-center py-[10px] rounded-xl border-none transition-all duration-200"
              style={{
                background: isActive ? 'color-mix(in srgb, var(--tg-theme-button-color) 15%, transparent)' : 'transparent',
                color: isActive ? 'var(--tg-theme-text-color)' : 'var(--tg-theme-hint-color)',
                boxShadow: isActive ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
              }}
            >
              <span className="text-[18px]">{t.emoji}</span>
            </button>
          );
        })}
      </div>

      {/* PACKS */}
      {tab === 'packs' && <PacksPage gs={gs} />}

      {/* LOCALITIES */}
      {tab === 'localities' && <LocalitiesPage gs={gs} />}

      {/* AVIARIES */}
      {tab === 'aviaries' && (
        <div className="px-[14px] flex flex-col gap-[10px] pt-3">
          {AVIARIES.map(av => {
            const owned = gs.aviaries.find(x => x.aviary_id === av.id)?.count ?? 0;
            const affordable = canAfford(av.price_rub);
            return (
              <div key={av.id} className="card">
                <div className="flex items-center gap-3 mb-[10px]">
                  <span className="text-[36px]">{av.emoji}</span>
                  <div>
                    <p className="m-0 font-bold text-[15px]">{av.name}</p>
                    <p className="mt-[2px] mb-0 text-[13px] text-tg-hint">
                      {av.seats} мест · ₽ {fmt(av.price_rub)}
                    </p>
                    {owned > 0 && (
                      <p className="mt-[2px] mb-0 text-xs text-[#34c759]">У вас: {owned} шт.</p>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => onBuyAviary(av.id)}
                  disabled={!affordable}
                  className="w-full py-[10px] rounded-[10px] border-none font-bold text-sm disabled:opacity-60 cursor-pointer"
                  style={{
                    background: affordable ? '#0a84ff' : 'color-mix(in srgb, var(--tg-theme-hint-color) 15%, transparent)',
                    color: affordable ? '#fff' : 'var(--tg-theme-hint-color)',
                  }}
                >
                  {affordable ? `Купить — ₽ ${fmt(av.price_rub)}` : 'Недостаточно средств'}
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* FORGE */}
      {tab === 'forge' && (
        <div className="px-[14px] pt-3 flex flex-col gap-[10px]">
          <div className="card">
            <p className="m-0 mb-2 font-bold text-base">⚒️ Кузница предметов</p>
            <p className="m-0 mb-3 text-[13px] text-tg-hint">
              Создавай, улучшай и объединяй магические предметы для бонусов.
            </p>
            <p className="m-0 text-[13px] text-tg-hint">
              Предметов в наличии: {gs.forge_items.length}
            </p>
          </div>
          <button className="py-[13px] rounded-xl border-none cursor-pointer bg-tg-button text-white font-bold text-[15px]">
            🐾 Создать предмет
          </button>
        </div>
      )}

      {/* COSMETICS */}
      {tab === 'cosmetics' && (
        <div className="px-[14px] pt-3 flex flex-col gap-[10px]">
          <div className="card">
            <p className="m-0 mb-[6px] text-base font-bold">🎨 Цвет ника в топе</p>
            <p className="m-0 mb-3 text-[13px] text-tg-hint">
              Твой ник в таблице лидеров будет выделен выбранным цветом. Покупка — навсегда.
            </p>

            <div className="flex gap-2 mb-3">
              <button className="px-[14px] py-[6px] rounded-[20px] border-none cursor-pointer text-[13px] font-semibold bg-[#34c759] text-white">
                Дешевле
              </button>
              <button className="px-[14px] py-[6px] rounded-[20px] border-none cursor-pointer text-[13px] font-semibold bg-white/[0.08] text-tg-hint">
                Дороже
              </button>
            </div>

            <div className="card flex justify-between items-center" style={{ background: 'var(--tg-theme-bg-color)' }}>
              <span className="font-bold">{gs.nickname}</span>
              <span className="text-tg-hint text-[13px]">По умолчанию</span>
              <button className="px-[14px] py-[6px] rounded-lg border-none cursor-pointer bg-[rgba(10,132,255,0.15)] text-[#0a84ff] font-semibold text-[13px]">
                Выбрать
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
