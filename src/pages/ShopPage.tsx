import { useState } from 'react';
import { fmt } from '../utils/format';
import type { ForgeItem, GameState } from '../types';
import { AVIARIES } from '../data/aviaries';
import { PacksPage } from './PacksPage';
import { LocalitiesPage } from './LocalitiesPage';
import {
  apiForgeCreate,
  apiForgeUpgrade,
  apiForgeMerge,
  apiForgeSell,
  apiForgeActivate,
} from '../api';

type ShopTab = 'packs' | 'localities' | 'aviaries' | 'forge' | 'cosmetics';

const SHOP_TABS: { id: ShopTab; emoji: string; label: string }[] = [
  { id: 'packs',      emoji: '📦', label: 'Паки' },
  { id: 'localities', emoji: '🌍', label: 'Местности' },
  { id: 'aviaries',   emoji: '🏗️', label: 'Вольеры' },
  { id: 'forge',      emoji: '🔨', label: 'Кузница' },
  { id: 'cosmetics',  emoji: '🎨', label: 'Мета' },
];

const RARITY_COLOR: Record<string, string> = {
  common: '#8f95ab', rare: '#34c759', epic: '#bf5af2', mythical: '#ff6b3d', legendary: '#ffd60a',
};
const RARITY_LABEL: Record<string, string> = {
  common: 'Обычный', rare: 'Редкий', epic: 'Эпический', mythical: 'Мифический', legendary: 'Легендарный',
};
const PROP_ICON: Record<string, string> = {
  bank_rate: '🔄',
  income_boost: '📈',
  animal_income: '🐾',
  aviary_discount: '🏗️',
  animal_discount: '📉',
  extra_turns: '🎲',
  last_chance: '🍀',
  bonus_rerolls: '🎁',
};

function forgeItemIcon(item: ForgeItem): string {
  const first = item.properties?.[0]?.type;
  return first ? (PROP_ICON[first] ?? '✨') : '✨';
}

// ─── Forge tab ───────────────────────────────────────────────────────────────

function ForgeTab({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [mergeFirst, setMergeFirst] = useState<string | null>(null);

  const items = gs.forge_items;
  const itemCount = items.length;
  const usdCost = Math.round(100_000 * Math.pow(1.15, itemCount));
  const pawCost = 350;
  const activeCount = items.filter(i => i.is_active).length;

  function showToast(msg: string, ok = true) {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3000);
  }

  async function handleCreate(currency: 'usd' | 'paw') {
    if (busy) return;
    setBusy(true);
    try {
      const r = await apiForgeCreate(currency);
      onRefresh();
      const rLabel = RARITY_LABEL[r.item.rarity] ?? r.item.rarity;
      showToast(`Создан ${rLabel} артефакт! ${r.item.properties?.map(p => p.label).join(', ')}`);
    } catch (e: unknown) {
      showToast((e as Error).message ?? 'Ошибка', false);
    } finally {
      setBusy(false);
    }
  }

  async function handleUpgrade(item: ForgeItem) {
    if (busy) return;
    const level = item.level;
    const cost = 30_000 * (level + 1);
    const successPct = Math.max(0, 100 - 8 * level);
    if (!confirm(`Улучшить ${item.name}?\nСтоимость: $${fmt(cost)}\nШанс успеха: ${successPct}%`)) return;
    setBusy(true);
    try {
      const r = await apiForgeUpgrade(item.id);
      onRefresh();
      if (r.success) showToast(`Успех! Уровень ${r.item.level}`);
      else showToast(`Провал. $${fmt(cost)} потрачены, свойства не изменились.`, false);
    } catch (e: unknown) {
      showToast((e as Error).message ?? 'Ошибка', false);
    } finally {
      setBusy(false);
    }
  }

  async function handleMergeSelect(item: ForgeItem) {
    if (!mergeFirst) {
      setMergeFirst(item.id);
      showToast(`Выбран «${item.name}». Теперь выбери второй предмет для слияния.`);
      return;
    }
    if (mergeFirst === item.id) {
      setMergeFirst(null);
      return;
    }
    const item1 = items.find(i => i.id === mergeFirst)!;
    const n1 = item1.properties?.length ?? 0;
    const n2 = item.properties?.length ?? 0;
    const cost = 100_000 * (n1 + n2 + Math.max(item1.level + item.level, 1));
    if (!confirm(`Слить «${item1.name}» + «${item.name}»?\nСтоимость: $${fmt(cost)}`)) {
      setMergeFirst(null);
      return;
    }
    setMergeFirst(null);
    setBusy(true);
    try {
      const r = await apiForgeMerge(mergeFirst, item.id);
      onRefresh();
      const rLabel = RARITY_LABEL[r.new_item.rarity] ?? r.new_item.rarity;
      showToast(`Получен ${rLabel} артефакт с ${r.new_item.properties?.length} св-вами!`);
    } catch (e: unknown) {
      showToast((e as Error).message ?? 'Ошибка', false);
    } finally {
      setBusy(false);
    }
  }

  async function handleSell(item: ForgeItem) {
    if (busy) return;
    if (!confirm(`Продать «${item.name}» за $80 000? Это нельзя отменить.`)) return;
    setBusy(true);
    try {
      await apiForgeSell(item.id);
      onRefresh();
      showToast(`Продан за $80 000`);
    } catch (e: unknown) {
      showToast((e as Error).message ?? 'Ошибка', false);
    } finally {
      setBusy(false);
    }
  }

  async function handleActivate(item: ForgeItem) {
    if (busy) return;
    setBusy(true);
    try {
      await apiForgeActivate(item.id);
      onRefresh();
    } catch (e: unknown) {
      showToast((e as Error).message ?? 'Ошибка', false);
    } finally {
      setBusy(false);
    }
  }

  const canAffordUsd = gs.usd >= usdCost;
  const canAffordPaw = gs.paw_coins >= pawCost;

  return (
    <div className="px-[14px] pt-3 flex flex-col gap-[10px]">
      {/* Toast */}
      {toast && (
        <div
          className="fixed top-[60px] left-1/2 z-50 px-4 py-3 rounded-xl text-sm font-semibold text-white shadow-lg"
          style={{
            transform: 'translateX(-50%)',
            background: toast.ok ? 'rgba(52,199,89,0.95)' : 'rgba(255,69,58,0.95)',
            maxWidth: '90vw',
          }}
        >
          {toast.msg}
        </div>
      )}

      {/* Info */}
      <div className="card">
        <p className="m-0 mb-[6px] font-bold text-base">⚒️ Кузница предметов</p>
        <p className="m-0 text-[13px] text-tg-hint">
          До 3 активных предметов. Редкость выпадает случайно: Common 50%, Rare 30%, Epic 13%, Mythical 7%.
          Каждый предмет в инвентаре поднимает стоимость создания на +15%.
        </p>
      </div>

      {/* Create */}
      <div className="card flex flex-col gap-[8px]">
        <div className="flex justify-between items-center mb-[4px]">
          <span className="font-bold text-sm">Создать предмет</span>
          <span className="text-xs text-tg-hint">В инвентаре: {itemCount}</span>
        </div>
        <button
          onClick={() => handleCreate('usd')}
          disabled={busy || !canAffordUsd}
          className="w-full py-[11px] rounded-[10px] border-none font-bold text-[14px] disabled:opacity-50 cursor-pointer"
          style={{ background: canAffordUsd ? '#ffd60a' : 'rgba(255,214,10,0.15)', color: canAffordUsd ? '#000' : '#ffd60a' }}
        >
          $ {fmt(usdCost)}
        </button>
        <button
          onClick={() => handleCreate('paw')}
          disabled={busy || !canAffordPaw}
          className="w-full py-[11px] rounded-[10px] border-none font-bold text-[14px] disabled:opacity-50 cursor-pointer"
          style={{ background: canAffordPaw ? 'rgba(191,90,242,0.2)' : 'rgba(191,90,242,0.08)', color: '#bf5af2' }}
        >
          🐾 {pawCost} PawCoins (фиксированно)
        </button>
      </div>

      {/* Active summary */}
      {activeCount > 0 && (
        <div className="card" style={{ border: '1px solid rgba(52,199,89,0.25)', background: 'rgba(52,199,89,0.06)' }}>
          <p className="m-0 mb-[6px] text-[13px] font-semibold text-[#34c759]">Активных: {activeCount} / 3</p>
          {items.filter(i => i.is_active).map(item => (
            <div key={item.id} className="text-[12px] text-tg-hint mb-[2px]">
              {forgeItemIcon(item)} {item.name} · {item.properties?.map(p => p.label).join(', ')}
            </div>
          ))}
        </div>
      )}

      {/* Merge hint */}
      {mergeFirst && (
        <div className="card" style={{ border: '1px solid rgba(255,214,10,0.4)', background: 'rgba(255,214,10,0.08)' }}>
          <p className="m-0 text-[13px] text-[#ffd60a] font-semibold">
            Выбери второй предмет для слияния или нажми ещё раз на выбранный, чтобы отменить.
          </p>
        </div>
      )}

      {/* Items list */}
      {items.length === 0 ? (
        <div className="card text-center">
          <p className="m-0 text-tg-hint text-[13px]">Предметов нет. Создай свой первый!</p>
        </div>
      ) : (
        items.map(item => {
          const rarityColor = RARITY_COLOR[item.rarity] ?? '#8f95ab';
          const level = item.level;
          const upgradeCost = 30_000 * (level + 1);
          const successPct = Math.max(0, 100 - 8 * level);
          const isLegendary = item.rarity === 'legendary';
          const isSelected = mergeFirst === item.id;

          return (
            <div
              key={item.id}
              className="card flex flex-col gap-[8px]"
              style={{
                border: isSelected
                  ? '1px solid rgba(255,214,10,0.6)'
                  : item.is_active
                  ? `1px solid ${rarityColor}44`
                  : undefined,
                background: isSelected
                  ? 'rgba(255,214,10,0.07)'
                  : item.is_active
                  ? `${rarityColor}0a`
                  : undefined,
              }}
            >
              {/* Header */}
              <div className="flex items-center gap-[10px]">
                <span className="text-[30px] shrink-0">{forgeItemIcon(item)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-[6px] flex-wrap">
                    <span className="font-bold text-sm">{item.name}</span>
                    <span
                      className="text-[11px] px-[6px] py-[1px] rounded-full font-semibold"
                      style={{ background: `${rarityColor}22`, color: rarityColor }}
                    >
                      {RARITY_LABEL[item.rarity] ?? item.rarity}
                    </span>
                    {item.is_active && (
                      <span className="text-[11px] px-[6px] py-[1px] rounded-full bg-[rgba(52,199,89,0.15)] text-[#34c759] font-semibold">
                        Активен
                      </span>
                    )}
                  </div>
                  <p className="m-0 mt-[2px] text-xs text-tg-hint">Уровень {level} / 12 · {item.properties?.length ?? 0} св-в</p>
                </div>
              </div>

              {/* Properties */}
              <div className="flex flex-col gap-[3px]">
                {(item.properties ?? []).map((p, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span className="text-[12px] text-tg-hint">
                      {PROP_ICON[p.type] ?? '✨'} {p.label.split(' ').slice(0, -1).join(' ')}
                    </span>
                    <span className="text-[12px] font-bold" style={{ color: rarityColor }}>
                      {p.label.split(' ').pop()}
                    </span>
                  </div>
                ))}
              </div>

              {/* Actions */}
              <div className="grid grid-cols-2 gap-[6px] mt-[2px]">
                {/* Activate / Deactivate */}
                <button
                  onClick={() => handleActivate(item)}
                  disabled={busy || (!item.is_active && activeCount >= 3)}
                  className="py-[9px] rounded-[8px] border-none font-semibold text-[12px] disabled:opacity-40 cursor-pointer"
                  style={{
                    background: item.is_active ? 'rgba(255,255,255,0.08)' : 'rgba(52,199,89,0.15)',
                    color: item.is_active ? 'var(--tg-theme-hint-color)' : '#34c759',
                  }}
                >
                  {item.is_active ? 'Деактивировать' : 'Активировать'}
                </button>

                {/* Upgrade */}
                <button
                  onClick={() => handleUpgrade(item)}
                  disabled={busy || level >= 12 || gs.usd < upgradeCost}
                  className="py-[9px] rounded-[8px] border-none font-semibold text-[12px] disabled:opacity-40 cursor-pointer"
                  style={{ background: 'rgba(10,132,255,0.15)', color: '#0a84ff' }}
                >
                  {level >= 12 ? 'Макс уровень' : `Улучш. $${fmt(upgradeCost)} (${successPct}%)`}
                </button>

                {/* Merge */}
                <button
                  onClick={() => handleMergeSelect(item)}
                  disabled={busy || isLegendary}
                  className="py-[9px] rounded-[8px] border-none font-semibold text-[12px] disabled:opacity-40 cursor-pointer"
                  style={{
                    background: isSelected ? 'rgba(255,214,10,0.2)' : 'rgba(255,214,10,0.1)',
                    color: '#ffd60a',
                  }}
                >
                  {isLegendary ? 'Нельзя слить' : isSelected ? '✓ Выбран' : 'Слить'}
                </button>

                {/* Sell */}
                <button
                  onClick={() => handleSell(item)}
                  disabled={busy}
                  className="py-[9px] rounded-[8px] border-none font-semibold text-[12px] disabled:opacity-40 cursor-pointer"
                  style={{ background: 'rgba(255,69,58,0.15)', color: '#ff453a' }}
                >
                  Продать $80k
                </button>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}

// ─── ShopPage ─────────────────────────────────────────────────────────────────

export function ShopPage({
  gs,
  onBuyAviary,
  onRefresh,
}: {
  gs: GameState;
  onBuyAviary: (id: string) => void;
  onRefresh: () => void;
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
      {tab === 'forge' && <ForgeTab gs={gs} onRefresh={onRefresh} />}

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
