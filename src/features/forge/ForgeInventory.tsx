import { useState } from 'react';
import type { ForgeItem, ForgeSet, PropertyKind } from '@/types';
import { PROPERTY_ICON, PROPERTY_SHORT } from '@/data/itemProperties';
import { fmt } from '@/utils/format';

function forgeItemIcon(item: ForgeItem): string {
  const first = item.properties?.[0]?.kind;
  return first ? (PROPERTY_ICON[first] ?? '✨') : '✨';
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

export function ForgeTab({ items, sets, busy, message, onApplySet, onCreateSet, onDeleteSet, onSelectItems, onItemDetail }: {
  items: ForgeItem[]; sets: ForgeSet[];
  busy: boolean; message: string | null;
  onApplySet: (id: string) => void; onCreateSet: (name?: string) => void; onDeleteSet: (id: string) => void;
  onSelectItems: (id: string) => void; onItemDetail: (id: string) => void;
}) {
  const [newSetName, setNewSetName] = useState('');
  const activeItems = items.filter(i => i.is_active);
  const activeSet = sets.find(s => s.is_active) ?? null;
  const orderedSets = [...sets].sort((a, b) => Number(b.is_active) - Number(a.is_active));
  // Mirrors `bonuses.load()` on the server, minus the caps: this is a summary, not a rule.
  const bonuses: Partial<Record<PropertyKind, number>> = {};
  for (const item of activeItems) {
    for (const p of item.properties ?? []) {
      bonuses[p.kind] = (bonuses[p.kind] ?? 0) + p.value;
    }
  }
  const bonusEntries = Object.entries(bonuses) as [PropertyKind, number][];

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
                {PROPERTY_ICON[type] ?? '✨'} {PROPERTY_SHORT[type] ?? type}: {val}
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
          <button onClick={() => { onCreateSet(newSetName.trim() || undefined); setNewSetName(''); }} disabled={busy || items.length === 0} className="py-[10px] rounded-xl border-none font-bold text-[13px] disabled:opacity-45" style={{ background: 'rgba(var(--c-blue-rgb),0.16)', color: 'var(--c-blue)' }}>
            + Новый сет
          </button>
          <button onClick={() => activeSet ? onSelectItems(activeSet.id) : orderedSets[0] && onApplySet(orderedSets[0].id)} disabled={busy || orderedSets.length === 0} className="py-[10px] rounded-xl border-none font-bold text-[13px] disabled:opacity-45" style={{ background: 'rgba(var(--c-green-rgb),0.16)', color: 'var(--c-green)' }}>
            {activeSet ? 'Настроить' : 'Применить'}
          </button>
        </div>
        <input
          value={newSetName}
          onChange={event => setNewSetName(event.target.value)}
          maxLength={32}
          placeholder="Название нового сета, например «Дуэли»"
          className="text-input text-[13px]"
          aria-label="Название нового сета"
        />
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
          <button onClick={() => onCreateSet()} disabled={busy || items.length === 0} className="px-4 py-[10px] rounded-xl border-none font-bold text-[13px] disabled:opacity-45" style={{ background: 'var(--tg-theme-button-color)', color: 'var(--tg-theme-button-text-color)' }}>
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

export function ItemSelectPage({ items, selectedIds, onSelect, onApply, onBack }: {
  items: ForgeItem[]; setId: string; selectedIds: string[];
  onSelect: (id: string) => void; onApply: () => void; onBack: () => void;
}) {
  const [previewItem, setPreviewItem] = useState<ForgeItem | null>(null);
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
              <button
                type="button"
                onClick={(event) => { event.stopPropagation(); setPreviewItem(item); }}
                className="shrink-0 px-2 py-1 rounded-lg border-none text-[10px] font-bold"
                style={{ background: 'rgba(var(--c-blue-rgb),0.14)', color: 'var(--c-blue)' }}
              >
                Подробнее
              </button>
              <span className="w-7 h-7 rounded-full grid place-items-center text-sm font-bold" style={{ background: sel ? 'var(--c-green)' : 'var(--surface-subtle)', color: sel ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)' }}>
                {sel ? '✓' : '+'}
              </span>
            </div>
          );
        })}
      </div>

      {previewItem && (
        <div className="modal-backdrop fixed inset-0 z-[300] flex items-end justify-center" onClick={() => setPreviewItem(null)} role="presentation">
          <section
            className="sheet-panel w-full max-w-[480px] rounded-t-3xl p-4"
            onClick={event => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label={`Свойства предмета ${previewItem.name}`}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.8px] text-tg-hint">Предмет в сете</p>
                <p className="m-0 mt-1 font-extrabold truncate">{previewItem.icon} {previewItem.name}</p>
              </div>
              <button type="button" onClick={() => setPreviewItem(null)} className="px-3 py-2 rounded-xl border-none bg-[var(--surface-subtle)] text-tg-text text-[12px] font-bold">Закрыть</button>
            </div>
            <div className="mt-3 flex flex-col gap-2">
              {(previewItem.properties ?? []).length > 0 ? previewItem.properties.map((property, index) => (
                <div key={`${property.kind}-${property.species_code ?? 'all'}-${index}`} className="rounded-xl px-3 py-2 surface-subtle flex items-center gap-2">
                  <span className="text-base">{PROPERTY_ICON[property.kind] ?? '✨'}</span>
                  <span className="text-[13px] text-tg-text">{property.label}</span>
                </div>
              )) : <p className="m-0 text-[13px] text-tg-hint">У предмета нет свойств.</p>}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export function ItemDetailPage({ item, onActivate, onSell, onBack }: {
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
              <span className="text-[13px] text-tg-hint">{PROPERTY_ICON[p.kind] ?? '✨'} {PROPERTY_SHORT[p.kind] ?? p.label.split(' ').slice(0, -1).join(' ')}</span>
              <span className="text-[13px] text-[var(--c-green)] font-bold">{p.label.split(' ').pop()}</span>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <button onClick={onActivate} className="flex-1 py-3 rounded-[10px] border-none font-bold text-sm"
            style={{ background: item.is_active ? 'var(--surface-subtle)' : 'rgba(var(--c-green-rgb),0.15)', color: item.is_active ? 'var(--tg-theme-hint-color)' : 'var(--c-green)' }}>
            {item.is_active ? 'Деактивировать' : 'Активировать'}
          </button>
          <button onClick={onSell} className="flex-1 py-3 rounded-[10px] border-none bg-[rgba(var(--c-orange-rgb),0.15)] text-[var(--c-orange)] font-bold text-sm">Продать ${fmt(item.sell_price_usd)}</button>
        </div>
      </div>
    </div>
  );
}
