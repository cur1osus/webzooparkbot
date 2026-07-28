import { memo, useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type SetStateAction } from 'react';
import { fmt, fmtMin, fmtBalance } from '@/utils/format';
import { AnimatedNumber } from '@/components/AnimatedNumber';
import { TgsPlayer } from '@/components/TgsPlayer';
import { AnimalDetailCard } from '@/components/AnimalDetailCard';
import { AnimalArt } from '@/components/AnimalArt';
import type { Animal, GameState, GeneTier, MaintenancePollStatus } from '@/types';
import { lifeLeft } from '@/data/packs';
import { ExpeditionPage } from './ExpeditionPage';
import { ExpeditionOverviewCard } from '@/features/expeditions/ExpeditionOverviewCard';
import { apiForgeApplySet, apiForgeCreateSet, apiForgeDeleteSet, apiForgeUpdateSet, apiGetAnimal, apiGetZooAnimals, apiReleaseAnimal, apiReleaseAnimals, apiSetAnimalFavorite, apiSetProfileAvatar } from '@/api';
import { setHashPath } from '@/lib/hashRoute';
import { tmaConfirm } from '@/lib/tma';
import { ACHIEVEMENT_TGS, customAchievementImage, PROFILE_ACHIEVEMENT_PREFIX } from '@/data/achievements';
import { ForgeTab, ItemSelectPage } from '@/features/forge/ForgeInventory';
import { VetTab } from '@/features/vet/VetTab';
import { DevelopmentTab } from '@/features/development/DevelopmentTab';
import { AchievementsTab } from '@/features/achievements/AchievementsTab';
import { Nickname } from '@/components/NicknameEffects';
import { profileFrameClass } from '@/data/profileFrames';
import { wallpaperClass } from '@/data/profileWallpapers';
import { OnlinePlayersIndicator } from '@/components/OnlinePlayersIndicator';
import { getDefaultProfileAnimal, type ProfileAnimal } from '@/data/profileAnimals';
import { SPECIES_RARITY_META } from '@/data/packs';
import { useStoredChoice } from '@/hooks/useStoredChoice';

type ZooTab = 'overview' | 'development' | 'forge' | 'vet' | 'medals';

// ─── ZooPage ──────────────────────────────────────────────────────────────────

type SubPage =
  | { type: 'expeditions' }
  | { type: 'forge_select'; setId: string; selectedIds: string[] }
  | null;

function getZooSubPageFromHash(): SubPage {
  const parts = window.location.hash.replace(/^#/, '').split('/').filter(Boolean);
  if (parts[0] !== 'zoo') return null;
  if (parts[1] === 'expeditions') return { type: 'expeditions' };
  return null;
}

function routeForSubPage(subPage: SubPage): string | null {
  if (subPage?.type === 'expeditions') return '/zoo/expeditions';
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

const ANIMAL_SORT_IDS = ANIMAL_SORTS.map(s => s.id);

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

// The overview grid lists every animal a player owns. A large zoo (thousands of animals)
// would otherwise mount thousands of DOM cards at once, making the page slow to open and
// laggy to scroll. Reveal the list in chunks as the player nears the end, so the page opens
// instantly and stays smooth no matter the collection size.
const ANIMAL_GRID_INITIAL = 60;
const ANIMAL_GRID_STEP = 60;

export function ZooPage({ gs, onRefresh, onPatchState, onlinePresence }: { gs: GameState; onRefresh: () => void; onPatchState: (patch: Partial<GameState>) => void; onlinePresence: MaintenancePollStatus }) {
  const [tab, setTab] = useState<ZooTab>('overview');
  const [subPage, setSubPageState] = useState<SubPage>(() => getZooSubPageFromHash());
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [selectedAnimal, setSelectedAnimal] = useState<Animal | null>(null);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedAnimalIds, setSelectedAnimalIds] = useState<Set<number>>(new Set());
  const [batchReleaseBusy, setBatchReleaseBusy] = useState(false);
  const [animalSort, setAnimalSort] = useStoredChoice<AnimalSort>('zoo-animal-sort', gs.tg_id, ANIMAL_SORT_IDS, 'new');
  const [favoriteOverrides, setFavoriteOverrides] = useState<Map<number, boolean>>(new Map());
  const [favoriteBusyId, setFavoriteBusyId] = useState<number | null>(null);
  const [defaultProfileAnimal] = useState<ProfileAnimal>(() => getDefaultProfileAnimal(gs.tg_id));
  const [animals, setAnimals] = useState<Animal[]>(gs.animals);
  const [animalsTotal, setAnimalsTotal] = useState(gs.live_animals_count);
  const [nextAnimalsOffset, setNextAnimalsOffset] = useState<number | null>(0);
  const [animalsLoading, setAnimalsLoading] = useState(false);
  const animalsRequestRef = useRef(0);
  const animalsLoadingRef = useRef(false);

  const profileAchievementId = gs.profile_emoji?.startsWith(PROFILE_ACHIEVEMENT_PREFIX)
    ? gs.profile_emoji.slice(PROFILE_ACHIEVEMENT_PREFIX.length)
    : null;
  const baseSortedAnimals = animals;
  const sortedAnimals = useMemo(() => {
    const favorites: Animal[] = [];
    const regular: Animal[] = [];
    for (const animal of baseSortedAnimals) {
      (favoriteOverrides.get(animal.id) ?? animal.is_favorite ? favorites : regular).push(animal);
    }
    return favorites.length === 0 ? regular : favorites.concat(regular);
  }, [baseSortedAnimals, favoriteOverrides]);

  useEffect(() => {
    const requestId = ++animalsRequestRef.current;
    animalsLoadingRef.current = true;
    setAnimalsLoading(true);
    setNextAnimalsOffset(0);
    setVisibleAnimalCount(ANIMAL_GRID_INITIAL);
    void apiGetZooAnimals(0, 120, animalSort)
      .then(result => {
        if (animalsRequestRef.current !== requestId) return;
        setAnimals(result.animals);
        setAnimalsTotal(result.total);
        setNextAnimalsOffset(result.next_offset);
      })
      .catch(error => {
        if (animalsRequestRef.current === requestId) {
          showMessage(error instanceof Error ? error.message : 'Не удалось загрузить животных');
        }
      })
      .finally(() => {
        if (animalsRequestRef.current === requestId) {
          animalsLoadingRef.current = false;
          setAnimalsLoading(false);
        }
      });
  }, [animalSort]);

  const loadMoreAnimals = useCallback(() => {
    const offset = nextAnimalsOffset;
    if (offset === null || animalsLoadingRef.current) return;
    const requestId = animalsRequestRef.current;
    animalsLoadingRef.current = true;
    setAnimalsLoading(true);
    void apiGetZooAnimals(offset, 120, animalSort)
      .then(result => {
        if (animalsRequestRef.current !== requestId) return;
        setAnimals(previous => {
          const known = new Set(previous.map(animal => animal.id));
          return previous.concat(result.animals.filter(animal => !known.has(animal.id)));
        });
        setAnimalsTotal(result.total);
        setNextAnimalsOffset(result.next_offset);
      })
      .catch(error => showMessage(error instanceof Error ? error.message : 'Не удалось загрузить животных'))
      .finally(() => {
        if (animalsRequestRef.current === requestId) {
          animalsLoadingRef.current = false;
          setAnimalsLoading(false);
        }
      });
  }, [animalSort, nextAnimalsOffset]);

  // Windowed reveal of the animal grid — see ANIMAL_GRID_INITIAL for the reasoning.
  const [visibleAnimalCount, setVisibleAnimalCount] = useState(ANIMAL_GRID_INITIAL);
  const animalSentinelRef = useRef<HTMLDivElement | null>(null);

  // Changing the sort presents a fresh ordering the player wants to read from the top,
  // so collapse back to the first chunk. A background refresh keeps the current window.
  useEffect(() => {
    setVisibleAnimalCount(ANIMAL_GRID_INITIAL);
  }, [animalSort]);

  const visibleAnimals = useMemo(
    () => sortedAnimals.slice(0, visibleAnimalCount),
    [sortedAnimals, visibleAnimalCount],
  );

  const hasMoreAnimals = visibleAnimalCount < sortedAnimals.length || nextAnimalsOffset !== null;

  const openAnimal = useCallback((animal: Animal) => {
    setSelectedAnimal(animal);
    void apiGetAnimal(animal.id)
      .then(({ animal: fullAnimal }) => {
        setSelectedAnimal(current => current?.id === fullAnimal.id ? fullAnimal : current);
      })
      .catch(() => {
        // The compact passport already contains everything except the optional income
        // breakdown, so a transient detail request must not block opening the card.
      });
  }, []);

  const toggleSelectedAnimal = useCallback((animalId: number) => {
    setSelectedAnimalIds(previous => {
      const next = new Set(previous);
      if (next.has(animalId)) next.delete(animalId);
      else next.add(animalId);
      return next;
    });
  }, []);

  // Grow the window as the sentinel near the end of the list scrolls into view. The
  // scroll container is the page shell, so observe against it rather than the viewport.
  useEffect(() => {
    const sentinel = animalSentinelRef.current;
    if (!sentinel || !hasMoreAnimals) return;
    const root = sentinel.closest('.page-scroll-area') as HTMLElement | null;
    const observer = new IntersectionObserver(
      entries => {
        if (entries.some(entry => entry.isIntersecting)) {
          if (visibleAnimalCount < sortedAnimals.length) {
            setVisibleAnimalCount(count => Math.min(count + ANIMAL_GRID_STEP, sortedAnimals.length));
          } else {
            loadMoreAnimals();
          }
        }
      },
      { root, rootMargin: '600px 0px' },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMoreAnimals, loadMoreAnimals, sortedAnimals.length, subPage, tab, visibleAnimalCount]);

  // Build the grid element only when the visible slice or favourite marks actually change.
  // The live-balance ticker replaces `gs` every second; without this the whole list would
  // reconcile on every tick even though nothing about the cards changed.
  const animalGrid = useMemo(
    () => (
      <div className="grid grid-cols-2 gap-2">
        {visibleAnimals.map(a => (
          <AnimalCard
            key={a.id}
            animal={a}
            isFavorite={favoriteOverrides.get(a.id) ?? a.is_favorite}
            selectionMode={selectionMode}
            isSelected={selectedAnimalIds.has(a.id)}
            onSelect={openAnimal}
            onToggleSelect={toggleSelectedAnimal}
          />
        ))}
      </div>
    ),
    [visibleAnimals, favoriteOverrides, selectionMode, selectedAnimalIds, openAnimal, toggleSelectedAnimal],
  );

  async function toggleFavorite(animal: Animal) {
    if (favoriteBusyId !== null) return;
    const current = favoriteOverrides.get(animal.id) ?? animal.is_favorite;
    const next = !current;
    setFavoriteOverrides(previous => new Map(previous).set(animal.id, next));
    setFavoriteBusyId(animal.id);
    try {
      await apiSetAnimalFavorite(animal.id, next);
    } catch (e) {
      setFavoriteOverrides(previous => {
        const nextOverrides = new Map(previous);
        nextOverrides.delete(animal.id);
        return nextOverrides;
      });
      showMessage(e instanceof Error ? e.message : 'Не удалось изменить избранное');
    } finally {
      setFavoriteBusyId(null);
    }
  }

  function toggleSelectionMode() {
    if (selectionMode) {
      setSelectionMode(false);
      setSelectedAnimalIds(new Set());
    } else {
      setSelectionMode(true);
    }
  }

  function selectAllAnimals() {
    setSelectedAnimalIds(new Set(animals.map(animal => animal.id)));
  }

  async function releaseSelectedAnimals() {
    if (batchReleaseBusy || selectedAnimalIds.size === 0) return;
    const ids = [...selectedAnimalIds];
    const label = ids.length === 1 ? 'животное' : 'животных';
    if (!(await tmaConfirm(`Отпустить ${ids.length} ${label}? Их нельзя будет вернуть.`, 'Массовый выпуск')))
      return;
    setBatchReleaseBusy(true);
    setMessage(null);
    try {
      const result = await apiReleaseAnimals(ids);
      const releasedIds = new Set(result.released_animal_ids);
      onPatchState({
        sick_animal_ids: gs.sick_animal_ids.filter(id => !releasedIds.has(id)),
        live_animals_count: Math.max(0, gs.live_animals_count - result.released_count),
        income_rub_per_min: result.income_rub_per_min,
      });
      setAnimals(previous => previous.filter(animal => !releasedIds.has(animal.id)));
      setAnimalsTotal(previous => Math.max(0, previous - result.released_count));
      setSelectionMode(false);
      setSelectedAnimalIds(new Set());
      showMessage(`Отпущено животных: ${result.released_count}`);
    } catch (e) {
      showMessage(e instanceof Error ? e.message : 'Не удалось отпустить животных');
    } finally {
      setBatchReleaseBusy(false);
    }
  }

  useEffect(() => {
    const onHashChange = () => setSubPageState(getZooSubPageFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const setSubPage = useCallback((next: SetStateAction<SubPage>) => {
    if (typeof next === 'function') {
      setSubPageState(next);
      return;
    }
    setSubPageState(next);
    const route = routeForSubPage(next);
    if (route) setHashPath(route);
  }, []);

  function showMessage(text: string) {
    setMessage(text);
    window.setTimeout(() => setMessage(null), 3000);
  }

  const runForgeAction = useCallback(async (action: () => Promise<void>, fallback: string, refresh = true) => {
    if (busy) return;
    setBusy(true);
    setMessage(null);
    try {
      await action();
      if (refresh) onRefresh();
    } catch (e) {
      showMessage(e instanceof Error ? e.message : fallback);
    } finally {
      setBusy(false);
    }
  }, [busy, onRefresh]);

  const handleForgeApplySet = useCallback((setId: string) => {
    void runForgeAction(async () => {
      const result = await apiForgeApplySet(setId);
      const activeItemIds = new Set(result.active_item_ids);
      onPatchState({
        items: gs.items.map(item => ({ ...item, is_active: activeItemIds.has(item.id) })),
        item_sets: gs.item_sets.map(itemSet => {
          const itemSetIds = new Set(itemSet.item_ids);
          const isActive = itemSet.item_ids.length > 0
            && itemSet.item_ids.length === activeItemIds.size
            && itemSet.item_ids.every(itemId => activeItemIds.has(itemId));
          return { ...itemSet, is_active: isActive && itemSetIds.size === activeItemIds.size };
        }),
        income_rub_per_min: result.income_rub_per_min,
        upkeep_rub_per_min: result.upkeep_rub_per_min,
        income_synced_at: result.income_synced_at,
        active_item_bonuses: result.active_item_bonuses,
      });
    }, 'Ошибка применения сета', false);
  }, [gs.items, gs.item_sets, onPatchState, runForgeAction]);

  const handleForgeCreateSet = useCallback((name?: string) => {
    void runForgeAction(async () => {
      const result = await apiForgeCreateSet([], name);
      setSubPage({ type: 'forge_select', setId: result.set.id, selectedIds: [] });
    }, 'Ошибка создания сета');
  }, [runForgeAction, setSubPage]);

  const handleForgeRenameSet = useCallback((setId: string, name: string) => {
    const trimmedName = name.trim();
    if (!trimmedName) {
      setMessage('Название сета не может быть пустым');
      return;
    }
    const previousSet = gs.item_sets.find(s => s.id === setId);
    if (!previousSet || previousSet.name === trimmedName) return;

    // Rename is a local metadata change. Patch it immediately so a large zoo does not make
    // the pencil interaction wait for a full `/api/me` refresh (which also contains animals).
    onPatchState({
      item_sets: gs.item_sets.map(itemSet => itemSet.id === setId ? { ...itemSet, name: trimmedName } : itemSet),
    });
    void runForgeAction(async () => {
      try {
        const result = await apiForgeUpdateSet(setId, previousSet.item_ids, trimmedName);
        onPatchState({
          item_sets: gs.item_sets.map(itemSet => itemSet.id === setId
            ? { ...itemSet, ...result.set, is_active: itemSet.is_active }
            : itemSet),
        });
      } catch (error) {
        onPatchState({
          item_sets: gs.item_sets.map(itemSet => itemSet.id === setId
            ? { ...itemSet, name: previousSet.name }
            : itemSet),
        });
        throw error;
      }
    }, 'Ошибка переименования сета', false);
  }, [gs.item_sets, onPatchState, runForgeAction]);

  const handleForgeDeleteSet = useCallback((setId: string) => {
    void runForgeAction(async () => {
      if (!(await tmaConfirm('Удалить этот сет? Предметы останутся у тебя.', 'Удалить сет?'))) return;
      await apiForgeDeleteSet(setId);
    }, 'Ошибка удаления сета');
  }, [runForgeAction]);

  const handleForgeSelectItems = useCallback((setId: string) => {
    const itemSet = gs.item_sets.find(s => s.id === setId);
    setSubPage({ type: 'forge_select', setId, selectedIds: [...(itemSet?.item_ids ?? [])] });
  }, [gs.item_sets, setSubPage]);

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
          {animalsTotal === 0 && !animalsLoading && (
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

          {animalsTotal > 0 && (
            <div>
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="m-0 text-[11px] font-extrabold text-tg-hint tracking-[1px] uppercase">
                  Мои животные · {animalsTotal}{selectionMode ? '' : ' · нажми для карточки'}
                </p>
                <button
                  type="button"
                  onClick={toggleSelectionMode}
                  className="shrink-0 rounded-xl border-none px-3 py-2 text-[11px] font-bold cursor-pointer"
                  style={{
                    background: selectionMode ? 'color-mix(in srgb, var(--c-gold) 18%, transparent)' : 'color-mix(in srgb, var(--tg-theme-hint-color) 10%, transparent)',
                    color: selectionMode ? 'var(--c-gold)' : 'var(--tg-theme-hint-color)',
                  }}
                >
                  {selectionMode ? 'Отмена' : 'Выбрать'}
                </button>
              </div>
              {selectionMode && (
                <div className="mb-2 flex items-center gap-2 rounded-2xl px-3 py-2" style={{ background: 'var(--surface-subtle)', border: '1px solid var(--card-border)' }}>
                  <span className="min-w-0 flex-1 text-[11px] font-bold text-tg-hint">
                    Выбрано: <span className="text-tg-text">{selectedAnimalIds.size}</span>
                  </span>
                  <button
                    type="button"
                    onClick={selectAllAnimals}
                    className="shrink-0 rounded-xl border-none px-2 py-2 text-[10px] font-bold cursor-pointer"
                    style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 10%, transparent)', color: 'var(--tg-theme-hint-color)' }}
                  >
                    Загруженные
                  </button>
                  <button
                    type="button"
                    onClick={() => void releaseSelectedAnimals()}
                    disabled={selectedAnimalIds.size === 0 || batchReleaseBusy}
                    className="shrink-0 rounded-xl border-none px-3 py-2 text-[10px] font-bold cursor-pointer disabled:opacity-40"
                    style={{ background: 'rgba(var(--c-red-rgb),0.14)', color: 'var(--c-red)' }}
                  >
                    {batchReleaseBusy ? '...' : 'Отпустить'}
                  </button>
                </div>
              )}
              {animalsTotal > 1 && (
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
              {animalGrid}
              {hasMoreAnimals && <div ref={animalSentinelRef} aria-hidden className="h-px w-full" />}
              {animalsLoading && <div className="flex justify-center py-3"><div className="spinner" /></div>}
            </div>
          )}
        </div>
      )}

      {tab === 'forge' && (
        <ForgeTab items={gs.items} sets={gs.item_sets} bonuses={gs.active_item_bonuses}
          busy={busy}
          message={message}
          onApplySet={handleForgeApplySet}
          onCreateSet={handleForgeCreateSet}
          onRenameSet={handleForgeRenameSet}
          onDeleteSet={handleForgeDeleteSet}
          onSelectItems={handleForgeSelectItems}
        />
      )}

      {tab === 'vet' && (
        <VetTab usd={gs.usd} onPatchState={onPatchState} />
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
          isFavorite={favoriteOverrides.get(selectedAnimal.id) ?? selectedAnimal.is_favorite}
          favoriteBusy={favoriteBusyId === selectedAnimal.id}
          onToggleFavorite={() => void toggleFavorite(selectedAnimal)}
          onClose={() => setSelectedAnimal(null)}
          onRelease={async animal => {
            const result = await apiReleaseAnimal(animal.id);
            onPatchState({
              sick_animal_ids: gs.sick_animal_ids.filter(id => id !== animal.id),
              live_animals_count: Math.max(0, gs.live_animals_count - 1),
              income_rub_per_min: result.income_rub_per_min,
            });
            setAnimals(previous => previous.filter(item => item.id !== animal.id));
            setAnimalsTotal(previous => Math.max(0, previous - 1));
            setSelectedAnimal(null);
          }}
        />
      )}
    </div>
  );
}

// Memoised so the per-second live-balance re-render of ZooPage never re-renders a card whose
// data is unchanged. `onSelect` is the stable `setSelectedAnimal` setter and `isFavorite` is a
// resolved boolean, so the props stay referentially stable across ticks.
const AnimalCard = memo(function AnimalCard({
  animal,
  isFavorite,
  selectionMode,
  isSelected,
  onSelect,
  onToggleSelect,
}: {
  animal: Animal;
  isFavorite: boolean;
  selectionMode: boolean;
  isSelected: boolean;
  onSelect: (animal: Animal) => void;
  onToggleSelect: (animalId: number) => void;
}) {
  const life = lifeLeft(animal.dies_at);
  const rarityColor = SPECIES_RARITY_META[animal.species_rarity].color;
  return (
    <div
      role={selectionMode ? 'checkbox' : 'button'}
      tabIndex={0}
      aria-checked={selectionMode ? isSelected : undefined}
      onClick={() => selectionMode ? onToggleSelect(animal.id) : onSelect(animal)}
      onKeyDown={event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          if (selectionMode) onToggleSelect(animal.id);
          else onSelect(animal);
        }
      }}
      className="card card-pressable text-left border-none w-full"
      style={{
        position: 'relative',
        padding: '10px 12px',
        border: isSelected ? '1.5px solid var(--c-gold)' : isFavorite ? '1.5px solid #f3b53f' : `1px solid color-mix(in srgb, ${rarityColor} 55%, var(--card-border))`,
        boxShadow: isFavorite ? '0 0 14px rgba(243, 181, 63, 0.3)' : `0 0 12px color-mix(in srgb, ${rarityColor} 13%, transparent)`,
      }}
    >
      {selectionMode && (
        <span
          className="absolute right-2 top-2 grid h-6 w-6 place-items-center rounded-full text-[13px] font-extrabold"
          style={{ background: isSelected ? 'var(--c-gold)' : 'var(--surface-subtle-strong)', color: isSelected ? '#241707' : 'var(--tg-theme-hint-color)', border: '1px solid color-mix(in srgb, var(--c-gold) 45%, transparent)' }}
          aria-hidden="true"
        >
          {isSelected ? '✓' : ''}
        </span>
      )}
      <div className="flex items-center gap-[8px] pr-5">
        <span className="relative shrink-0 w-[38px] h-[38px] flex items-center justify-center">
          <AnimalArt animal={animal} size={38} />
          {animal.is_sick && <span className="absolute -top-1 -right-1 text-[11px]">🤒</span>}
        </span>
        <div className="min-w-0 flex-1">
          <p className="m-0 text-[13px] font-bold truncate">{animal.name}</p>
          <p className="m-0 text-[11px] text-tg-hint truncate">{animal.species_name} · ₽{fmt(animal.income)}/мин</p>
        </div>
      </div>
      <div className="mt-[6px] flex min-w-0 items-center justify-between gap-2">
        {life ? (
          <p className="m-0 min-w-0 truncate text-[10.5px] font-bold tabular-nums" style={{ color: life.color }}>
            ⏳ {life.label}
          </p>
        ) : <span />}
        <GeneDots animal={animal} />
      </div>
    </div>
  );
});

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
