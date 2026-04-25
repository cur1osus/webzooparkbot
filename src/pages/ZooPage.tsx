import { useEffect, useState, type SetStateAction } from 'react';
import { fmt, fmtMin, formatDateShort } from '@/utils/format';
import type { GameState } from '@/types';
import { ANIMALS } from '@/data/animals';
import { ExpeditionPage } from './ExpeditionPage';
import { ExpeditionOverviewCard } from '@/features/expeditions/ExpeditionOverviewCard';
import { getClanSpecialtyLabel } from '@/utils/clan';
import { apiForgeActivate, apiForgeApplySet, apiForgeCreateSet, apiForgeDeleteSet, apiForgeSell, apiForgeUpdateSet } from '@/api';
import { setHashPath } from '@/lib/hashRoute';
import { tmaConfirm } from '@/lib/tma';
import { ForgeTab, ItemDetailPage, ItemSelectPage } from '@/features/forge/ForgeInventory';

type ZooTab = 'overview' | 'forge' | 'medals';

// ─── ZooPage ──────────────────────────────────────────────────────────────────

type SubPage =
  | { type: 'expeditions' }
  | { type: 'forge_select'; setId: string; selectedIds: string[] }
  | { type: 'forge_item_detail'; itemId: string }
  | null;

function getZooSubPageFromHash(): SubPage {
  const parts = window.location.hash.replace(/^#/, '').split('/').filter(Boolean);
  if (parts[0] !== 'zoo') return null;
  if (parts[1] === 'expeditions') return { type: 'expeditions' };
  if (parts[1] === 'forge' && parts[2] === 'item' && parts[3]) {
    return { type: 'forge_item_detail', itemId: decodeURIComponent(parts[3]) };
  }
  return null;
}

function routeForSubPage(subPage: SubPage): string | null {
  if (subPage?.type === 'expeditions') return '/zoo/expeditions';
  if (subPage?.type === 'forge_item_detail') return `/zoo/forge/item/${encodeURIComponent(subPage.itemId)}`;
  if (subPage === null) return '/zoo';
  return null;
}

const ZOO_TABS: { id: ZooTab; emoji: string; label: string; badge?: (gs: GameState) => number | null }[] = [
  { id: 'overview', emoji: '🏠', label: 'Обзор' },
  { id: 'forge',    emoji: '⚒️',  label: 'Кузня',  badge: gs => gs.forge_items.length > 0 ? gs.forge_items.length : null },
  { id: 'medals',   emoji: '🏅', label: 'Медали' },
];

export function ZooPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [tab, setTab] = useState<ZooTab>('overview');
  const [subPage, setSubPageState] = useState<SubPage>(() => getZooSubPageFromHash());
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const onHashChange = () => setSubPageState(getZooSubPageFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  function setSubPage(next: SetStateAction<SubPage>) {
    if (typeof next === 'function') {
      setSubPageState(next);
      return;
    }
    setSubPageState(next);
    const route = routeForSubPage(next);
    if (route) setHashPath(route);
  }

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
