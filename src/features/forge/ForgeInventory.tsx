import { memo, useMemo, useState } from 'react';
import type { ActiveItemBonus, ForgeItem, ForgeSet } from '@/types';
import { PROPERTY_ICON, PROPERTY_SHORT } from '@/data/itemProperties';

/** How the effective value reads next to its label: a percent for the percent kinds, a bare
 *  count for the flat kinds. The sign is carried by the unit, so a discount shows as "−50%". */
function bonusValueText(bonus: ActiveItemBonus): string {
  if (bonus.unit === 'percent_bonus') return `+${bonus.value}%`;
  if (bonus.unit === 'percent_discount') return `−${bonus.value}%`;
  return `+${bonus.value}`;
}

function forgeItemIcon(item: ForgeItem): string {
  const first = item.properties?.[0]?.kind;
  return first ? (PROPERTY_ICON[first] ?? '✨') : '✨';
}

const RARITY_COLOR: Record<string, string> = {
  common: 'var(--tg-theme-hint-color)', rare: 'var(--c-green)', epic: 'var(--c-purple)', mythical: 'var(--c-orange)', legendary: 'var(--c-gold)',
};
const RARITY_LABEL: Record<string, string> = {
  common: 'Обычный', rare: 'Редкий', epic: 'Эпический', mythical: 'Мифический', legendary: 'Легендарный',
};
const INVENTORY_PAGE_SIZE = 60;

const ForgeInventoryItem = memo(function ForgeInventoryItem({ item }: {
  item: ForgeItem;
}) {
  const color = RARITY_COLOR[item.rarity] ?? 'var(--tg-theme-hint-color)';
  return (
    <div className="card flex flex-col gap-2 text-left">
      <span className="w-full flex items-center gap-3">
        <span className="w-11 h-11 rounded-2xl grid place-items-center text-[25px] shrink-0" style={{ background: `color-mix(in srgb, ${color} 12%, transparent)` }}>{forgeItemIcon(item)}</span>
        <span className="flex-1 min-w-0">
          <span className="flex items-center gap-[6px] min-w-0">
            <span className="font-bold text-sm truncate">{item.name}</span>
            {item.is_active && <span className="shrink-0 text-[10px] font-bold" style={{ color: 'var(--c-green)' }}>ON</span>}
          </span>
          <span className="block mt-[2px] text-xs text-tg-hint">Ур. {item.level} · {item.properties?.length ?? 0} свойств</span>
        </span>
        <span className="text-[11px] px-[7px] py-[3px] rounded-full font-semibold shrink-0" style={{ background: `color-mix(in srgb, ${color} 13%, transparent)`, color }}>
          {RARITY_LABEL[item.rarity] ?? item.rarity}
        </span>
      </span>
      <span className="w-full flex flex-col gap-1 rounded-xl px-3 py-2 text-[12px]" style={{ background: 'var(--surface-subtle)' }}>
        {(item.properties ?? []).length > 0 ? item.properties.map((property, index) => (
          <span key={`${property.kind}-${property.species_code ?? 'all'}-${index}`} className="flex items-start gap-2 text-tg-hint">
            <span aria-hidden="true" className="shrink-0">{PROPERTY_ICON[property.kind] ?? '✨'}</span>
            <span className="leading-[1.35]">{property.label}</span>
          </span>
        )) : <span className="text-tg-hint">У предмета нет свойств</span>}
      </span>
    </div>
  );
});

export const ForgeTab = memo(function ForgeTab({ items, sets, bonuses, busy, message, onApplySet, onCreateSet, onRenameSet, onDeleteSet, onSelectItems }: {
  items: ForgeItem[]; sets: ForgeSet[]; bonuses: ActiveItemBonus[];
  busy: boolean; message: string | null;
  onApplySet: (id: string) => void; onCreateSet: (name?: string) => void; onRenameSet: (id: string, name: string) => void; onDeleteSet: (id: string) => void;
  onSelectItems: (id: string) => void;
}) {
  const [editingSetId, setEditingSetId] = useState<string | null>(null);
  const [editingSetName, setEditingSetName] = useState('');
  const [visibleItemCount, setVisibleItemCount] = useState(INVENTORY_PAGE_SIZE);
  const activeItems = useMemo(() => items.filter(i => i.is_active), [items]);
  const activeSet = useMemo(() => sets.find(s => s.is_active) ?? null, [sets]);
  const orderedSets = useMemo(() => [...sets].sort((a, b) => Number(b.is_active) - Number(a.is_active)), [sets]);
  const itemsById = useMemo(() => new Map(items.map(item => [item.id, item])), [items]);
  const visibleItems = items.slice(0, visibleItemCount);
  // The effective, already-capped totals from the server — the numbers the game actually
  // applies. Summing per-item labels here would overshoot the caps and mislead the player.
  const bonusEntries = bonuses;

  function startRename(itemSet: ForgeSet) {
    setEditingSetId(itemSet.id);
    setEditingSetName(itemSet.name);
  }

  function cancelRename() {
    setEditingSetId(null);
    setEditingSetName('');
  }

  function saveRename() {
    if (!editingSetId || !editingSetName.trim() || busy) return;
    onRenameSet(editingSetId, editingSetName.trim());
    cancelRename();
  }

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
                  onClick={() => activeSet && onSelectItems(activeSet.id)}
                  disabled={!item || !activeSet}
                  aria-label={item ? `Изменить сет, предмет ${item.name}` : 'Пустой слот'}
                  className="w-11 h-11 rounded-2xl border-none grid place-items-center text-[22px] disabled:opacity-70 disabled:cursor-default"
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
          <>
            <div className="relative mt-3 flex flex-wrap gap-[6px]">
              {bonusEntries.map((bonus, index) => (
                <span key={`${bonus.kind}-${bonus.species_code ?? 'all'}-${index}`} className="px-[9px] py-[5px] rounded-full text-[12px] font-semibold inline-flex items-center gap-[5px]" style={{ background: 'rgba(var(--c-green-rgb),0.12)', color: 'var(--c-green)' }}>
                  {PROPERTY_ICON[bonus.kind] ?? '✨'} {PROPERTY_SHORT[bonus.kind] ?? bonus.kind}: {bonusValueText(bonus)}
                  {bonus.capped && <span className="px-[5px] py-px rounded-full text-[9px] font-bold uppercase tracking-[0.4px]" style={{ background: 'rgba(var(--c-orange-rgb),0.18)', color: 'var(--c-orange)' }}>макс.</span>}
                </span>
              ))}
            </div>
            <p className="relative mt-2 mb-0 text-[10px] text-tg-hint">Итог по активным предметам — уже с учётом лимитов. «Макс.» значит, что бонус упёрся в потолок.</p>
          </>
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
        <div>
          <button type="button" onClick={() => onCreateSet()} disabled={busy || items.length === 0} className="w-full py-[10px] rounded-xl border-none font-bold text-[13px] disabled:opacity-45" style={{ background: 'rgba(var(--c-blue-rgb),0.16)', color: 'var(--c-blue)' }}>
            + Новый сет
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
          <button onClick={() => onCreateSet()} disabled={busy || items.length === 0} className="px-4 py-[10px] rounded-xl border-none font-bold text-[13px] disabled:opacity-45" style={{ background: 'var(--tg-theme-button-color)', color: 'var(--tg-theme-button-text-color)' }}>
            Создать сет
          </button>
        </div>
      ) : orderedSets.map(itemSet => {
        const setItems = itemSet.item_ids
          .map(itemId => itemsById.get(itemId))
          .filter((item): item is ForgeItem => Boolean(item));
        return (
          <div key={itemSet.id} className="card flex flex-col gap-3" style={{
            border: itemSet.is_active ? '1px solid rgba(var(--c-blue-rgb),0.45)' : undefined,
            background: itemSet.is_active ? 'rgba(var(--c-blue-rgb),0.08)' : undefined,
          }}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                {editingSetId === itemSet.id ? (
                  <div className="flex items-center gap-1">
                    <input
                      autoFocus
                      value={editingSetName}
                      onChange={event => setEditingSetName(event.target.value.slice(0, 32))}
                      onKeyDown={event => {
                        if (event.key === 'Enter') saveRename();
                        if (event.key === 'Escape') cancelRename();
                      }}
                      maxLength={32}
                      className="text-input min-w-0 flex-1 text-[13px]"
                      aria-label={`Новое название сета ${itemSet.name}`}
                    />
                    <button type="button" onClick={saveRename} disabled={busy || !editingSetName.trim()} aria-label="Сохранить название сета" className="min-w-11 min-h-11 rounded-xl border-none text-[17px] font-bold disabled:opacity-45" style={{ background: 'rgba(var(--c-green-rgb),0.14)', color: 'var(--c-green)' }}>✓</button>
                    <button type="button" onClick={cancelRename} disabled={busy} aria-label="Отменить переименование сета" className="min-w-11 min-h-11 rounded-xl border-none text-[17px] font-bold disabled:opacity-45" style={{ background: 'var(--surface-subtle)', color: 'var(--tg-theme-hint-color)' }}>×</button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-bold text-sm truncate">{itemSet.icon} {itemSet.name}</span>
                    <button type="button" onClick={() => startRename(itemSet)} disabled={busy} aria-label={`Переименовать сет ${itemSet.name}`} title="Переименовать сет" className="w-8 h-8 min-w-8 min-h-8 rounded-xl border-none grid place-items-center leading-none shrink-0 disabled:opacity-45" style={{ background: 'rgba(var(--c-gold-rgb),0.16)', color: 'var(--c-gold)', fontFamily: '"Apple Color Emoji", "Segoe UI Emoji", sans-serif', fontSize: '18px', lineHeight: 1 }}>✏️</button>
                    {itemSet.is_active && <span className="shrink-0 px-[7px] py-[2px] rounded-full text-[10px] font-bold" style={{ background: 'rgba(var(--c-blue-rgb),0.16)', color: 'var(--c-blue)' }}>Активен</span>}
                  </div>
                )}
                <p className="mt-[3px] mb-0 text-xs text-tg-hint">{setItems.length}/3 слота заполнено</p>
              </div>
              <button onClick={() => onDeleteSet(itemSet.id)} disabled={busy} className="w-8 h-8 rounded-xl border-none disabled:opacity-45" style={{ background: 'rgba(var(--c-red-rgb),0.12)', color: 'var(--c-red)' }}>×</button>
            </div>

            <div className="grid grid-cols-3 gap-2">
              {[0, 1, 2].map(index => {
                const item = setItems[index];
                return (
                  <button key={index} onClick={() => onSelectItems(itemSet.id)} className="min-h-[62px] rounded-2xl border-none flex flex-col items-center justify-center gap-[3px]" style={{ background: item ? 'rgba(var(--c-purple-rgb),0.10)' : 'var(--surface-subtle)', color: 'var(--tg-theme-text-color)' }}>
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
          <p className="mt-[2px] mb-0 text-xs text-tg-hint">Свойства предметов показаны сразу</p>
        </div>
        <span className="text-xs text-tg-hint">{items.length} шт.</span>
      </div>

      {items.length === 0 ? (
        <div className="card text-center py-7">
          <p className="m-0 text-[36px]">🧰</p>
          <p className="mt-2 mb-0 font-bold text-sm">Инвентарь пуст</p>
          <p className="mt-[4px] mb-0 text-xs text-tg-hint">Открой Магазин → Кузница и создай первый предмет.</p>
        </div>
      ) : visibleItems.map(item => <ForgeInventoryItem key={item.id} item={item} />)}

      {visibleItemCount < items.length && (
        <button
          type="button"
          onClick={() => setVisibleItemCount(count => Math.min(count + INVENTORY_PAGE_SIZE, items.length))}
          className="w-full rounded-2xl border-none py-3 text-[13px] font-extrabold cursor-pointer"
          style={{ background: 'var(--surface-subtle)', color: 'var(--c-blue)' }}
        >
          Показать ещё {Math.min(INVENTORY_PAGE_SIZE, items.length - visibleItemCount)} из {items.length - visibleItemCount}
        </button>
      )}
    </div>
  );
});

export function ItemSelectPage({ items, selectedIds, onSelect, onApply, onBack }: {
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
              className="card flex flex-col items-start gap-2 cursor-pointer"
              style={{ border: sel ? `1px solid ${color}` : undefined, background: sel ? `color-mix(in srgb, ${color} 9%, transparent)` : undefined }}>
              <div className="w-full flex items-center gap-3">
                <span className="w-11 h-11 rounded-2xl grid place-items-center text-[25px] shrink-0" style={{ background: `color-mix(in srgb, ${color} 12%, transparent)` }}>{forgeItemIcon(item)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-[6px] min-w-0">
                    <span className="font-bold text-sm truncate">{item.name}</span>
                    <span className="text-[11px] px-[6px] py-[1px] rounded" style={{ background: `color-mix(in srgb, ${RARITY_COLOR[item.rarity] ?? 'var(--tg-theme-hint-color)'} 13%, transparent)`, color: RARITY_COLOR[item.rarity] ?? 'var(--tg-theme-hint-color)' }}>
                      {RARITY_LABEL[item.rarity] ?? item.rarity}
                    </span>
                    {item.is_active && <span className="text-[10px] font-bold text-[var(--c-green)]">ON</span>}
                  </div>
                  <p className="mt-[2px] mb-0 text-xs text-tg-hint">Ур. {item.level} · {item.properties?.length ?? 0} свойств</p>
                </div>
                <span className="w-8 h-8 rounded-full grid place-items-center text-sm font-bold shrink-0" style={{ background: sel ? 'var(--c-green)' : 'var(--surface-subtle)', color: sel ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)' }}>
                  {sel ? '✓' : '+'}
                </span>
              </div>
              <div className="w-full flex flex-col gap-1 rounded-xl px-3 py-2 text-[12px]" style={{ background: 'var(--surface-subtle)' }}>
                {(item.properties ?? []).length > 0 ? item.properties.map((property, index) => (
                  <div key={`${property.kind}-${property.species_code ?? 'all'}-${index}`} className="flex items-start gap-2 text-tg-hint">
                    <span aria-hidden="true" className="shrink-0">{PROPERTY_ICON[property.kind] ?? '✨'}</span>
                    <span className="leading-[1.35]">{property.label}</span>
                  </div>
                )) : <span className="text-tg-hint">У предмета нет свойств</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
