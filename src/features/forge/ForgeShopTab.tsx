import { useState } from 'react';
import { apiForgeCreate, apiForgeMerge, apiForgeSell, apiForgeUpgrade } from '@/api';
import { tmaConfirm } from '@/lib/tma';
import type { ForgeItem, GameState } from '@/types';
import { fmt } from '@/utils/format';
import { FORGE_CREATE_PAW, forgeCreateCostUsd, PROPERTY_ICON } from '@/data/itemProperties';

const RARITY_COLOR: Record<string, string> = {
  common: 'var(--tg-theme-hint-color)', rare: 'var(--c-green)', epic: 'var(--c-purple)', mythical: 'var(--c-orange)', legendary: 'var(--c-gold)',
};
const RARITY_LABEL: Record<string, string> = {
  common: 'Обычный', rare: 'Редкий', epic: 'Эпический', mythical: 'Мифический', legendary: 'Легендарный',
};
function forgeItemIcon(item: ForgeItem): string {
  const first = item.properties?.[0]?.kind;
  return first ? (PROPERTY_ICON[first] ?? '✨') : '✨';
}

export function ForgeShopTab({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [mergeFirst, setMergeFirst] = useState<string | null>(null);
  const [pendingItem, setPendingItem] = useState<ForgeItem | null>(null);

  const allItems = gs.items;
  const items = pendingItem ? allItems.filter(i => i.id !== pendingItem.id) : allItems;
  const itemCount = allItems.length;
  // The preview used to read `1 * 1.15^n`, promising a $1 artefact.
  const usdCost = forgeCreateCostUsd(itemCount);
  const pawCost = FORGE_CREATE_PAW;

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
      setPendingItem(r.item);
    } catch (e: unknown) {
      showToast((e as Error).message ?? 'Ошибка', false);
    } finally {
      setBusy(false);
    }
  }

  async function handlePendingSell() {
    if (!pendingItem || busy) return;
    setBusy(true);
    try {
      const r = await apiForgeSell(pendingItem.id);
      setPendingItem(null);
      onRefresh();
      showToast(`Продано за $${fmt(r.earned_usd)}`);
    } catch (e: unknown) {
      showToast((e as Error).message ?? 'Ошибка', false);
    } finally {
      setBusy(false);
    }
  }

  function handlePendingKeep() {
    setPendingItem(null);
  }

  async function handleUpgrade(item: ForgeItem) {
    if (busy) return;
    const level = item.level;
    const cost = 300 * (level + 1);
    const successPct = Math.max(0, 100 - 8 * level);
    if (!(await tmaConfirm(`Стоимость: $${fmt(cost)}\nШанс успеха: ${successPct}%`, `Улучшить ${item.name}?`))) return;
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
      return;
    }
    if (mergeFirst === item.id) {
      setMergeFirst(null);
      return;
    }
    const item1 = items.find(i => i.id === mergeFirst)!;
    const n1 = item1.properties?.length ?? 0;
    const n2 = item.properties?.length ?? 0;
    const cost = 1_000 * (n1 + n2 + Math.max(item1.level + item.level, 1));
    if (!(await tmaConfirm(`Стоимость: $${fmt(cost)}`, `Слить «${item1.name}» + «${item.name}»?`))) {
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

  const canAffordUsd = gs.usd >= usdCost;
  const canAffordPaw = gs.paw_coins >= pawCost;

  return (
    <div className="px-[14px] pt-3 flex flex-col gap-[10px]">
      {toast && (
        <div
          className="fixed top-[60px] left-1/2 z-50 px-4 py-3 rounded-xl text-sm font-semibold text-[var(--tg-theme-button-text-color)] shadow-lg"
          style={{
            transform: 'translateX(-50%)',
            background: toast.ok ? 'rgba(var(--c-green-rgb),0.95)' : 'rgba(var(--c-red-rgb),0.95)',
            maxWidth: '90vw',
          }}
        >
          {toast.msg}
        </div>
      )}

      <div className="card flex flex-col gap-[8px]">
        <div className="flex justify-between items-center mb-[4px]">
          <span className="font-bold text-sm">Создать предмет</span>
          <span className="text-xs text-tg-hint">В инвентаре: {itemCount}</span>
        </div>
        <button
          onClick={() => handleCreate('usd')}
          disabled={busy || !canAffordUsd}
          className="w-full py-[11px] rounded-[10px] border-none font-bold text-[14px] disabled:opacity-50 cursor-pointer"
          style={{ background: canAffordUsd ? 'var(--c-gold)' : 'rgba(var(--c-gold-rgb),0.15)', color: canAffordUsd ? '#000' : 'var(--c-gold)' }}
        >
          $ {fmt(usdCost)}
        </button>
        <button
          onClick={() => handleCreate('paw')}
          disabled={busy || !canAffordPaw}
          className="w-full py-[11px] rounded-[10px] border-none font-bold text-[14px] disabled:opacity-50 cursor-pointer"
          style={{ background: canAffordPaw ? 'rgba(var(--c-purple-rgb),0.2)' : 'rgba(var(--c-purple-rgb),0.08)', color: 'var(--c-purple)' }}
        >
          🐾 {pawCost} PawCoins
        </button>
      </div>

      {pendingItem && (() => {
        const rc = RARITY_COLOR[pendingItem.rarity] ?? 'var(--tg-theme-hint-color)';
        return (
          <div className="card flex flex-col gap-[10px]" style={{ border: `1px solid ${rc}55`, background: `${rc}0d` }}>
            <div className="flex items-center gap-[10px]">
              <span className="text-[32px] shrink-0">{forgeItemIcon(pendingItem)}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-[6px] flex-wrap">
                  <span className="font-bold text-sm">{pendingItem.name}</span>
                  <span className="text-[11px] px-[6px] py-[1px] rounded-full font-semibold"
                    style={{ background: `${rc}22`, color: rc }}>
                    {RARITY_LABEL[pendingItem.rarity] ?? pendingItem.rarity}
                  </span>
                </div>
                <div className="mt-[4px] flex flex-col gap-[2px]">
                  {(pendingItem.properties ?? []).map((p, i) => (
                    <span key={i} className="text-[12px] text-tg-hint">
                      {PROPERTY_ICON[p.kind] ?? '✨'} {p.label}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex gap-[8px]">
              <button
                onClick={handlePendingSell}
                disabled={busy}
                className="flex-1 py-[11px] rounded-[10px] border-none font-bold text-[14px] disabled:opacity-50 cursor-pointer"
                style={{ background: 'rgba(var(--c-red-rgb),0.15)', color: 'var(--c-red)' }}
              >
                Продать ${fmt(pendingItem.sell_price_usd)}
              </button>
              <button
                onClick={handlePendingKeep}
                disabled={busy}
                className="flex-1 py-[11px] rounded-[10px] border-none font-bold text-[14px] disabled:opacity-50 cursor-pointer"
                style={{ background: 'rgba(var(--c-green-rgb),0.15)', color: 'var(--c-green)' }}
              >
                Оставить
              </button>
            </div>
          </div>
        );
      })()}

      {mergeFirst && (
        <div className="card" style={{ border: '1px solid rgba(var(--c-gold-rgb),0.4)', background: 'rgba(var(--c-gold-rgb),0.08)' }}>
          <p className="m-0 text-[13px] text-[var(--c-gold)] font-semibold">
            Выбери второй предмет для слияния или нажми ещё раз на выбранный, чтобы отменить.
          </p>
        </div>
      )}

      {items.length === 0 && !pendingItem ? (
        <div className="card text-center">
          <p className="m-0 text-tg-hint text-[13px]">Предметов нет. Создай свой первый!</p>
        </div>
      ) : (
        items.map(item => {
          const rarityColor = RARITY_COLOR[item.rarity] ?? 'var(--tg-theme-hint-color)';
          const level = item.level;
          const upgradeCost = 300 * (level + 1);
          const successPct = Math.max(0, 100 - 8 * level);
          const isLegendary = item.rarity === 'legendary';
          const isSelected = mergeFirst === item.id;

          return (
            <div
              key={item.id}
              className="card flex flex-col gap-[8px]"
              style={{
                border: isSelected ? '1px solid rgba(var(--c-gold-rgb),0.6)' : undefined,
                background: isSelected ? 'rgba(var(--c-gold-rgb),0.07)' : undefined,
              }}
            >
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
                      <span className="text-[11px] px-[6px] py-[1px] rounded-full bg-[rgba(var(--c-green-rgb),0.15)] text-[var(--c-green)] font-semibold">
                        Активен
                      </span>
                    )}
                  </div>
                  <p className="m-0 mt-[2px] text-xs text-tg-hint">Уровень {level} / 12 · {item.properties?.length ?? 0} св-в</p>
                </div>
              </div>

              <div className="flex flex-col gap-[3px]">
                {(item.properties ?? []).map((p, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span className="text-[12px] text-tg-hint">
                      {PROPERTY_ICON[p.kind] ?? '✨'} {p.label.split(' ').slice(0, -1).join(' ')}
                    </span>
                    <span className="text-[12px] font-bold" style={{ color: rarityColor }}>
                      {p.label.split(' ').pop()}
                    </span>
                  </div>
                ))}
              </div>

              <div className="flex gap-[6px] mt-[2px]">
                <button
                  onClick={() => handleUpgrade(item)}
                  disabled={busy || level >= 12 || gs.usd < upgradeCost}
                  className="flex-1 py-[9px] rounded-[8px] border-none font-semibold text-[12px] disabled:opacity-40 cursor-pointer"
                  style={{ background: 'rgba(var(--c-blue-rgb),0.15)', color: 'var(--c-blue)' }}
                >
                  {level >= 12 ? 'Макс уровень' : `Улучш. $${fmt(upgradeCost)} (${successPct}%)`}
                </button>

                <button
                  onClick={() => handleMergeSelect(item)}
                  disabled={busy || isLegendary}
                  className="flex-1 py-[9px] rounded-[8px] border-none font-semibold text-[12px] disabled:opacity-40 cursor-pointer"
                  style={{
                    background: isSelected ? 'rgba(var(--c-gold-rgb),0.2)' : 'rgba(var(--c-gold-rgb),0.1)',
                    color: 'var(--c-gold)',
                  }}
                >
                  {isLegendary ? 'Нельзя слить' : isSelected ? '✓ Выбран' : 'Слить'}
                </button>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
