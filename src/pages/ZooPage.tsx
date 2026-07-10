import { useEffect, useState, type SetStateAction } from 'react';
import { fmt, fmtMin } from '@/utils/format';
import type { GameState } from '@/types';
import { HABITAT_INFO } from '@/data/packs';
import { ExpeditionPage } from './ExpeditionPage';
import { ExpeditionOverviewCard } from '@/features/expeditions/ExpeditionOverviewCard';
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
  { id: 'forge',    emoji: '⚒️',  label: 'Кузня',  badge: gs => gs.items.length > 0 ? gs.items.length : null },
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
        items={gs.items} setId={subPage.setId} selectedIds={subPage.selectedIds}
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
    const item = gs.items.find(i => i.id === subPage.itemId);
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

  const netPerMin = gs.income_rub_per_min - gs.upkeep_rub_per_min;

  return (
    <div className="page-content-safe">
      {/* ── Header HUD — one grid, one font, left-aligned (idle-tycoon convention) ── */}
      <div className="relative overflow-hidden" style={{ paddingTop: '16px' }}>
        {/* Identity row: avatar + name (left), premium currencies (right) */}
        <div className="relative px-[14px] flex items-center gap-3">
          <div className="w-10 h-10 rounded-full grid place-items-center text-[22px] shrink-0"
            style={{ background: 'linear-gradient(150deg,rgba(var(--c-gold-rgb),0.26),rgba(var(--c-orange-rgb),0.16))', border: '1.5px solid color-mix(in srgb, var(--c-gold) 30%, transparent)' }}>
            {gs.profile_emoji ?? '🦁'}
          </div>
          <div className="min-w-0 flex-1">
            <p className="m-0 text-[16px] font-extrabold leading-tight truncate">{gs.nickname}</p>
            <p className="mt-[1px] mb-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>Смотритель · сезон {gs.season_id}</p>
          </div>
          <div className="flex gap-[6px] shrink-0">
            {[
              { label: `$ ${fmt(gs.usd)}`,   color: 'var(--c-gold)' },
              { label: `🐾 ${gs.paw_coins}`, color: 'var(--c-purple)' },
            ].map(({ label, color }) => (
              <span key={label} className="px-[10px] py-[5px] rounded-full text-[12px] font-extrabold tabular-nums whitespace-nowrap"
                style={{ background: `color-mix(in srgb, ${color} 13%, var(--tg-theme-secondary-bg-color))`, color, border: `1px solid color-mix(in srgb, ${color} 26%, transparent)` }}>
                {label}
              </span>
            ))}
          </div>
        </div>

        {/* Primary balance = the number that grows; income rate is its subordinate line */}
        <div className="relative mx-[14px] mt-3 rounded-2xl px-[16px] py-[13px]"
          style={{ background: 'var(--surface-subtle)', border: '1px solid var(--card-border)' }}>
          <p className="m-0 text-[10px] font-extrabold uppercase tracking-[1.5px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Касса зоопарка
          </p>
          <p className="font-display m-0 mt-[3px] text-[30px] leading-none">
            <span className="text-[19px] font-bold" style={{ color: 'var(--tg-theme-hint-color)' }}>₽ </span>{fmt(gs.rub)}
          </p>
          <p className="m-0 mt-[7px] text-[13px] font-extrabold tabular-nums"
            style={{ color: netPerMin >= 0 ? 'var(--c-green)' : 'var(--c-orange)' }}>
            {netPerMin >= 0 ? '▲' : '▼'} {fmtMin(netPerMin)} ₽/мин
          </p>
        </div>
      </div>

      {/* ── Section tabs ── */}
      <div
        className="flex mx-[14px] my-3 rounded-2xl p-1"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 18%, transparent)' }}
      >
        {ZOO_TABS.map(({ id, emoji, label, badge }) => {
          const isActive = tab === id;
          const badgeVal = badge?.(gs) ?? null;
          return (
            <button
              key={id}
              onClick={() => setTab(id)}
              className="flex-1 flex flex-col items-center justify-center gap-[3px] py-[8px] rounded-xl border-none relative transition-all duration-200"
              style={{
                background: isActive ? 'color-mix(in srgb, var(--tg-theme-button-color) 15%, transparent)' : 'transparent',
                color: isActive ? 'var(--tg-theme-text-color)' : 'var(--tg-theme-hint-color)',
                boxShadow: isActive ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
              }}
            >
              <span className="text-[17px] leading-none">{emoji}</span>
              <span className={`text-[10px] leading-none ${isActive ? 'font-bold' : 'font-semibold'}`}>{label}</span>
              {badgeVal != null && (
                <span className="absolute top-[3px] right-[8px] bg-[var(--c-red)] text-[var(--tg-theme-button-text-color)] text-[9px] font-extrabold rounded-full min-w-[15px] h-[15px] flex items-center justify-center px-[3px]"
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
          {gs.sick_animal_ids.length > 0 && (
            <div className="rounded-2xl px-[14px] py-3 flex items-start gap-3"
              style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.35)' }}>
              <span className="text-xl">🤒</span>
              <p className="m-0 text-[13px] font-bold text-[var(--c-red-soft)]">
                {gs.sick_animal_ids.length} животное больно! Штраф уже действует — открой ветеринара
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-2">
            <StatTile icon="🦁" label="Животных"    value={fmt(gs.live_animals_count)} accent="var(--c-green)" />
            <StatTile icon="🌿" label={`Видов (+${gs.diversity_bonus_percent}%)`} value={String(gs.species_count)} accent="var(--c-cyan)" />
            <StatTile icon="🌍" label="Местностей"  value={fmt(gs.localities_count)} accent="var(--c-cyan)" />
            <StatTile icon="📅" label="Сезон"       value={String(gs.season_id)}  accent="var(--c-gold)" />
          </div>

          {gs.clan && (
            <div className="card flex items-center gap-3" style={{ border: '1px solid rgba(var(--c-blue-rgb),0.24)' }}>
              <div className="icon-box" style={{ background: 'rgba(var(--c-blue-rgb),0.14)' }}>🏰</div>
              <div className="flex-1">
                <p className="m-0 font-bold text-sm">«{gs.clan.name}»</p>
                <p className="mt-[2px] mb-0 text-xs text-tg-hint">
                  Ур. {gs.clan.level} · {gs.clan.member_count} уч.
                </p>
              </div>
              <span className="text-base text-tg-hint">›</span>
            </div>
          )}

          <ExpeditionOverviewCard onOpen={() => setSubPage({ type: 'expeditions' })} />

          {/* First-run onboarding: an empty zoo is an invitation, and it teaches the
              core loop by doing — get an animal, it earns income every minute. */}
          {gs.animals.length === 0 && (
            <div className="card text-center" style={{ padding: '22px 18px', border: '1px solid rgba(var(--c-green-rgb),0.30)' }}>
              <p className="m-0 text-[40px]" style={{ animation: 'float 3s ease-in-out infinite' }}>🎁</p>
              <p className="mt-2 mb-1 font-extrabold text-[16px]">Заведи первого зверя</p>
              <p className="m-0 mb-4 text-[13px] text-tg-hint max-w-[280px] mx-auto leading-snug">
                Открой бесплатный пак в магазине — животное поселится в зоопарке и начнёт приносить доход каждую минуту.
              </p>
              <button
                onClick={() => setHashPath('/shop')}
                className="btn-primary w-full py-3 rounded-xl text-[15px]"
              >
                Открыть первый пак
              </button>
            </div>
          )}

          {gs.animals.length > 0 && (
            <div>
              <p className="m-0 mb-2 text-[11px] font-extrabold text-tg-hint tracking-[1px] uppercase">Мои животные</p>
              <div className="grid grid-cols-2 gap-2">
                {gs.animals.slice(0, 10).map(a => {
                  const habitat = HABITAT_INFO[a.habitat];
                  return (
                    <div key={a.id} className="card" style={{ padding: '10px 12px' }}>
                      <div className="flex items-center gap-[10px]">
                        <span className="text-[24px]">{a.species_emoji}</span>
                        <div className="min-w-0">
                          <p className="m-0 text-[13px] font-semibold truncate">{a.species_name}</p>
                          <p className="m-0 text-[11px] text-tg-hint">{habitat.emoji} {habitat.name} · ₽{fmt(a.income)}/мин</p>
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
        <ForgeTab items={gs.items} sets={gs.item_sets}
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
            const itemSet = gs.item_sets.find(s => s.id === setId);
            setSubPage({ type: 'forge_select', setId, selectedIds: [...(itemSet?.item_ids ?? [])] });
          }}
          onItemDetail={(itemId) => setSubPage({ type: 'forge_item_detail', itemId })}
        />
      )}

      {tab === 'medals' && (
        <div className="px-[14px] pt-3 page-enter">
          <div className="card text-center py-10">
            <p className="m-0 text-[48px]" style={{ animation: 'float 3s ease-in-out infinite' }}>🏅</p>
            <p className="mt-3 mb-1 font-bold text-[15px]">Медали уже в пути</p>
            <p className="m-0 text-tg-hint text-[13px] max-w-[260px] mx-auto leading-snug">
              Развивай зоопарк и открывай виды — скоро за это начнут давать награды.
            </p>
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
      <div className="icon-box mb-2" style={{ background: `color-mix(in srgb, ${accent} 16%, transparent)` }}>
        <span>{icon}</span>
      </div>
      <p className="font-display m-0 mb-[3px] text-[22px] leading-none" style={{ color: accent }}>{value}</p>
      <p className="m-0 text-[11px] text-tg-hint leading-snug">{label}</p>
    </div>
  );
}
