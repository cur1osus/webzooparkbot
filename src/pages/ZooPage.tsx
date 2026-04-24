import { useState } from 'react';
import { fmt, fmtMin, formatDateShort } from '../utils/format';
import type { GameState, ForgeItem, ForgeSet } from '../types';
import { ANIMALS } from '../data/animals';
import { ExpeditionOverviewCard, ExpeditionPage } from './ExpeditionPage';
import { getClanSpecialtyLabel } from '../utils/clan';
import { apiForgeActivate, apiForgeApplySet, apiForgeCreateSet, apiForgeDeleteSet, apiForgeSell, apiForgeUpdateSet } from '../api';
import { tmaConfirm } from '../tma';

type ZooTab = 'overview' | 'forge' | 'aviaries' | 'medals';

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
const PROP_LABEL: Record<string, string> = {
  bank_rate: 'Курс банка',
  income_boost: 'Общий доход',
  animal_income: 'Доход животных',
  aviary_discount: 'Вольеры',
  animal_discount: 'Животные',
  extra_turns: 'Доп. ходы',
  last_chance: 'Последний шанс',
  bonus_rerolls: 'Перебросы',
};
function forgeItemIcon(item: ForgeItem): string {
  const first = item.properties?.[0]?.type;
  return first ? (PROP_ICON[first] ?? '✨') : '✨';
}

function itemBonusSummary(item: ForgeItem): string {
  const props = item.properties ?? [];
  if (props.length === 0) return 'Нет свойств';
  return props.map(p => p.label).join(' · ');
}

const RARITY_COLOR: Record<string, string> = {
  common: 'var(--tg-theme-hint-color)', rare: 'var(--c-green)', epic: 'var(--c-purple)', mythical: 'var(--c-orange)', legendary: 'var(--c-gold)',
};
const RARITY_LABEL: Record<string, string> = {
  common: 'Обычный', rare: 'Редкий', epic: 'Эпический', mythical: 'Мифический', legendary: 'Легендарный',
};

// ─── Forge sub-pages ──────────────────────────────────────────────────────────

function ForgeTab({ items, sets, busy, message, onApplySet, onCreateSet, onDeleteSet, onSelectItems, onItemDetail }: {
  items: ForgeItem[]; sets: ForgeSet[];
  busy: boolean; message: string | null;
  onApplySet: (id: string) => void; onCreateSet: () => void; onDeleteSet: (id: string) => void;
  onSelectItems: (id: string) => void; onItemDetail: (id: string) => void;
}) {
  const activeItems = items.filter(i => i.is_active);
  const activeSet = sets.find(s => s.is_active) ?? null;
  const orderedSets = [...sets].sort((a, b) => Number(b.is_active) - Number(a.is_active));
  const bonuses: Record<string, number> = {};
  for (const item of activeItems) {
    for (const p of item.properties ?? []) {
      bonuses[p.type] = (bonuses[p.type] ?? 0) + p.value;
    }
  }
  const bonusEntries = Object.entries(bonuses);

  return (
    <div className="px-[14px] pt-3 flex flex-col gap-3 page-enter">
      <div className="card overflow-hidden relative" style={{ background: 'linear-gradient(135deg, rgba(var(--c-blue-rgb),0.14), rgba(var(--c-purple-rgb),0.08))', borderColor: 'rgba(var(--c-blue-rgb),0.25)' }}>
        <div className="absolute -right-8 -top-10 w-28 h-28 rounded-full" style={{ background: 'rgba(var(--c-blue-rgb),0.12)' }} />
        <div className="relative flex items-start justify-between gap-3">
          <div>
            <p className="m-0 text-[11px] font-extrabold uppercase tracking-[1px] text-tg-hint">Активная сборка</p>
            <p className="mt-1 mb-0 text-[18px] font-extrabold leading-tight">{activeSet ? `${activeSet.icon} ${activeSet.name}` : 'Ручной набор'}</p>
            <p className="mt-[4px] mb-0 text-xs text-tg-hint">{activeItems.length}/3 предмета дают бонусы прямо сейчас</p>
          </div>
          <div className="grid grid-cols-3 gap-[6px] shrink-0">
            {[0, 1, 2].map(index => {
              const item = activeItems[index];
              return (
                <button
                  key={index}
                  onClick={() => item && onItemDetail(item.id)}
                  disabled={!item}
                  className="w-11 h-11 rounded-2xl border-none grid place-items-center text-[22px] disabled:opacity-70"
                  style={{ background: item ? 'rgba(var(--c-green-rgb),0.16)' : 'rgba(var(--tg-theme-hint-color-rgb,128,128,128),0.08)', color: 'var(--tg-theme-text-color)' }}
                >
                  {item ? forgeItemIcon(item) : '＋'}
                </button>
              );
            })}
          </div>
        </div>

        <div className="relative mt-3 grid grid-cols-2 gap-2">
          <div className="rounded-2xl px-3 py-2" style={{ background: 'rgba(var(--c-green-rgb),0.10)' }}>
            <p className="m-0 text-[10px] uppercase tracking-[0.8px] text-tg-hint">Бонусов</p>
            <p className="mt-[2px] mb-0 text-lg font-extrabold">{bonusEntries.length}</p>
          </div>
          <div className="rounded-2xl px-3 py-2" style={{ background: 'rgba(var(--c-gold-rgb),0.10)' }}>
            <p className="m-0 text-[10px] uppercase tracking-[0.8px] text-tg-hint">Предметов</p>
            <p className="mt-[2px] mb-0 text-lg font-extrabold">{items.length}</p>
          </div>
        </div>

        {bonusEntries.length > 0 && (
          <div className="relative mt-3 flex flex-wrap gap-[6px]">
            {bonusEntries.map(([type, val]) => (
              <span key={type} className="px-[9px] py-[5px] rounded-full text-[12px] font-semibold" style={{ background: 'rgba(var(--c-green-rgb),0.12)', color: 'var(--c-green)' }}>
                {PROP_ICON[type] ?? '✨'} {PROP_LABEL[type] ?? type}: {val}
              </span>
            ))}
          </div>
        )}
      </div>

      {message && (
        <div className="rounded-2xl px-3 py-2 text-[13px] font-semibold" style={{ background: 'rgba(var(--c-orange-rgb),0.12)', color: 'var(--c-orange)' }}>
          {message}
        </div>
      )}

      <div className="card flex flex-col gap-2" style={{ borderColor: 'rgba(var(--c-gold-rgb),0.22)' }}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl grid place-items-center text-xl" style={{ background: 'rgba(var(--c-gold-rgb),0.14)' }}>✨</div>
          <div className="flex-1 min-w-0">
            <p className="m-0 font-bold text-sm">Следующее действие</p>
            <p className="mt-[2px] mb-0 text-xs text-tg-hint">
              {items.length === 0 ? 'Создай предметы в магазине, потом собери из них сет.' : sets.length === 0 ? 'Создай первый сет и выбери до 3 предметов.' : activeSet ? 'Текущий сет можно быстро настроить или заменить.' : 'Примени готовый сет, чтобы включить его бонусы.'}
            </p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <button onClick={onCreateSet} disabled={busy || items.length === 0} className="py-[10px] rounded-xl border-none font-bold text-[13px] disabled:opacity-45" style={{ background: 'rgba(var(--c-blue-rgb),0.16)', color: 'var(--c-blue)' }}>
            + Новый сет
          </button>
          <button onClick={() => activeSet ? onSelectItems(activeSet.id) : orderedSets[0] && onApplySet(orderedSets[0].id)} disabled={busy || orderedSets.length === 0} className="py-[10px] rounded-xl border-none font-bold text-[13px] disabled:opacity-45" style={{ background: 'rgba(var(--c-green-rgb),0.16)', color: 'var(--c-green)' }}>
            {activeSet ? 'Настроить' : 'Применить'}
          </button>
        </div>
      </div>

      <div className="flex justify-between items-end">
        <div>
          <p className="m-0 font-bold text-[15px]">Сеты</p>
          <p className="mt-[2px] mb-0 text-xs text-tg-hint">Переключай сборки одним нажатием</p>
        </div>
        <span className="text-xs text-tg-hint">{sets.length} шт.</span>
      </div>

      {orderedSets.length === 0 ? (
        <div className="card text-center py-6">
          <p className="m-0 text-[34px]">⚒️</p>
          <p className="mt-2 mb-0 font-bold text-sm">Сетов пока нет</p>
          <p className="mt-[4px] mb-3 text-xs text-tg-hint">Создай сет, чтобы быстро включать нужные бонусы.</p>
          <button onClick={onCreateSet} disabled={busy || items.length === 0} className="px-4 py-[10px] rounded-xl border-none font-bold text-[13px] disabled:opacity-45" style={{ background: 'var(--tg-theme-button-color)', color: 'var(--tg-theme-button-text-color)' }}>
            Создать сет
          </button>
        </div>
      ) : orderedSets.map(itemSet => {
        const setItems = items.filter(i => itemSet.item_ids.includes(i.id));
        return (
          <div key={itemSet.id} className="card flex flex-col gap-3" style={{
            border: itemSet.is_active ? '1px solid rgba(var(--c-blue-rgb),0.45)' : undefined,
            background: itemSet.is_active ? 'rgba(var(--c-blue-rgb),0.08)' : undefined,
          }}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm truncate">{itemSet.icon} {itemSet.name}</span>
                  {itemSet.is_active && <span className="px-[7px] py-[2px] rounded-full text-[10px] font-bold" style={{ background: 'rgba(var(--c-blue-rgb),0.16)', color: 'var(--c-blue)' }}>Активен</span>}
                </div>
                <p className="mt-[3px] mb-0 text-xs text-tg-hint">{setItems.length}/3 слота заполнено</p>
              </div>
              <button onClick={() => onDeleteSet(itemSet.id)} disabled={busy} className="w-8 h-8 rounded-xl border-none disabled:opacity-45" style={{ background: 'rgba(var(--c-red-rgb),0.12)', color: 'var(--c-red)' }}>×</button>
            </div>

            <div className="grid grid-cols-3 gap-2">
              {[0, 1, 2].map(index => {
                const item = setItems[index];
                return (
                  <button key={index} onClick={() => item ? onItemDetail(item.id) : onSelectItems(itemSet.id)} className="min-h-[62px] rounded-2xl border-none flex flex-col items-center justify-center gap-[3px]" style={{ background: item ? 'rgba(var(--c-purple-rgb),0.10)' : 'var(--surface-subtle)', color: 'var(--tg-theme-text-color)' }}>
                    <span className="text-[22px]">{item ? forgeItemIcon(item) : '＋'}</span>
                    <span className="max-w-full px-1 text-[10px] text-tg-hint truncate">{item ? item.name : 'Пусто'}</span>
                  </button>
                );
              })}
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button onClick={() => onSelectItems(itemSet.id)} disabled={busy} className="py-[10px] rounded-xl border-none font-bold text-[13px] disabled:opacity-45" style={{ background: 'rgba(var(--c-gold-rgb),0.14)', color: 'var(--c-gold)' }}>Изменить</button>
              <button onClick={() => onApplySet(itemSet.id)} disabled={busy || setItems.length === 0 || itemSet.is_active} className="py-[10px] rounded-xl border-none font-bold text-[13px] disabled:opacity-45" style={{ background: 'rgba(var(--c-green-rgb),0.14)', color: 'var(--c-green)' }}>{itemSet.is_active ? 'Уже активен' : 'Применить'}</button>
            </div>
          </div>
        );
      })}

      <div className="flex justify-between items-end mt-1">
        <div>
          <p className="m-0 font-bold text-[15px]">Инвентарь</p>
          <p className="mt-[2px] mb-0 text-xs text-tg-hint">Нажми на предмет, чтобы посмотреть свойства</p>
        </div>
        <span className="text-xs text-tg-hint">{items.length} шт.</span>
      </div>

      {items.length === 0 ? (
        <div className="card text-center py-7">
          <p className="m-0 text-[36px]">🧰</p>
          <p className="mt-2 mb-0 font-bold text-sm">Инвентарь пуст</p>
          <p className="mt-[4px] mb-0 text-xs text-tg-hint">Открой Магазин → Кузница и создай первый предмет.</p>
        </div>
      ) : items.map(item => {
        const color = RARITY_COLOR[item.rarity] ?? 'var(--tg-theme-hint-color)';
        return (
          <button key={item.id} onClick={() => onItemDetail(item.id)} className="card flex items-center gap-3 text-left border-none cursor-pointer">
            <span className="w-11 h-11 rounded-2xl grid place-items-center text-[25px] shrink-0" style={{ background: `color-mix(in srgb, ${color} 12%, transparent)` }}>{forgeItemIcon(item)}</span>
            <span className="flex-1 min-w-0">
              <span className="flex items-center gap-[6px] min-w-0">
                <span className="font-bold text-sm truncate">{item.name}</span>
                {item.is_active && <span className="shrink-0 text-[10px] font-bold" style={{ color: 'var(--c-green)' }}>ON</span>}
              </span>
              <span className="block mt-[2px] text-xs text-tg-hint truncate">Ур. {item.level} · {itemBonusSummary(item)}</span>
            </span>
            <span className="text-[11px] px-[7px] py-[3px] rounded-full font-semibold shrink-0" style={{ background: `color-mix(in srgb, ${color} 13%, transparent)`, color }}>
              {RARITY_LABEL[item.rarity] ?? item.rarity}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function ItemSelectPage({ items, setId: _setId, selectedIds, onSelect, onApply, onBack }: {
  items: ForgeItem[]; setId: string; selectedIds: string[];
  onSelect: (id: string) => void; onApply: () => void; onBack: () => void;
}) {
  const selectedItems = selectedIds.map(id => items.find(item => item.id === id)).filter((item): item is ForgeItem => Boolean(item));
  return (
    <div className="page-content-safe">
      <div className="sticky z-10 bg-tg-bg px-[14px] pt-3 pb-[10px] border-b" style={{ top: 0, borderColor: 'var(--surface-overlay-border)' }}>
        <div className="flex items-center justify-between gap-3">
          <button onClick={onBack} className="w-9 h-9 rounded-xl border-none bg-[var(--surface-subtle)] text-tg-text text-[18px]">✕</button>
          <div className="text-center min-w-0">
            <p className="m-0 font-bold text-[15px]">Настрой сет</p>
            <p className="mt-[2px] mb-0 text-[11px] text-tg-hint">Выбрано {selectedIds.length}/3</p>
          </div>
          <button onClick={onApply} className="px-[14px] py-[9px] rounded-xl border-none bg-[var(--c-green)] text-[var(--tg-theme-button-text-color)] font-bold text-[13px]">Сохранить</button>
        </div>

        <div className="mt-3 grid grid-cols-3 gap-2">
          {[0, 1, 2].map(index => {
            const item = selectedItems[index];
            return (
              <div key={index} className="min-h-[58px] rounded-2xl flex flex-col items-center justify-center gap-[2px]" style={{ background: item ? 'rgba(var(--c-green-rgb),0.12)' : 'var(--surface-subtle)' }}>
                <span className="text-[22px]">{item ? forgeItemIcon(item) : '＋'}</span>
                <span className="max-w-full px-1 text-[10px] text-tg-hint truncate">{item ? item.name : 'Слот'}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="px-[14px] pt-3 flex flex-col gap-[10px]">
        {items.length === 0 && <div className="card text-center py-7"><p className="m-0 text-[34px]">🧰</p><p className="mt-2 mb-0 text-tg-hint text-sm">Нет предметов для выбора.</p></div>}
        {items.map(item => {
          const sel = selectedIds.includes(item.id);
          const color = RARITY_COLOR[item.rarity] ?? 'var(--tg-theme-hint-color)';
          return (
            <div key={item.id} onClick={() => onSelect(item.id)}
              className="card flex items-center gap-3 cursor-pointer"
              style={{ border: sel ? `1px solid ${color}` : undefined, background: sel ? `color-mix(in srgb, ${color} 9%, transparent)` : undefined }}>
              <span className="w-11 h-11 rounded-2xl grid place-items-center text-[25px] shrink-0" style={{ background: `color-mix(in srgb, ${color} 12%, transparent)` }}>{forgeItemIcon(item)}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-[6px] min-w-0">
                  <span className="font-bold text-sm truncate">{item.name}</span>
                  <span className="text-[11px] px-[6px] py-[1px] rounded" style={{ background: `color-mix(in srgb, ${RARITY_COLOR[item.rarity] ?? 'var(--tg-theme-hint-color)'} 13%, transparent)`, color: RARITY_COLOR[item.rarity] ?? 'var(--tg-theme-hint-color)' }}>
                    {RARITY_LABEL[item.rarity] ?? item.rarity}
                  </span>
                  {item.is_active && <span className="text-[10px] font-bold text-[var(--c-green)]">ON</span>}
                </div>
                <p className="mt-[2px] mb-0 text-xs text-tg-hint truncate">Ур. {item.level} · {itemBonusSummary(item)}</p>
              </div>
              <span className="w-7 h-7 rounded-full grid place-items-center text-sm font-bold" style={{ background: sel ? 'var(--c-green)' : 'var(--surface-subtle)', color: sel ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)' }}>
                {sel ? '✓' : '+'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ItemDetailPage({ item, onActivate, onSell, onBack }: {
  item: ForgeItem; onActivate: () => void; onSell: () => void; onBack: () => void;
}) {
  const color = RARITY_COLOR[item.rarity] ?? 'var(--tg-theme-hint-color)';
  return (
    <div className="page-content-safe">
      <div className="sticky z-10 bg-tg-bg px-[14px] pt-3 pb-[10px] flex items-center justify-between border-b" style={{ top: 0, borderColor: 'var(--surface-overlay-border)' }}>
        <button onClick={onBack} className="w-9 h-9 rounded-xl border-none bg-[var(--surface-subtle)] text-tg-text text-[18px]">✕</button>
        <span className="font-bold text-[15px]">Предмет</span>
        <span className="w-9" />
      </div>
      <div className="p-[14px] flex flex-col gap-[10px]">
        <div className="card text-center overflow-hidden relative" style={{ borderColor: `color-mix(in srgb, ${color} 35%, transparent)`, background: `color-mix(in srgb, ${color} 8%, transparent)` }}>
          <div className="absolute -right-10 -top-10 w-28 h-28 rounded-full" style={{ background: `color-mix(in srgb, ${color} 12%, transparent)` }} />
          <div className="relative">
            <div className="mx-auto w-[74px] h-[74px] rounded-3xl grid place-items-center text-[40px]" style={{ background: `color-mix(in srgb, ${color} 15%, transparent)` }}>{forgeItemIcon(item)}</div>
            <p className="mt-3 mb-0 text-lg font-extrabold">{item.name}</p>
            <div className="mt-2 flex items-center justify-center gap-2 flex-wrap">
              <span className="px-[9px] py-[4px] rounded-full text-[11px] font-bold" style={{ background: `color-mix(in srgb, ${color} 15%, transparent)`, color }}>{RARITY_LABEL[item.rarity] ?? item.rarity}</span>
              <span className="px-[9px] py-[4px] rounded-full text-[11px] font-bold bg-[var(--surface-subtle)] text-tg-hint">Уровень {item.level}</span>
              {item.is_active && <span className="px-[9px] py-[4px] rounded-full text-[11px] font-bold" style={{ background: 'rgba(var(--c-green-rgb),0.14)', color: 'var(--c-green)' }}>Активен</span>}
            </div>
          </div>
        </div>

        <div className="card">
          <p className="m-0 mb-3 font-bold text-sm">Свойства</p>
          {(item.properties ?? []).length === 0 && <p className="m-0 text-[13px] text-tg-hint">У предмета нет свойств.</p>}
          {(item.properties ?? []).map((p, i) => (
            <div key={i} className="flex items-center justify-between gap-3 mb-2 rounded-xl px-3 py-2" style={{ background: 'var(--surface-subtle)' }}>
              <span className="text-[13px] text-tg-hint">{PROP_ICON[p.type] ?? '✨'} {PROP_LABEL[p.type] ?? p.label.split(' ').slice(0, -1).join(' ')}</span>
              <span className="text-[13px] text-[var(--c-green)] font-bold">{p.label.split(' ').pop()}</span>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <button onClick={onActivate} className="flex-1 py-3 rounded-[10px] border-none font-bold text-sm"
            style={{ background: item.is_active ? 'var(--surface-subtle)' : 'rgba(var(--c-green-rgb),0.15)', color: item.is_active ? 'var(--tg-theme-hint-color)' : 'var(--c-green)' }}>
            {item.is_active ? 'Деактивировать' : 'Активировать'}
          </button>
          <button onClick={onSell} className="flex-1 py-3 rounded-[10px] border-none bg-[rgba(var(--c-orange-rgb),0.15)] text-[var(--c-orange)] font-bold text-sm">Продать $80k</button>
        </div>
      </div>
    </div>
  );
}

// ─── ZooPage ──────────────────────────────────────────────────────────────────

type SubPage =
  | { type: 'expeditions' }
  | { type: 'forge_select'; setId: string; selectedIds: string[] }
  | { type: 'forge_item_detail'; itemId: string }
  | null;

const ZOO_TABS: { id: ZooTab; emoji: string; label: string; badge?: (gs: GameState) => number | null }[] = [
  { id: 'overview', emoji: '🏠', label: 'Обзор' },
  { id: 'forge',    emoji: '⚒️',  label: 'Кузня',  badge: gs => gs.forge_items.length > 0 ? gs.forge_items.length : null },
  { id: 'aviaries', emoji: '🏗️', label: 'Вольер', badge: gs => gs.sick_animals.length > 0 ? gs.sick_animals.length : null },
  { id: 'medals',   emoji: '🏅', label: 'Медали' },
];

export function ZooPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [tab, setTab] = useState<ZooTab>('overview');
  const [subPage, setSubPage] = useState<SubPage>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  function showMessage(text: string) {
    setMessage(text);
    window.setTimeout(() => setMessage(null), 3000);
  }

  async function runForgeAction(action: () => Promise<void>, fallback: string) {
    if (busy) return;
    setBusy(true);
    setMessage(null);
    try {
      await action();
      onRefresh();
    } catch (e) {
      showMessage(e instanceof Error ? e.message : fallback);
    } finally {
      setBusy(false);
    }
  }

  if (subPage?.type === 'expeditions') {
    return <ExpeditionPage onRefresh={onRefresh} onBack={() => setSubPage(null)} />;
  }

  if (subPage?.type === 'forge_select') {
    return (
      <ItemSelectPage
        items={gs.forge_items} setId={subPage.setId} selectedIds={subPage.selectedIds}
        onSelect={(id) => setSubPage(prev => {
          if (prev?.type !== 'forge_select') return prev;
          const ids = prev.selectedIds.includes(id)
            ? prev.selectedIds.filter(x => x !== id)
            : prev.selectedIds.length < 3 ? [...prev.selectedIds, id] : prev.selectedIds;
          return { ...prev, selectedIds: ids };
        })}
        onApply={() => void runForgeAction(async () => {
          await apiForgeUpdateSet(subPage.setId, subPage.selectedIds);
          setSubPage(null);
        }, 'Ошибка сохранения сета')} onBack={() => setSubPage(null)}
      />
    );
  }

  if (subPage?.type === 'forge_item_detail') {
    const item = gs.forge_items.find(i => i.id === subPage.itemId);
    if (item) return <ItemDetailPage item={item}
      onActivate={() => void runForgeAction(async () => {
        await apiForgeActivate(item.id);
        setSubPage(null);
      }, 'Ошибка активации предмета')}
      onSell={() => void runForgeAction(async () => {
        if (!(await tmaConfirm(`Продать «${item.name}» за $80k?`, 'Продать предмет?'))) return;
        await apiForgeSell(item.id);
        setSubPage(null);
      }, 'Ошибка продажи предмета')}
      onBack={() => setSubPage(null)} />;
  }

  const netPerMin = gs.income_rub_per_min - gs.expenses_rub_per_min;

  return (
    <div className="page-content-safe">
      {/* ── Hero Header ── */}
      <div className="relative overflow-hidden"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', paddingTop: '16px' }}>
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse at 20% -10%, rgba(var(--c-green-rgb),0.1) 0%, transparent 55%)' }} />

        {/* Profile row */}
        <div className="relative px-[14px] flex items-center gap-3 mb-3">
          <div className="w-11 h-11 rounded-full grid place-items-center text-[24px] shrink-0 relative"
            style={{ background: 'linear-gradient(135deg,rgba(var(--c-green-rgb),0.3),rgba(var(--c-blue-rgb),0.2))', border: '1.5px solid color-mix(in srgb, var(--tg-theme-hint-color) 30%, transparent)' }}>
            {gs.profile_emoji ?? '🦁'}
            <div className="absolute inset-0 rounded-full" style={{ boxShadow: '0 0 14px rgba(var(--c-green-rgb),0.3)' }} />
          </div>
          <div>
            <p className="m-0 text-lg font-extrabold leading-tight">{gs.nickname}</p>
            <p className="mt-[2px] mb-0 text-xs" style={{ color: 'var(--tg-theme-hint-color)' }}>С {formatDateShort(gs.registered_at)} г.</p>
          </div>
        </div>

        {/* Balance chips */}
        <div className="relative px-[14px] flex gap-[6px] mb-3 overflow-x-auto">
          {[
            { label: `₽ ${fmt(gs.rub)}`,   color: 'var(--c-green)' },
            { label: `$ ${fmt(gs.usd)}`,   color: 'var(--c-gold)' },
            { label: `🐾 ${gs.paw_coins}`, color: 'var(--c-purple)' },
          ].map(({ label, color }) => (
            <span key={label} className="px-3 py-[5px] rounded-[20px] text-[13px] font-bold whitespace-nowrap shrink-0"
              style={{ background: `color-mix(in srgb, ${color} 10%, transparent)`, color, border: `1px solid color-mix(in srgb, ${color} 16%, transparent)`, boxShadow: `0 0 8px color-mix(in srgb, ${color} 8%, transparent)` }}>
              {label}
            </span>
          ))}
        </div>

        {/* Income / Expenses row */}
        <div className="relative px-[14px] flex items-end">
          <div>
            <p className="m-0 text-[9px] font-bold tracking-[1px] uppercase" style={{ color: 'var(--tg-theme-hint-color)' }}>Чистый доход/мин</p>
            <p className={`mt-[3px] mb-0 text-[18px] font-extrabold tabular-nums ${netPerMin >= 0 ? 'income-glow' : 'expense-glow'}`}
              style={{ color: netPerMin >= 0 ? 'var(--c-green)' : 'var(--c-orange)' }}>
              {fmtMin(netPerMin)}₽
            </p>
          </div>
        </div>
      </div>

      {/* ── Section tabs ── */}
      <div
        className="flex mx-[14px] my-3 rounded-2xl p-1"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 18%, transparent)' }}
      >
        {ZOO_TABS.map(({ id, emoji, badge }) => {
          const isActive = tab === id;
          const badgeVal = badge?.(gs) ?? null;
          return (
            <button
              key={id}
              onClick={() => setTab(id)}
              className="flex-1 flex items-center justify-center py-[10px] rounded-xl border-none relative transition-all duration-200"
              style={{
                background: isActive ? 'color-mix(in srgb, var(--tg-theme-button-color) 15%, transparent)' : 'transparent',
                color: isActive ? 'var(--tg-theme-text-color)' : 'var(--tg-theme-hint-color)',
                boxShadow: isActive ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
              }}
            >
              <span className="text-[18px] leading-none">{emoji}</span>
              {badgeVal != null && (
                <span className="absolute top-[4px] right-[4px] bg-[var(--c-red)] text-[var(--tg-theme-button-text-color)] text-[9px] font-extrabold rounded-full min-w-[15px] h-[15px] flex items-center justify-center px-[3px]"
                  style={{ animation: 'badge-pop 0.3s ease' }}>
                  {badgeVal}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ── Tab content ── */}

      {tab === 'overview' && (
        <div className="px-[14px] pt-3 flex flex-col gap-3 page-enter">
          {gs.sick_animals.length > 0 && (
            <div className="rounded-2xl px-[14px] py-3 flex items-start gap-3"
              style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.35)' }}>
              <span className="text-xl">🤒</span>
              <p className="m-0 text-[13px] font-bold text-[var(--c-red-soft)]">
                {gs.sick_animals.length} животное больно! Штраф уже действует — открой ветеринара
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-2">
            <StatTile icon="🦁" label="Животных"    value={fmt(gs.animals.reduce((s, a) => s + a.quantity, 0))} accent="var(--c-green)" />
            <StatTile icon="🌿" label={`Видов (+${Math.round(gs.diversity_bonus_per_species * gs.species_count * 100)}%)`} value={String(gs.species_count)} accent="var(--c-cyan)" />
            <StatTile icon="🏗️" label="Мест всего"  value={fmt(gs.total_seats)} accent="var(--c-cyan)" />
            <StatTile icon="✅" label="Свободно"    value={fmt(gs.free_seats)}  accent="var(--c-gold)" />
          </div>

          {gs.clan && (
            <div className="card flex items-center gap-3" style={{ border: '1px solid rgba(90,200,250,0.2)' }}>
              <div className="icon-box" style={{ background: 'rgba(90,200,250,0.12)' }}>🏰</div>
              <div className="flex-1">
                <p className="m-0 font-bold text-sm">«{gs.clan.name}»</p>
                <p className="mt-[2px] mb-0 text-xs text-tg-hint">
                  Ур. {gs.clan.level} · {gs.clan.member_count} уч.{gs.clan.specialty ? ` · ${getClanSpecialtyLabel(gs.clan.specialty)}` : ''}
                </p>
              </div>
              <span className="text-base text-tg-hint">›</span>
            </div>
          )}

          <ExpeditionOverviewCard onOpen={() => setSubPage({ type: 'expeditions' })} />

          {gs.animals.filter(a => a.quantity > 0).length > 0 && (
            <div>
              <p className="m-0 mb-2 text-[11px] font-extrabold text-tg-hint tracking-[1px] uppercase">Мои животные</p>
              <div className="grid grid-cols-2 gap-2">
                {gs.animals.filter(a => a.quantity > 0).slice(0, 10).map(a => {
                  const def = ANIMALS.find(d => d.id === a.animal_id);
                  if (!def) return null;
                  return (
                    <div key={a.animal_id} className="card" style={{ padding: '10px 12px' }}>
                      <div className="flex items-center gap-[10px]">
                        <span className="text-[24px]">{def.emoji}</span>
                        <div className="min-w-0">
                          <p className="m-0 text-[13px] font-semibold truncate">{def.name}</p>
                          <p className="m-0 text-[11px] text-tg-hint">{fmt(a.quantity)} шт.</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'forge' && (
        <ForgeTab items={gs.forge_items} sets={gs.forge_sets}
          busy={busy}
          message={message}
          onApplySet={(setId) => void runForgeAction(async () => {
            await apiForgeApplySet(setId);
          }, 'Ошибка применения сета')}
          onCreateSet={() => void runForgeAction(async () => {
            const result = await apiForgeCreateSet([]);
            setSubPage({ type: 'forge_select', setId: result.set.id, selectedIds: [] });
          }, 'Ошибка создания сета')}
          onDeleteSet={(setId) => void runForgeAction(async () => {
            if (!(await tmaConfirm('Удалить этот сет? Предметы останутся у тебя.', 'Удалить сет?'))) return;
            await apiForgeDeleteSet(setId);
          }, 'Ошибка удаления сета')}
          onSelectItems={(setId) => {
            const itemSet = gs.forge_sets.find(s => s.id === setId);
            setSubPage({ type: 'forge_select', setId, selectedIds: [...(itemSet?.item_ids ?? [])] });
          }}
          onItemDetail={(itemId) => setSubPage({ type: 'forge_item_detail', itemId })}
        />
      )}

      {tab === 'aviaries' && (
        <div className="px-[14px] pt-3 flex flex-col gap-[10px] page-enter">
          {gs.sick_animals.length > 0 && (
            <div className="rounded-2xl px-[14px] py-3" style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.35)' }}>
              <p className="m-0 mb-[6px] font-bold text-[var(--c-red-soft)]">🤒 Больные животные</p>
              {gs.sick_animals.map(s => {
                const def = ANIMALS.find(d => d.id === s.animal_id);
                return (
                  <div key={s.animal_id} className="flex justify-between items-center mb-2">
                    <span className="text-[13px]">{def?.emoji ?? '🐾'} {def?.name ?? s.animal_id}</span>
                    <div className="flex gap-2 items-center">
                      <span className="text-xs text-[var(--c-red-soft)]">-{fmt(s.penalty_rub_per_min)}/мин</span>
                      <button className="px-[10px] py-1 rounded-lg border-none bg-[rgba(var(--c-green-rgb),0.15)] text-[var(--c-green)] text-xs font-semibold">Лечить 🐾</button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {gs.aviaries.map(av => (
            <div key={av.aviary_id} className="card flex justify-between items-center">
              <p className="m-0 font-semibold">🏗️ {av.aviary_id}</p>
              <span className="text-[13px] text-tg-hint">{av.count} шт.</span>
            </div>
          ))}
          {gs.aviaries.length === 0 && gs.sick_animals.length === 0 && (
            <div className="card text-center py-8">
              <p className="m-0 text-4xl mb-3">🏗️</p>
              <p className="m-0 text-tg-hint text-sm">Нет вольеров. Купи в магазине!</p>
            </div>
          )}
        </div>
      )}

      {tab === 'medals' && (
        <div className="px-[14px] pt-3 page-enter">
          <div className="card text-center py-10">
            <p className="m-0 text-[48px]" style={{ animation: 'float 3s ease-in-out infinite' }}>🏅</p>
            <p className="mt-3 mb-0 text-tg-hint">Раздел достижений скоро!</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Helper components ────────────────────────────────────────────────────────

function StatTile({ icon, value, label, accent }: { icon: string; value: string; label: string; accent: string }) {
  return (
    <div className="stat-tile">
      <div className="icon-box mb-2" style={{ background: `${accent}18` }}>
        <span>{icon}</span>
      </div>
      <p className="m-0 mb-[2px] text-[22px] font-extrabold leading-none">{value}</p>
      <p className="m-0 text-[11px] text-tg-hint leading-snug">{label}</p>
    </div>
  );
}
