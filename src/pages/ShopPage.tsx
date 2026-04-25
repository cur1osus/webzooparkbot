import { useState } from 'react';
import { fmt } from '@/utils/format';
import type { GameState } from '@/types';
import { PacksPage } from './PacksPage';
import { LocalitiesPage } from './LocalitiesPage';
import { ForgeShopTab } from '@/features/forge/ForgeShopTab';

type ShopTab = 'packs' | 'localities' | 'forge' | 'cosmetics';

const SHOP_TABS: { id: ShopTab; emoji: string; label: string }[] = [
  { id: 'packs',      emoji: '📦', label: 'Паки' },
  { id: 'localities', emoji: '🌍', label: 'Местности' },
  { id: 'forge',      emoji: '🔨', label: 'Кузница' },
  { id: 'cosmetics',  emoji: '🎨', label: 'Мета' },
];

// ─── ShopPage ─────────────────────────────────────────────────────────────────

export function ShopPage({
  gs,
  onRefresh,
}: {
  gs: GameState;
  onRefresh: () => void;
}) {
  const [tab, setTab] = useState<ShopTab>('packs');

  return (
    <div className="page-content-safe">
      {/* Header */}
      <div className="px-[14px] pt-[14px]">
        <p className="m-0 mb-[10px] text-[22px] font-extrabold">🛒 Зоомаркет</p>

        {/* Balance + seats */}
        <div className="flex gap-[6px] mb-[10px] overflow-x-auto">
          {[
            { label: `₽ ${fmt(gs.rub)}`,    color: 'var(--c-green)' },
            { label: `$ ${fmt(gs.usd)}`,    color: 'var(--c-gold)' },
            { label: `🐾 ${gs.paw_coins}`,  color: 'var(--c-purple)' },
          ].map(({ label, color }) => (
            <span key={label} className="px-[10px] py-1 rounded-[20px] text-[13px] font-bold whitespace-nowrap shrink-0"
              style={{ background: `color-mix(in srgb, ${color} 10%, transparent)`, color, border: `1px solid color-mix(in srgb, ${color} 19%, transparent)` }}>
              {label}
            </span>
          ))}
          <span className="px-[10px] py-1 rounded-[20px] text-[13px] font-bold whitespace-nowrap shrink-0"
            style={{ background: 'rgba(143,149,171,0.15)', color: 'var(--tg-theme-hint-color)', border: '1px solid rgba(143,149,171,0.2)' }}>
            🌍 {fmt(gs.localities_count)} местн.
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
      {tab === 'packs' && <PacksPage gs={gs} onRefresh={onRefresh} />}

      {/* LOCALITIES */}
      {tab === 'localities' && <LocalitiesPage gs={gs} onRefresh={onRefresh} />}

      {/* FORGE */}
      {tab === 'forge' && <ForgeShopTab gs={gs} onRefresh={onRefresh} />}

      {/* COSMETICS */}
      {tab === 'cosmetics' && (
        <div className="px-[14px] pt-3 flex flex-col gap-[10px]">
          <div className="card">
            <p className="m-0 mb-[6px] text-base font-bold">🎨 Цвет ника в топе</p>
            <p className="m-0 mb-3 text-[13px] text-tg-hint">
              Твой ник в таблице лидеров будет выделен выбранным цветом. Покупка — навсегда.
            </p>

            <div className="flex gap-2 mb-3">
              <button className="px-[14px] py-[6px] rounded-[20px] border-none cursor-pointer text-[13px] font-semibold bg-[var(--c-green)] text-[var(--tg-theme-button-text-color)]">
                Дешевле
              </button>
              <button className="px-[14px] py-[6px] rounded-[20px] border-none cursor-pointer text-[13px] font-semibold text-tg-hint" style={{ background: 'var(--surface-subtle)' }}>
                Дороже
              </button>
            </div>

            <div className="card flex justify-between items-center" style={{ background: 'var(--tg-theme-bg-color)' }}>
              <span className="font-bold">{gs.nickname}</span>
              <span className="text-tg-hint text-[13px]">По умолчанию</span>
              <button className="px-[14px] py-[6px] rounded-lg border-none cursor-pointer bg-[rgba(var(--c-blue-rgb),0.15)] text-[var(--c-blue)] font-semibold text-[13px]">
                Выбрать
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
