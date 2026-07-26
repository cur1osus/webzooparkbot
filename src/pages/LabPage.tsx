import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { AnimalArt } from '@/components/AnimalArt';
import { AnimalFavoriteButton } from '@/components/AnimalFavoriteButton';
import { PageHeader } from '@/components/PageHeader';
import type { Animal, BreedResult, BreedingAnimal, GameState, GeneTier, InheritedGene } from '@/types';
import { apiBreed, apiGetBreedingAnimals, apiSetAnimalFavorite } from '@/api';
import { fmt } from '@/utils/format';
import { GENE_META, SPECIES_RARITY_META } from '@/data/packs';
import { compareByQuality } from '@/lib/animalQuality';
import { useStoredChoice } from '@/hooks/useStoredChoice';

const GENETICS_BONUS_BY_LEVEL = [0, 1, 3, 6, 9, 12];
// Mirrors BREED_COST_INCOME_HOURS: a breeding attempt costs this many hours of the two
// parents' combined intrinsic income (their `base_income`), in rubles.
const BREED_COST_INCOME_HOURS = 4;
function breedCostRub(a: BreedingAnimal, b: BreedingAnimal): number {
  return Math.round(BREED_COST_INCOME_HOURS * 60 * (a.base_income + b.base_income));
}
const BREED_TIER_INDEX: Record<GeneTier, number> = { low: 0, medium: 1, high: 2 };
type PickerSort = 'new' | 'income' | 'quality' | 'reproduction';
const PICKER_SORTS: Array<{ id: PickerSort; label: string }> = [
  { id: 'new',           label: 'Новые' },
  { id: 'income',       label: 'Доход' },
  { id: 'quality',      label: 'Качество' },
  { id: 'reproduction', label: 'Размножение' },
];
const PICKER_SORT_IDS = PICKER_SORTS.map(option => option.id);

function breedRate(a: BreedingAnimal | null, b: BreedingAnimal | null, geneticsLevel: number): number | null {
  if (!a || !b) return null;
  const baseRate = (30 + 15 * (BREED_TIER_INDEX[a.reproduction] + BREED_TIER_INDEX[b.reproduction])) / 100;
  const bonus = GENETICS_BONUS_BY_LEVEL[Math.min(Math.max(geneticsLevel, 0), 5)] ?? 0;
  return Math.min(0.95, baseRate + bonus / 100);
}

const GENE_STAT_ROWS: Array<{ key: keyof typeof GENE_META; short: string; label: string }> = [
  { key: 'survival', short: 'Выж', label: 'Выживание' },
  { key: 'reproduction', short: 'Разм', label: 'Размножение' },
  { key: 'appearance', short: 'Вид', label: 'Внешний вид' },
  { key: 'size_trait', short: 'Размер', label: 'Размер' },
];

function GeneStats({ animal, compact = false }: { animal: BreedingAnimal; compact?: boolean }) {
  return (
    <div className={`grid grid-cols-2 gap-x-2 gap-y-1 ${compact ? 'text-[10px]' : 'text-[11px]'}`}>
      {GENE_STAT_ROWS.map(({ key, short }) => {
        const meta = GENE_META[key][animal[key]];
        return <span key={key} className="truncate" style={{ color: meta.color }}>{short}: {meta.label}</span>;
      })}
    </div>
  );
}

function GeneComparison({ parentA, parentB }: { parentA: BreedingAnimal; parentB: BreedingAnimal }) {
  return (
    <div className="rounded-2xl p-3" style={{ background: 'rgba(var(--c-purple-rgb),0.07)', border: '1px solid rgba(var(--c-purple-rgb),0.2)' }}>
      <p className="m-0 text-[12px] font-extrabold">Сравнение родителей</p>
      <div className="mt-2 grid grid-cols-[76px_minmax(0,1fr)_minmax(0,1fr)] gap-2 items-center text-[10px]">
        <span />
        <span className="truncate font-bold text-tg-hint">{parentA.name}</span>
        <span className="truncate font-bold text-tg-hint">{parentB.name}</span>
        {GENE_STAT_ROWS.map(({ key, label }) => {
          const metaA = GENE_META[key][parentA[key]];
          const metaB = GENE_META[key][parentB[key]];
          return (
            <div key={key} className="contents">
              <span className="text-tg-hint">{label}</span>
              <span className="truncate font-extrabold" style={{ color: metaA.color }}>{metaA.label}</span>
              <span className="truncate font-extrabold" style={{ color: metaB.color }}>{metaB.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function InheritanceCard({ genes }: { genes: InheritedGene[] }) {
  return (
    <div className="rounded-2xl p-3" style={{ background: 'rgba(var(--c-purple-rgb),0.08)', border: '1px solid rgba(var(--c-purple-rgb),0.22)' }}>
      <p className="m-0 text-[13px] font-extrabold">🧬 Какие гены получил детёныш</p>
      <p className="m-0 mt-1 text-[11px] text-tg-hint">Здесь видно, от какого родителя пришло каждое свойство.</p>
      <div className="mt-3 flex flex-col gap-2">
        {genes.map(entry => {
          const meta = GENE_META[entry.gene][entry.value];
          const parentAMeta = GENE_META[entry.gene][entry.parent_a_value];
          const parentBMeta = GENE_META[entry.gene][entry.parent_b_value];
          const geneLabel = GENE_STAT_ROWS.find(row => row.key === entry.gene)?.short ?? entry.gene;
          return (
            <div key={entry.gene} className="rounded-xl px-3 py-2" style={{ background: 'rgba(0,0,0,0.12)' }}>
              <div className="flex items-center justify-between gap-2"><span className="text-[11px] font-bold text-tg-hint">{geneLabel}</span><span className="text-[11px] font-extrabold" style={{ color: meta.color }}>{meta.label}</span></div>
              <p className="m-0 mt-1 text-[10px] text-tg-hint">{entry.parent_a_name}: <span style={{ color: parentAMeta.color }}>{parentAMeta.label}</span> · {entry.parent_b_name}: <span style={{ color: parentBMeta.color }}>{parentBMeta.label}</span></p>
              <p className="m-0 mt-1 text-[10px] font-bold" style={{ color: entry.source === 'both' ? 'var(--c-purple)' : 'var(--c-green)' }}>Получено от: {entry.source_name}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Animal mini-card for result display ─────────────────────────────────────

function AnimalResultCard({ animal }: { animal: Animal }) {
  const rarity = SPECIES_RARITY_META[animal.species_rarity];
  const genes: [keyof typeof GENE_META, GeneTier][] = [
    ['survival', animal.survival], ['reproduction', animal.reproduction],
    ['appearance', animal.appearance], ['size_trait', animal.size_trait],
  ];
  return (
    <div className="rounded-2xl p-4 flex flex-col gap-3"
         style={{ background: `linear-gradient(135deg, ${rarity.color}18, var(--surface-subtle))`, border: `1px solid ${rarity.color}45` }}>
      <div className="flex items-center gap-3">
        <div className="w-14 h-14 rounded-2xl grid place-items-center overflow-hidden shrink-0"
             style={{ background: `${rarity.color}18`, border: `1px solid ${rarity.color}40` }}>
          <AnimalArt animal={animal} size={52} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="m-0 font-extrabold text-[15px] truncate">{animal.name}</p>
          <p className="m-0 text-[11px] truncate" style={{ color: 'var(--tg-theme-hint-color)' }}>{animal.species_name}</p>
          <div className="mt-[3px] flex items-center gap-2">
            <span className="px-[7px] py-[1px] rounded-full text-[10px] font-extrabold"
                  style={{ background: `${rarity.color}22`, color: rarity.color, border: `1px solid ${rarity.color}55` }}>
              {rarity.label}
            </span>
            <span className="text-[11px] font-bold" style={{ color: 'var(--c-green)' }}>₽{fmt(animal.income)}/мин</span>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-[6px]">
        {genes.map(([key, val]) => {
          const meta = GENE_META[key][val];
          return (
            <div key={key} className="flex items-center gap-2 px-3 py-[7px] rounded-xl"
                 style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 7%, transparent)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)' }}>
              <div className="w-2 h-2 rounded-full shrink-0" style={{ background: meta.color }} />
              <span className="text-[10px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                {key === 'survival' ? 'Выж' : key === 'reproduction' ? 'Разм' : key === 'appearance' ? 'Вид' : 'Размер'}
              </span>
              <span className="ml-auto text-[11px] font-bold" style={{ color: meta.color }}>
                {meta.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Parent selector card ─────────────────────────────────────────────────────

function ParentSlot({ label, animal, onClick }: {
  label: string;
  animal: BreedingAnimal | null;
  onClick: () => void;
}) {
  if (!animal) {
    return (
      <button onClick={onClick}
              className="flex-1 rounded-2xl border-none cursor-pointer flex flex-col items-center justify-center gap-2 py-6"
              style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 7%, transparent)', border: '1px dashed color-mix(in srgb, var(--tg-theme-hint-color) 25%, transparent)' }}>
        <span className="text-[32px]">🐾</span>
        <span className="text-[12px] font-bold" style={{ color: 'var(--tg-theme-hint-color)' }}>{label}</span>
      </button>
    );
  }

  const rarity = SPECIES_RARITY_META[animal.species_rarity];
  return (
    <button onClick={onClick}
            className="flex-1 rounded-2xl border-none cursor-pointer flex flex-col gap-3 p-3 text-left"
            style={{ background: `${rarity.color}12`, border: `1px solid ${rarity.color}40` }}>
      <div className="grid grid-cols-[64px_minmax(0,1fr)] items-center gap-3">
        <div className="w-16 h-16 rounded-2xl grid place-items-center overflow-hidden shrink-0"
             style={{ background: `${rarity.color}18` }}>
          <AnimalArt animal={animal} size={58} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="m-0 text-[13px] font-bold leading-tight break-words">{animal.name}</p>
          <p className="m-0 mt-1 text-[10px] leading-tight break-words" style={{ color: 'var(--tg-theme-hint-color)' }}>
            {animal.species_name}
          </p>
        </div>
      </div>
      <span className="text-[10px] px-3 py-[6px] rounded-xl self-start"
            style={{ background: 'rgba(143,149,171,0.15)', color: 'var(--tg-theme-hint-color)' }}>
        сменить
      </span>
    </button>
  );
}

// ─── Animal picker overlay ────────────────────────────────────────────────────

const PICKER_ROW_HEIGHT = 96;
const PICKER_OVERSCAN = 8;

function AnimalPicker({ animals, tgId, exclude, mateSpeciesCode, onPick, onToggleFavorite, favoriteOverrides, favoriteBusyIds, onClose }: {
  animals: BreedingAnimal[];
  tgId: number;
  exclude: number | null;
  // When the other parent is already chosen, only its species can breed with it.
  mateSpeciesCode: string | null;
  onPick: (a: BreedingAnimal) => void;
  onToggleFavorite: (animal: BreedingAnimal) => void;
  favoriteOverrides: ReadonlyMap<number, boolean>;
  favoriteBusyIds: ReadonlySet<number>;
  onClose: () => void;
}) {
  const [query, setQuery] = useState('');
  const [sort, setSort] = useStoredChoice<PickerSort>('breed-picker-sort', tgId, PICKER_SORT_IDS, 'new');
  const [scrollTop, setScrollTop] = useState(0);
  const available = useMemo(() => {
    const breedable = animals.filter(a => a.can_breed && a.id !== exclude);
    // The first slot should never offer a dead end: if the player has no other
    // ready animal of that species, choosing it can only lead to an error later.
    if (!mateSpeciesCode) {
      const speciesCounts = new Map<string, number>();
      for (const animal of breedable) {
        speciesCounts.set(animal.species_code, (speciesCounts.get(animal.species_code) ?? 0) + 1);
      }
      return breedable.filter(animal => (speciesCounts.get(animal.species_code) ?? 0) > 1);
    }
    return breedable.filter(animal => animal.species_code === mateSpeciesCode);
  }, [animals, exclude, mateSpeciesCode]);
  // Keep the expensive sort independent from star clicks. A favorite change only needs
  // to repartition this already-sorted array, not sort all 11k animals again.
  const baseSorted = useMemo(() => [...available].sort((a, b) => {
      // Keep possible partners at the top after the first parent is chosen.
      // The picker still shows other species below them so the search remains useful.
      if (mateSpeciesCode) {
        const compatibleOrder = Number(b.species_code === mateSpeciesCode) - Number(a.species_code === mateSpeciesCode);
        if (compatibleOrder !== 0) return compatibleOrder;
      }
      if (sort === 'income') return b.income - a.income;
      // Самые редкие с лучшими генами сверху, обычные со слабыми — внизу.
      if (sort === 'quality') return compareByQuality(a, b);
      if (sort === 'reproduction') return BREED_TIER_INDEX[b.reproduction] - BREED_TIER_INDEX[a.reproduction] || b.income - a.income;
      return new Date(b.acquired_at).getTime() - new Date(a.acquired_at).getTime() || b.income - a.income;
    }), [available, mateSpeciesCode, sort]);
  const sorted = useMemo(() => {
    const favorites: BreedingAnimal[] = [];
    const regular: BreedingAnimal[] = [];
    for (const animal of baseSorted) {
      if (favoriteOverrides.get(animal.id) ?? animal.is_favorite) favorites.push(animal);
      else regular.push(animal);
    }
    return favorites.length === 0 ? regular : favorites.concat(regular);
  }, [baseSorted, favoriteOverrides]);
  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return needle
      ? sorted.filter(a => `${a.name} ${a.species_name}`.toLocaleLowerCase().includes(needle))
      : sorted;
  }, [query, sorted]);
  const effectiveScrollTop = Math.min(scrollTop, Math.max(0, filtered.length * PICKER_ROW_HEIGHT - 420));
  const visibleStart = Math.max(0, Math.floor(effectiveScrollTop / PICKER_ROW_HEIGHT) - PICKER_OVERSCAN);
  const visibleEnd = Math.min(
    filtered.length,
    Math.ceil((effectiveScrollTop + 420) / PICKER_ROW_HEIGHT) + PICKER_OVERSCAN,
  );

  return createPortal(
    <div className="modal-backdrop fixed inset-0 z-[300] flex items-end justify-center" onClick={onClose}>
      <div className="sheet-panel w-full max-w-[480px] rounded-t-3xl p-4 flex flex-col gap-3 max-h-[75vh] overflow-hidden"
           onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-1">
          <div>
            <p className="m-0 font-extrabold text-[15px]">Выбери родителя</p>
            <p className="m-0 mt-1 text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
              {filtered.length} из {available.length} доступных
            </p>
          </div>
          <button onClick={onClose} aria-label="Закрыть" className="tap-target -mr-2 border-none bg-transparent text-[18px] cursor-pointer"
                  style={{ color: 'var(--tg-theme-hint-color)' }}>✕</button>
        </div>

        {available.length > 0 && (
          <>
            <label className="flex items-center gap-2 min-h-11 rounded-xl px-3"
                   style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 14%, transparent)' }}>
              <span className="text-[16px]" aria-hidden="true">⌕</span>
              <input
                value={query}
                onChange={event => setQuery(event.target.value)}
                placeholder="Найти по имени или виду"
                aria-label="Поиск животного"
                className="min-w-0 flex-1 bg-transparent border-none outline-none text-[13px]"
              />
              {query && <button type="button" onClick={() => setQuery('')} aria-label="Очистить поиск" className="border-none bg-transparent text-[16px] cursor-pointer" style={{ color: 'var(--tg-theme-hint-color)' }}>×</button>}
            </label>
            <div className="flex shrink-0 min-h-10 gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Сортировка животных">
              {PICKER_SORTS.map(option => (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => setSort(option.id)}
                  role="tab"
                  aria-selected={sort === option.id}
                  className="shrink-0 min-h-10 rounded-xl border-none px-3 text-[11px] font-bold cursor-pointer"
                  style={{ background: sort === option.id ? 'rgba(var(--c-purple-rgb),0.18)' : 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)', color: sort === option.id ? 'var(--c-purple)' : 'var(--tg-theme-hint-color)' }}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </>
        )}

        {available.length === 0 ? (
          <p className="text-center py-6 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
              Нет животных с доступным партнёром<br />
              <span className="text-[11px]">Нужны два животных одного вида, готовых к скрещиванию сегодня</span>
          </p>
        ) : filtered.length === 0 ? (
          <p className="text-center py-6 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Ничего не найдено
          </p>
        ) : (
          <div
            className="min-h-0 overflow-y-auto overscroll-contain"
            style={{ height: 'min(48vh, 420px)' }}
            onScroll={event => setScrollTop(event.currentTarget.scrollTop)}
          >
            <div className="relative" style={{ height: filtered.length * PICKER_ROW_HEIGHT }}>
              {filtered.slice(visibleStart, visibleEnd).map((a, offset) => {
                const index = visibleStart + offset;
                const rarity = SPECIES_RARITY_META[a.species_rarity];
                const isFavorite = favoriteOverrides.get(a.id) ?? a.is_favorite;
                return (
                  <div key={a.id} className="absolute left-0 right-0" style={{ top: index * PICKER_ROW_HEIGHT, height: PICKER_ROW_HEIGHT, paddingBottom: 8 }}>
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => onPick(a)}
                      onKeyDown={event => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          onPick(a);
                        }
                      }}
                      className="relative flex h-full items-center gap-3 px-3 pr-14 rounded-xl text-left w-full"
                      style={{
                        background: 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)',
                        border: isFavorite ? '1px solid #f3b53f' : '1px solid transparent',
                        boxShadow: isFavorite ? '0 0 12px rgba(243, 181, 63, 0.22)' : 'none',
                        cursor: 'pointer',
                      }}
                    >
                      <div className="w-11 h-11 rounded-xl grid place-items-center overflow-hidden shrink-0"
                           style={{ background: `${rarity.color}18`, border: `1px solid ${rarity.color}35` }}>
                        <AnimalArt animal={a} size={40} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="m-0 text-[13px] font-bold truncate">
                          {a.name} <span className="font-normal" style={{ color: 'var(--tg-theme-hint-color)' }}>· {a.species_name}</span>
                        </p>
                        <div className="mt-1"><GeneStats animal={a} compact /></div>
                        <p className="m-0 text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>Доход: ₽{fmt(a.income)}/мин</p>
                      </div>
                      <AnimalFavoriteButton
                        className="absolute right-2 top-1/2 -translate-y-1/2"
                        isFavorite={isFavorite}
                        busy={favoriteBusyIds.has(a.id)}
                        disableWhileBusy={false}
                        onToggle={() => onToggleFavorite(a)}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function LabPage({ gs, onRefresh, onPatchState }: { gs: GameState; onRefresh: () => void; onPatchState: (patch: Partial<GameState>) => void }) {
  const [animals, setAnimals]   = useState<BreedingAnimal[]>([]);
  const [loading, setLoading]   = useState(true);
  const [parent1, setParent1]   = useState<BreedingAnimal | null>(null);
  const [parent2, setParent2]   = useState<BreedingAnimal | null>(null);
  const [picking, setPicking]   = useState<1 | 2 | null>(null);
  const [breeding, setBreeding] = useState(false);
  const [result, setResult]     = useState<BreedResult | null>(null);
  const [error, setError]       = useState<string | null>(null);
  const [favoriteOverrides, setFavoriteOverrides] = useState<Map<number, boolean>>(() => new Map());
  const [favoriteBusyIds, setFavoriteBusyIds] = useState<Set<number>>(() => new Set());
  const favoriteRequests = useRef(new Map<number, { desired: boolean; previousOverride: boolean | undefined }>());

  const load = async () => {
    try {
      const { animals } = await apiGetBreedingAnimals();
      setAnimals(animals);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  async function toggleFavorite(animal: BreedingAnimal) {
    const request = favoriteRequests.current.get(animal.id);
    const previousOverride = request?.previousOverride ?? favoriteOverrides.get(animal.id);
    const current = request?.desired ?? (previousOverride ?? animal.is_favorite);
    const next = !current;

    // The picker is optimistic and O(1): do not copy the entire breeding list just to
    // flip one boolean. Independent ids can be clicked while their requests are in flight;
    // repeated clicks on one id update the queued target instead of being dropped.
    setFavoriteOverrides(previous => new Map(previous).set(animal.id, next));
    if (request) {
      request.desired = next;
      return;
    }

    const nextRequest = { desired: next, previousOverride };
    favoriteRequests.current.set(animal.id, nextRequest);
    setFavoriteBusyIds(previous => new Set(previous).add(animal.id));
    try {
      while (true) {
        const result = await apiSetAnimalFavorite(animal.id, nextRequest.desired);
        if (nextRequest.desired !== result.is_favorite) continue;

        // Keep the already-loaded full zoo state in sync without re-fetching and parsing
        // the whole game state after every star click. Defer this O(n) immutable patch so
        // it can never sit on the interaction's critical path; the picker already has the
        // authoritative optimistic value on screen.
        window.setTimeout(() => {
          onPatchState({
            animals: gs.animals.map(item => item.id === animal.id ? { ...item, is_favorite: result.is_favorite } : item),
          });
        }, 0);
        break;
      }
    } catch (e) {
      setFavoriteOverrides(previous => {
        const nextOverrides = new Map(previous);
        if (nextRequest.previousOverride === undefined) nextOverrides.delete(animal.id);
        else nextOverrides.set(animal.id, nextRequest.previousOverride);
        return nextOverrides;
      });
      setError(e instanceof Error ? e.message : 'Не удалось изменить избранное');
    } finally {
      favoriteRequests.current.delete(animal.id);
      setFavoriteBusyIds(previous => {
        const nextBusy = new Set(previous);
        nextBusy.delete(animal.id);
        return nextBusy;
      });
    }
  }

  const handleBreed = async () => {
    if (!parent1 || !parent2 || breeding) return;
    setBreeding(true);
    setError(null);
    setResult(null);
    try {
      const res = await apiBreed(parent1.id, parent2.id);
      setResult(res);
      // The response contains the child, so patch the compact local picker state without
      // downloading the entire ready-pair list again.
      const fresh = animals.map(animal => (
        animal.id === parent1.id || animal.id === parent2.id
          ? { ...animal, can_breed: false }
          : animal
      ));
      if (res.animal && !fresh.some(animal => animal.id === res.animal?.id)) {
        fresh.push(res.animal);
      }
      setAnimals(fresh);
      const p1 = fresh.find(a => a.id === parent1.id);
      const p2 = fresh.find(a => a.id === parent2.id);
      if (p1) setParent1(p1);
      if (p2) setParent2(p2);
      onRefresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBreeding(false);
    }
  };

  const rate = breedRate(parent1, parent2, gs.genetics_level);
  const cost = parent1 && parent2 ? breedCostRub(parent1, parent2) : null;
  const canAfford = cost === null || gs.rub >= cost;
  const canBreed = parent1?.can_breed && parent2?.can_breed && canAfford && !breeding;

  return (
    <div className="page-content-safe flex flex-col gap-4">

      <PageHeader
        emoji="🧪"
        title="Лаборатория"
        subtitle="Скрещивай животных — каждое животное 1 раз в день"
        accent="var(--c-purple-rgb)"
      />

      <div className="px-[14px] flex flex-col gap-4">

      {loading ? (
        <div className="flex justify-center py-8"><div className="spinner" /></div>
      ) : (
        <>
          {/* Parent selectors */}
          <div className="flex gap-3">
            <ParentSlot label="Родитель 1" animal={parent1} onClick={() => setPicking(1)} />
            <div className="flex items-center text-[24px]" style={{ color: 'var(--tg-theme-hint-color)' }}>×</div>
            <ParentSlot label="Родитель 2" animal={parent2} onClick={() => setPicking(2)} />
          </div>

          {parent1 && parent2 && <GeneComparison parentA={parent1} parentB={parent2} />}
          {parent1 && parent2 && (
            <button
              type="button"
              onClick={() => { setParent1(null); setParent2(null); setResult(null); setError(null); }}
              className="self-center rounded-xl border-none px-4 py-2 text-[11px] font-bold"
              style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 10%, transparent)', color: 'var(--tg-theme-hint-color)' }}
            >
              ↺ Сбросить выбор
            </button>
          )}

          {/* Success probability */}
          {rate !== null && (
            <div className="rounded-2xl px-4 py-3 flex items-center justify-between"
                 style={{ background: 'rgba(var(--c-blue-rgb),0.08)', border: '1px solid rgba(var(--c-blue-rgb),0.2)' }}>
              <span className="text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                Шанс успеха
              </span>
              <span className="text-[22px] font-extrabold" style={{ color: 'var(--c-blue)' }}>
                {Math.round(rate * 100)}%
              </span>
            </div>
          )}

          {/* Cost of an attempt (charged whether or not it succeeds) */}
          {cost !== null && (
            <div className="rounded-2xl px-4 py-3 flex items-center justify-between"
                 style={{ background: 'rgba(var(--c-green-rgb),0.08)', border: '1px solid rgba(var(--c-green-rgb),0.2)' }}>
              <span className="text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                Стоимость попытки
              </span>
              <span className="text-[20px] font-extrabold" style={{ color: canAfford ? 'var(--c-green)' : 'var(--c-red)' }}>
                ₽{fmt(cost)}
              </span>
            </div>
          )}

          {/* Breed button */}
          <button
            onClick={() => void handleBreed()}
            disabled={!canBreed}
            className="w-full py-[14px] rounded-2xl border-none font-extrabold text-[15px] cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            style={{
              background: canBreed
                ? 'linear-gradient(135deg, var(--c-purple), #9b3bd6)'
                : 'color-mix(in srgb, var(--tg-theme-hint-color) 15%, transparent)',
              color: canBreed ? 'var(--tg-theme-button-text-color)' : 'var(--tg-theme-hint-color)',
            }}
          >
            {breeding ? '🧬 Скрещиваем...' : '🧬 Скрестить'}
          </button>

          {!result && parent1 && parent2 && (!parent1.can_breed || !parent2.can_breed) && (
            <p className="m-0 text-center text-[12px]" style={{ color: 'var(--c-amber)' }}>
              ⚠️ Одно из животных уже скрещивалось сегодня
            </p>
          )}

          {!result && parent1 && parent2 && parent1.can_breed && parent2.can_breed && !canAfford && (
            <p className="m-0 text-center text-[12px]" style={{ color: 'var(--c-red)' }}>
              ⚠️ Недостаточно рублей: нужно ₽{fmt(cost ?? 0)}
            </p>
          )}

          {error && (
            <div className="rounded-xl px-4 py-3 text-sm"
                 style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.25)', color: 'var(--c-red)' }}>
              {error}
            </div>
          )}

          {/* Result */}
          {result && (
            <div className="flex flex-col gap-3">
              <div
                className="rounded-2xl px-4 py-3 text-center font-extrabold text-[15px]"
                style={result.success
                  ? { background: 'rgba(var(--c-green-rgb),0.12)', border: '1px solid rgba(var(--c-green-rgb),0.3)', color: 'var(--c-green)' }
                  : { background: 'rgba(var(--c-red-rgb),0.08)', border: '1px solid rgba(var(--c-red-rgb),0.2)', color: 'var(--c-red)' }
                }
              >
                {result.success ? '✅ Успех! Родился новый детёныш' : '❌ Попытка не удалась'}
              </div>
              {result.success && result.animal && (
                <>
                  {result.inherited_genes && <InheritanceCard genes={result.inherited_genes} />}
                  <AnimalResultCard animal={result.animal} />
                </>
              )}
            </div>
          )}

          {/* Info */}
          <div className="card">
            <p className="m-0 mb-2 font-bold text-[13px]">Правила скрещивания</p>
            <div className="flex flex-col gap-[6px]">
              {[
                ['🧬', 'Каждое животное скрещивается 1 раз в день'],
                ['📊', 'Шанс зависит от гена «Размножение» обоих родителей'],
                ['⚖️', 'Наследование: худший ген побеждает в 60% случаев'],
                ['🌍', 'Среда обитания — случайно от одного из родителей'],
              ].map(([icon, text]) => (
                <div key={text as string} className="flex items-start gap-2">
                  <span className="text-[14px] shrink-0 mt-[1px]">{icon}</span>
                  <span className="text-[12px] leading-relaxed" style={{ color: 'var(--tg-theme-hint-color)' }}>{text}</span>
                </div>
              ))}
            </div>
          </div>

        </>
      )}

      </div>

      {/* Picker overlay */}
      {picking !== null && (
        <AnimalPicker
          animals={animals}
          tgId={gs.tg_id}
          exclude={picking === 1 ? parent2?.id ?? null : parent1?.id ?? null}
          mateSpeciesCode={picking === 1 ? parent2?.species_code ?? null : parent1?.species_code ?? null}
          onPick={a => {
            if (picking === 1) setParent1(a);
            else setParent2(a);
            setResult(null);
            setPicking(null);
          }}
          onToggleFavorite={animal => void toggleFavorite(animal)}
          favoriteOverrides={favoriteOverrides}
          favoriteBusyIds={favoriteBusyIds}
          onClose={() => setPicking(null)}
        />
      )}
    </div>
  );
}
