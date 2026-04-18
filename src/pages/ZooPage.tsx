import { useState } from 'react';
import { fmt, fmtMin, formatDateShort } from '../utils/format';
import type { GameState, ForgeItem, ForgeSet } from '../types';
import { ANIMALS } from '../data/animals';
import { ExpeditionOverviewCard, ExpeditionPage } from './ExpeditionPage';

type ZooTab = 'overview' | 'forge' | 'aviaries' | 'medals';

const FORGE_ICON: Record<string, string> = {
  bank: '🔄', income: '📈', game: '🧠', bonus: '🎲',
  aviary: '🔗', discount: '📉', agility: '⚡', luck: '🍀',
};
function forgeItemIcon(item: ForgeItem): string {
  for (const key of Object.keys(FORGE_ICON)) {
    if (item.item_type.includes(key)) return FORGE_ICON[key];
  }
  return '✨';
}

const RARITY_COLOR: Record<string, string> = {
  common: '#8f95ab', rare: '#34c759', epic: '#bf5af2', mythic: '#ff6b3d',
};

// ─── Forge sub-pages ──────────────────────────────────────────────────────────

function ForgeTab({ items, sets, onApplySet, onSelectItems }: {
  items: ForgeItem[]; sets: ForgeSet[];
  onApplySet: (id: string) => void; onSelectItems: (id: string) => void;
}) {
  const activeItems = items.filter(i => i.is_active);
  const bonuses: Record<string, number> = {};
  for (const item of activeItems) bonuses[item.item_type] = (bonuses[item.item_type] ?? 0) + item.effect_value;

  return (
    <div className="px-[14px] pt-3 flex flex-col gap-3 page-enter">
      <div className="card">
        <p className="m-0 mb-[10px] font-bold text-[15px]">Суммарные бонусы активных предметов:</p>
        {Object.entries(bonuses).length === 0
          ? <p className="m-0 text-tg-hint text-[13px]">Нет активных предметов</p>
          : Object.entries(bonuses).map(([type, val]) => (
            <div key={type} className="flex justify-between mb-1">
              <span className="text-[13px] text-tg-hint">{activeItems.find(i => i.item_type === type)?.name ?? type}</span>
              <span className="text-[13px] text-[#34c759] font-bold">+{val}</span>
            </div>
          ))}
        <div className="mt-2 pt-2 border-t border-white/[0.08]">
          <span className="text-[13px] text-tg-hint">Активных предметов </span>
          <span className="text-[13px] font-bold">{activeItems.length} / {Math.min(items.length, 3)}</span>
        </div>
      </div>

      <div className="flex justify-between items-center">
        <p className="m-0 font-bold text-[15px]">Сеты предметов</p>
        <button className="px-3 py-[5px] rounded-lg border-none bg-[rgba(10,132,255,0.15)] text-[#0a84ff] text-[13px] font-semibold">+ Добавить</button>
      </div>
      <p className="m-0 -mt-2 text-xs text-tg-hint">Выбери до 3 предметов для каждого слота и переключай наборы одним нажатием.</p>

      {sets.map(s => {
        const setItems = items.filter(i => s.item_ids.includes(i.id));
        return (
          <div key={s.id} className="card" style={{
            border: s.is_active ? '1px solid rgba(10,132,255,0.4)' : undefined,
            background: s.is_active ? 'rgba(10,132,255,0.07)' : undefined,
          }}>
            <div className="flex items-center justify-between mb-[6px]">
              <div>
                <span className="font-bold text-sm">{s.icon} {s.name} 🔨 🗑️</span>
                {s.is_active
                  ? <span className="ml-2 text-[11px] text-[#0a84ff]">Сейчас активен</span>
                  : <p className="mt-[2px] mb-0 text-[11px] text-tg-hint">{setItems.length} предмет{setItems.length === 1 ? '' : 'а'} в слоте</p>}
              </div>
              <div className="flex gap-[6px]">{setItems.slice(0, 3).map(i => <span key={i.id} className="text-lg">{forgeItemIcon(i)}</span>)}</div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => onSelectItems(s.id)} className="flex-1 py-2 rounded-lg border-none bg-[rgba(255,214,10,0.15)] text-[#ffd60a] text-[13px] font-semibold">Выбрать предметы</button>
              <button onClick={() => onApplySet(s.id)} className="flex-1 py-2 rounded-lg border-none bg-[rgba(52,199,89,0.15)] text-[#34c759] text-[13px] font-semibold">Применить</button>
            </div>
          </div>
        );
      })}
      {sets.length === 0 && <div className="card text-center"><p className="m-0 text-tg-hint">Нет сетов. Нажми «+ Добавить»</p></div>}
    </div>
  );
}

function ItemSelectPage({ items, setId: _setId, selectedIds, onSelect, onApply, onBack }: {
  items: ForgeItem[]; setId: string; selectedIds: string[];
  onSelect: (id: string) => void; onApply: () => void; onBack: () => void;
}) {
  return (
    <div className="page-content-safe">
      <div className="sticky z-10 bg-tg-bg px-[14px] pt-3 pb-[10px] flex items-center justify-between border-b border-white/[0.07]" style={{ top: 0 }}>
        <button onClick={onBack} className="bg-transparent border-none text-white text-[22px]">✕</button>
        <span className="font-bold text-[15px]">Выбрать предметы</span>
        <button onClick={onApply} className="px-[14px] py-[7px] rounded-lg border-none bg-[#34c759] text-white font-bold text-[13px]">Применить ✓</button>
      </div>
      <div className="px-[14px] pt-3 flex flex-col gap-[10px]">
        {items.map(item => {
          const sel = selectedIds.includes(item.id);
          return (
            <div key={item.id} onClick={() => onSelect(item.id)}
              className={`card flex items-center gap-3 cursor-pointer ${sel ? 'card-rare' : ''}`}
              style={sel ? { border: `1px solid ${RARITY_COLOR[item.rarity] ?? '#34c759'}` } : undefined}>
              <span className="text-[26px] shrink-0">{forgeItemIcon(item)}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-[6px]">
                  <span className="font-semibold text-sm">{item.name}</span>
                  <span className="text-[11px] px-[6px] py-[1px] rounded" style={{ background: `${RARITY_COLOR[item.rarity] ?? '#8f95ab'}22`, color: RARITY_COLOR[item.rarity] ?? '#8f95ab' }}>
                    {item.rarity === 'rare' ? 'Редкий' : item.rarity === 'epic' ? 'Эпический' : item.rarity === 'mythic' ? 'Мифический' : 'Обычный'}
                  </span>
                  {item.is_active && <span className="text-[11px] text-[#34c759]">АКТИВЕН</span>}
                </div>
                <p className="mt-[2px] mb-0 text-xs text-tg-hint">Уровень {item.level} · {item.sv} св-в</p>
              </div>
              <span className="text-base text-tg-hint">▼</span>
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
  return (
    <div className="page-content-safe">
      <div className="sticky z-10 bg-tg-bg px-[14px] pt-3 pb-[10px] flex items-center justify-between border-b border-white/[0.07]" style={{ top: 0 }}>
        <button onClick={onBack} className="bg-transparent border-none text-white text-[22px]">✕</button>
        <span className="font-bold text-[15px]">
          {item.name} · <span style={{ color: RARITY_COLOR[item.rarity] }}>{item.rarity === 'epic' ? 'Эпический' : item.rarity === 'rare' ? 'Редкий' : 'Обычный'}</span>
        </span>
        <div />
      </div>
      <div className="p-[14px] flex flex-col gap-[10px]">
        <div className="card">
          <p className="m-0 mb-1 text-[13px] text-tg-hint">Уровень {item.level} · {item.sv} св-в</p>
          <div className="flex justify-between mt-2">
            <span className="text-[13px]">{item.effect_label}</span>
            <span className="text-[13px] text-[#34c759] font-bold">{item.effect_value}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={onActivate} disabled={item.is_active} className="flex-1 py-3 rounded-[10px] border-none font-bold text-sm disabled:opacity-60"
            style={{ background: item.is_active ? 'rgba(255,255,255,0.08)' : 'rgba(52,199,89,0.15)', color: item.is_active ? 'var(--tg-theme-hint-color)' : '#34c759' }}>
            Активировать
          </button>
          <button onClick={onSell} className="flex-1 py-3 rounded-[10px] border-none bg-[rgba(255,107,61,0.15)] text-[#ff6b3d] font-bold text-sm">Продать</button>
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
        onApply={() => setSubPage(null)} onBack={() => setSubPage(null)}
      />
    );
  }

  if (subPage?.type === 'forge_item_detail') {
    const item = gs.forge_items.find(i => i.id === subPage.itemId);
    if (item) return <ItemDetailPage item={item} onActivate={() => setSubPage(null)} onSell={() => setSubPage(null)} onBack={() => setSubPage(null)} />;
  }

  const netPerMin = gs.income_rub_per_min - gs.expenses_rub_per_min;

  return (
    <div className="page-content-safe">
      {/* ── Hero Header ── */}
      <div className="relative overflow-hidden"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', paddingTop: '16px' }}>
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse at 20% -10%, rgba(52,199,89,0.1) 0%, transparent 55%)' }} />

        {/* Profile row */}
        <div className="relative px-[14px] flex items-center gap-3 mb-3">
          <div className="w-11 h-11 rounded-full grid place-items-center text-[24px] shrink-0 relative"
            style={{ background: 'linear-gradient(135deg,rgba(52,199,89,0.3),rgba(10,132,255,0.2))', border: '1.5px solid color-mix(in srgb, var(--tg-theme-hint-color) 30%, transparent)' }}>
            {gs.profile_emoji ?? '🦁'}
            <div className="absolute inset-0 rounded-full" style={{ boxShadow: '0 0 14px rgba(52,199,89,0.3)' }} />
          </div>
          <div>
            <p className="m-0 text-lg font-extrabold leading-tight">{gs.nickname}</p>
            <p className="mt-[2px] mb-0 text-xs" style={{ color: 'var(--tg-theme-hint-color)' }}>С {formatDateShort(gs.registered_at)} г.</p>
          </div>
        </div>

        {/* Balance chips */}
        <div className="relative px-[14px] flex gap-[6px] mb-3 overflow-x-auto">
          {[
            { label: `₽ ${fmt(gs.rub)}`,   color: '#34c759' },
            { label: `$ ${fmt(gs.usd)}`,   color: '#ffd60a' },
            { label: `🐾 ${gs.paw_coins}`, color: '#bf5af2' },
          ].map(({ label, color }) => (
            <span key={label} className="px-3 py-[5px] rounded-[20px] text-[13px] font-bold whitespace-nowrap shrink-0"
              style={{ background: `${color}18`, color, border: `1px solid ${color}28`, boxShadow: `0 0 8px ${color}14` }}>
              {label}
            </span>
          ))}
        </div>

        {/* Income / Expenses row */}
        <div className="relative px-[14px] flex items-end">
          <div>
            <p className="m-0 text-[9px] font-bold tracking-[1px] uppercase" style={{ color: 'var(--tg-theme-hint-color)' }}>Чистый доход/мин</p>
            <p className={`mt-[3px] mb-0 text-[18px] font-extrabold tabular-nums ${netPerMin >= 0 ? 'income-glow' : 'expense-glow'}`}
              style={{ color: netPerMin >= 0 ? '#34c759' : '#ff6b3d' }}>
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
                <span className="absolute top-[4px] right-[4px] bg-[#ff3b30] text-white text-[9px] font-extrabold rounded-full min-w-[15px] h-[15px] flex items-center justify-center px-[3px]"
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
              style={{ background: 'rgba(255,59,48,0.1)', border: '1px solid rgba(255,59,48,0.35)' }}>
              <span className="text-xl">🤒</span>
              <p className="m-0 text-[13px] font-bold text-[#ff6b63]">
                {gs.sick_animals.length} животное больно! Штраф уже действует — открой ветеринара
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-2">
            <StatTile icon="🦁" label="Животных"    value={fmt(gs.animals.reduce((s, a) => s + a.quantity, 0))} accent="#34c759" />
            <StatTile icon="🌿" label={`Видов (+${Math.round(gs.diversity_bonus_per_species * gs.species_count * 100)}%)`} value={String(gs.species_count)} accent="#5ac8fa" />
            <StatTile icon="🏗️" label="Мест всего"  value={fmt(gs.total_seats)} accent="#5ac8fa" />
            <StatTile icon="✅" label="Свободно"    value={fmt(gs.free_seats)}  accent="#ffd60a" />
          </div>

          {gs.clan && (
            <div className="card flex items-center gap-3" style={{ border: '1px solid rgba(90,200,250,0.2)' }}>
              <div className="icon-box" style={{ background: 'rgba(90,200,250,0.12)' }}>🏰</div>
              <div className="flex-1">
                <p className="m-0 font-bold text-sm">«{gs.clan.name}»</p>
                <p className="mt-[2px] mb-0 text-xs text-tg-hint">
                  Ур. {gs.clan.level} · {gs.clan.member_count} уч.{gs.clan.specialty ? ` · ${gs.clan.specialty}` : ''}
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
          onApplySet={() => {}}
          onSelectItems={(setId) => setSubPage({ type: 'forge_select', setId, selectedIds: [] })}
        />
      )}

      {tab === 'aviaries' && (
        <div className="px-[14px] pt-3 flex flex-col gap-[10px] page-enter">
          {gs.sick_animals.length > 0 && (
            <div className="rounded-2xl px-[14px] py-3" style={{ background: 'rgba(255,59,48,0.1)', border: '1px solid rgba(255,59,48,0.35)' }}>
              <p className="m-0 mb-[6px] font-bold text-[#ff6b63]">🤒 Больные животные</p>
              {gs.sick_animals.map(s => {
                const def = ANIMALS.find(d => d.id === s.animal_id);
                return (
                  <div key={s.animal_id} className="flex justify-between items-center mb-2">
                    <span className="text-[13px]">{def?.emoji ?? '🐾'} {def?.name ?? s.animal_id}</span>
                    <div className="flex gap-2 items-center">
                      <span className="text-xs text-[#ff6b63]">-{fmt(s.penalty_rub_per_min)}/мин</span>
                      <button className="px-[10px] py-1 rounded-lg border-none bg-[rgba(52,199,89,0.15)] text-[#34c759] text-xs font-semibold">Лечить 🐾</button>
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
