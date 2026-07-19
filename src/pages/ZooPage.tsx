import { useEffect, useMemo, useState, type CSSProperties, type SetStateAction } from 'react';
import { fmt, fmtMin, fmtBalance } from '@/utils/format';
import { AnimatedNumber } from '@/components/AnimatedNumber';
import { TgsPlayer } from '@/components/TgsPlayer';
import { AnimalDetailCard } from '@/components/AnimalDetailCard';
import { AnimalArt } from '@/components/AnimalArt';
import type { Animal, GameState, GeneTier, MaintenancePollStatus } from '@/types';
import { lifeLeft } from '@/data/packs';
import { ExpeditionPage } from './ExpeditionPage';
import { ExpeditionOverviewCard } from '@/features/expeditions/ExpeditionOverviewCard';
import { apiForgeActivate, apiForgeApplySet, apiForgeCreateSet, apiForgeDeleteSet, apiForgeSell, apiForgeUpdateSet, apiReleaseAnimal, apiSetProfileAvatar } from '@/api';
import { setHashPath } from '@/lib/hashRoute';
import { tmaConfirm } from '@/lib/tma';
import { ACHIEVEMENT_TGS, customAchievementImage, PROFILE_ACHIEVEMENT_PREFIX } from '@/data/achievements';
import { ForgeTab, ItemDetailPage, ItemSelectPage } from '@/features/forge/ForgeInventory';
import { VetTab } from '@/features/vet/VetTab';
import { DevelopmentTab } from '@/features/development/DevelopmentTab';
import { AchievementsTab } from '@/features/achievements/AchievementsTab';
import { Nickname } from '@/components/NicknameEffects';
import { profileFrameClass } from '@/data/profileFrames';
import { wallpaperClass } from '@/data/profileWallpapers';
import { OnlinePlayersIndicator } from '@/components/OnlinePlayersIndicator';
import { getDefaultProfileAnimal, type ProfileAnimal } from '@/data/profileAnimals';
import { SPECIES_RARITY_META } from '@/data/packs';
import { compareByQuality } from '@/lib/animalQuality';

type ZooTab = 'overview' | 'development' | 'forge' | 'vet' | 'medals';

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
  { id: 'development', emoji: '🏗️', label: 'Развитие' },
  { id: 'forge',    emoji: '⚒️',  label: 'Кузня',  badge: gs => gs.items.length > 0 ? gs.items.length : null },
  { id: 'vet',      emoji: '🩺', label: 'Ветеринар', badge: gs => gs.sick_animal_ids.length > 0 ? gs.sick_animal_ids.length : null },
  { id: 'medals',   emoji: '🏅', label: 'Медали' },
];

type AnimalSort = 'new' | 'income' | 'life' | 'quality';

const ANIMAL_SORTS: { id: AnimalSort; label: string }[] = [
  { id: 'new',     label: 'Новые' },
  { id: 'income',  label: 'Доход' },
  { id: 'life',    label: 'Скоро умрут' },
  { id: 'quality', label: 'Качество' },
];

const ANIMAL_GENE_ORDER = [
  { key: 'survival', label: 'Выживаемость' },
  { key: 'appearance', label: 'Внешность' },
  { key: 'size_trait', label: 'Размер' },
  { key: 'reproduction', label: 'Размножение' },
] as const;

const GENE_TIER_COLORS: Record<GeneTier, string> = {
  // Keep the gene legend stable across player themes: ocean's gold accent is blue.
  low: '#d92323',
  medium: '#ffd21c',
  high: '#55c936',
};

// Each mode returns a fully-ordered comparator; ties fall back to income so the list never
// reshuffles arbitrarily between renders.
function compareAnimals(mode: AnimalSort): (a: Animal, b: Animal) => number {
  const byIncome = (a: Animal, b: Animal) => b.income - a.income;
  switch (mode) {
    case 'income':
      return byIncome;
    case 'life':
      // Soonest death first — the animals that need attention.
      return (a, b) => new Date(a.dies_at).getTime() - new Date(b.dies_at).getTime() || byIncome(a, b);
    case 'quality':
      // Самые редкие с лучшими генами сверху, обычные со слабыми — внизу.
      return compareByQuality;
    case 'new':
    default:
      // Most recently acquired first — freshly bought animals surface at the top.
      return (a, b) => new Date(b.acquired_at).getTime() - new Date(a.acquired_at).getTime() || byIncome(a, b);
  }
}

export function ZooPage({ gs, onRefresh, onlinePresence }: { gs: GameState; onRefresh: () => void; onlinePresence: MaintenancePollStatus }) {
  const [tab, setTab] = useState<ZooTab>('overview');
  const [subPage, setSubPageState] = useState<SubPage>(() => getZooSubPageFromHash());
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [selectedAnimal, setSelectedAnimal] = useState<Animal | null>(null);
  const [animalSort, setAnimalSort] = useState<AnimalSort>('new');
  const [defaultProfileAnimal] = useState<ProfileAnimal>(() => getDefaultProfileAnimal(gs.tg_id));

  const profileAchievementId = gs.profile_emoji?.startsWith(PROFILE_ACHIEVEMENT_PREFIX)
    ? gs.profile_emoji.slice(PROFILE_ACHIEVEMENT_PREFIX.length)
    : null;
  const sortedAnimals = useMemo(
    () => [...gs.animals].sort(compareAnimals(animalSort)),
    [gs.animals, animalSort],
  );

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
      <div className="relative">
        {gs.profile_wallpaper && gs.profile_wallpaper !== 'none' && (
          <div className={`profile-wallpaper ${wallpaperClass(gs.profile_wallpaper)}`} aria-hidden="true" />
        )}
        {/* Identity row: avatar + name (left), premium currencies (right) */}
        <div className="relative z-[1] px-[14px] flex items-center justify-between gap-4">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className={`profile-badge-frame shrink-0 ${profileFrameClass(gs.profile_frame)}`} style={{ '--frame-w': '3px' } as CSSProperties}>
              <div className="w-10 h-10 rounded-full overflow-hidden"
                style={{ background: 'linear-gradient(150deg,rgba(var(--c-gold-rgb),0.26),rgba(var(--c-orange-rgb),0.16))', border: '1.5px solid color-mix(in srgb, var(--c-gold) 30%, transparent)' }}>
                {profileAchievementId && (ACHIEVEMENT_TGS[profileAchievementId] || customAchievementImage(profileAchievementId)) ? (
                  customAchievementImage(profileAchievementId) ? <img src={customAchievementImage(profileAchievementId) ?? undefined} alt="" className="h-full w-full object-cover" /> :
                  <TgsPlayer src={ACHIEVEMENT_TGS[profileAchievementId]} loop />
                ) : (
                  <div className="grid h-full w-full place-items-center">
                    <AnimalArt animal={defaultProfileAnimal} size={32} />
                  </div>
                )}
              </div>
            </div>
            <div className="min-w-0 flex-1">
              <Nickname as="p" name={gs.nickname} color={gs.nickname_color} className="m-0 text-[16px] font-extrabold leading-tight truncate" />
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <OnlinePlayersIndicator data={onlinePresence} placement="inline" />
            <button
              type="button"
              onClick={() => setHashPath('/more/profile')}
              aria-label="Открыть настройки профиля"
              className="grid min-h-[44px] min-w-[44px] place-items-center rounded-xl border-none text-[18px] transition-transform active:scale-95"
              style={{ background: 'var(--surface-subtle)', color: 'var(--tg-theme-hint-color)', border: '1px solid var(--surface-overlay-border)' }}
            >
              ⚙️
            </button>
          </div>
        </div>
      </div>

      {/* Primary balance = the number that grows; income rate is its subordinate line */}
      <div className="relative mx-[14px] mt-3 rounded-2xl px-[16px] py-[13px]"
        style={{ background: 'var(--surface-subtle)', border: '1px solid var(--card-border)' }}>
          <div className="zoo-cash-currencies">
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
          <p className="zoo-cash-label m-0 text-[10px] font-extrabold uppercase tracking-[1.5px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Касса зоопарка
          </p>
          <p className="font-display m-0 mt-[3px] text-[28px] leading-none tabular-nums">
            <span className="text-[19px] font-bold" style={{ color: 'var(--tg-theme-hint-color)' }}>₽ </span>
            <AnimatedNumber value={gs.rub} format={fmtBalance} durationMs={850} />
          </p>
          <div className="m-0 mt-[7px] flex items-center justify-between gap-3 text-[13px] font-extrabold tabular-nums">
            <span className="text-[11px] font-bold text-tg-hint">Чистый доход</span>
            <span
              style={{ color: netPerMin >= 0 ? 'var(--c-green)' : 'var(--c-orange)' }}
            >
              {netPerMin >= 0 ? '▲' : '▼'} {fmtMin(netPerMin)} ₽/мин
            </span>
          </div>
          <div className="mt-[7px] flex items-center gap-2 text-[10px] font-bold tabular-nums text-tg-hint">
            <span>Доход <b className="text-tg-text">{fmt(gs.income_rub_per_min)} ₽</b></span>
            <span aria-hidden>−</span>
            <span>содержание <b style={{ color: 'var(--c-orange)' }}>{fmt(gs.upkeep_rub_per_min)} ₽</b></span>
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

      {tab === 'development' && (
        <DevelopmentTab gs={gs} onRefresh={onRefresh} />
      )}

      {tab === 'overview' && (
        <div className="px-[14px] pt-3 flex flex-col gap-3 page-enter">
          {gs.sick_animal_ids.length > 0 && (
            <button
              onClick={() => setTab('vet')}
              className="w-full rounded-2xl px-[14px] py-3 flex items-center gap-3 border-none text-left cursor-pointer"
              style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.35)' }}
            >
              <span className="text-xl shrink-0">🤒</span>
              <p className="m-0 flex-1 text-[13px] font-bold text-[var(--c-red-soft)]">
                Больных животных: {gs.sick_animal_ids.length}. Штраф к доходу уже действует — открой ветеринара
              </p>
              <span className="text-[18px] shrink-0" style={{ color: 'var(--c-red-soft)' }}>›</span>
            </button>
          )}

          <div className="grid grid-cols-2 gap-2">
            <StatTile icon="🦁" label="Животных"    value={fmt(gs.live_animals_count)} accent="var(--c-green)" />
            <StatTile icon="🌿" label={`Видов (+${gs.diversity_bonus_percent}%)`} value={String(gs.species_count)} accent="var(--c-cyan)" />
          </div>

          {gs.clan && (
            <button
              type="button"
              className="card flex items-center gap-3 cursor-pointer border-none text-left w-full"
              style={{ border: '1px solid rgba(var(--c-blue-rgb),0.24)' }}
              onClick={() => setHashPath('/more/clan')}
            >
              <div className="icon-box" style={{ background: 'rgba(var(--c-blue-rgb),0.14)' }}>🏰</div>
              <div className="flex-1">
                <p className="m-0 font-bold text-sm">«{gs.clan.name}»</p>
                <p className="mt-[2px] mb-0 text-xs text-tg-hint">
                  Ур. {gs.clan.level} · {gs.clan.member_count} уч.
                </p>
              </div>
              <span className="text-base text-tg-hint">›</span>
            </button>
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
              <p className="m-0 mb-2 text-[11px] font-extrabold text-tg-hint tracking-[1px] uppercase">
                Мои животные · {gs.animals.length} · нажми для карточки
              </p>
              {gs.animals.length > 1 && (
                <div className="grid grid-cols-4 gap-1 mb-2">
                  {ANIMAL_SORTS.map(s => {
                    const active = s.id === animalSort;
                    return (
                      <button
                        key={s.id}
                        onClick={() => setAnimalSort(s.id)}
                        className="min-w-0 w-full rounded-xl border-none cursor-pointer whitespace-nowrap transition-colors"
                        style={{
                          background: active ? 'color-mix(in srgb, var(--c-gold) 18%, transparent)' : 'color-mix(in srgb, var(--tg-theme-hint-color) 9%, transparent)',
                          color: active ? 'var(--c-gold)' : 'var(--tg-theme-hint-color)',
                          border: `1px solid ${active ? 'color-mix(in srgb, var(--c-gold) 40%, transparent)' : 'transparent'}`,
                          minHeight: 44,
                          padding: '0 2px',
                          fontSize: 11,
                          lineHeight: 1.1,
                          fontWeight: 700,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {s.label}
                      </button>
                    );
                  })}
                </div>
              )}
              <div className="grid grid-cols-2 gap-2">
                {sortedAnimals.map(a => {
                  const life = lifeLeft(a.dies_at);
                  const rarityColor = SPECIES_RARITY_META[a.species_rarity].color;
                  return (
                    <button
                      key={a.id}
                      onClick={() => setSelectedAnimal(a)}
                      className="card card-pressable text-left border-none w-full"
                      style={{
                        padding: '10px 12px',
                        border: `1px solid color-mix(in srgb, ${rarityColor} 55%, var(--card-border))`,
                        boxShadow: `0 0 12px color-mix(in srgb, ${rarityColor} 13%, transparent)`,
                      }}
                    >
                      <div className="flex items-center gap-[10px]">
                        <span className="relative shrink-0 w-[38px] h-[38px] flex items-center justify-center">
                          <AnimalArt animal={a} size={38} />
                          {a.is_sick && <span className="absolute -top-1 -right-1 text-[11px]">🤒</span>}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="m-0 text-[13px] font-bold truncate">{a.name}</p>
                          <p className="m-0 text-[11px] text-tg-hint truncate">{a.species_name} · ₽{fmt(a.income)}/мин</p>
                        </div>
                      </div>
                      <div className="mt-[6px] flex min-w-0 items-center justify-between gap-2">
                        {life ? (
                          <p className="m-0 min-w-0 truncate text-[10.5px] font-bold tabular-nums" style={{ color: life.color }}>
                            ⏳ {life.label}
                          </p>
                        ) : <span />}
                        <GeneDots animal={a} />
                      </div>
                    </button>
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
          onCreateSet={(name) => void runForgeAction(async () => {
            const result = await apiForgeCreateSet([], name);
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

      {tab === 'vet' && (
        <VetTab animals={gs.animals} usd={gs.usd} onRefresh={onRefresh} />
      )}

      {tab === 'medals' && (
        <AchievementsTab
          achievements={gs.achievements}
          profileAvatar={gs.profile_emoji}
          onSetProfileAvatar={(avatar) => void runForgeAction(
            () => apiSetProfileAvatar(avatar).then(() => undefined),
            'Не удалось изменить аватар профиля',
          )}
        />
      )}

      {selectedAnimal && (
        <AnimalDetailCard
          animal={selectedAnimal}
          onClose={() => setSelectedAnimal(null)}
          onRelease={async animal => {
            await apiReleaseAnimal(animal.id);
            setSelectedAnimal(null);
            onRefresh();
          }}
        />
      )}
    </div>
  );
}

function GeneDots({ animal }: { animal: Animal }) {
  return (
    <div
      className="flex shrink-0 items-center gap-[4px]"
      role="img"
      aria-label={`Свойства: ${ANIMAL_GENE_ORDER.map(gene => `${gene.label} — ${animal[gene.key]}`).join(', ')}`}
      title="Редкость свойств"
    >
      {ANIMAL_GENE_ORDER.map(gene => {
        const tier = animal[gene.key];
        return (
          <span
            key={gene.key}
            className="animal-gene-dot"
            style={{ backgroundColor: GENE_TIER_COLORS[tier] }}
            aria-hidden="true"
          />
        );
      })}
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
