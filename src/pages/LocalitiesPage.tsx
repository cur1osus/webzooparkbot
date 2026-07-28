import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import type { GameState, Habitat, Locality, LocalityAnimal, LocalitiesInfo } from '@/types';
import {
  apiAssignLocality,
  apiAssignMatchingLocality,
  apiBuyLocality,
  apiGetLocalities,
  apiGetLocalityAnimalsPage,
} from '@/api';
import { fmt } from '@/utils/format';
import { AnimalArt } from '@/components/AnimalArt';

const HABITAT_INFO: Record<Habitat, { emoji: string; name: string; color: string }> = {
  desert:     { emoji: '🏜️', name: 'Пустыня',   color: 'var(--c-gold)' },
  mountains:  { emoji: '⛰️', name: 'Горы',       color: 'var(--tg-theme-hint-color)' },
  forest:     { emoji: '🌲', name: 'Густой лес', color: 'var(--c-green)' },
  fields:     { emoji: '🌾', name: 'Поля',        color: 'var(--c-teal)' },
  antarctica: { emoji: '🏔️', name: 'Антарктида', color: 'var(--c-cyan)' },
};

const ALL_HABITATS: Habitat[] = ['desert', 'mountains', 'forest', 'fields', 'antarctica'];
const PAGE_SIZE = 120;
const BONUS_MULTIPLIER = 1.5;

function mergeUnique(current: LocalityAnimal[], incoming: LocalityAnimal[]) {
  const known = new Set(current.map(animal => animal.id));
  return current.concat(incoming.filter(animal => !known.has(animal.id)));
}

function AnimalChip({ animal, onRemove }: { animal: LocalityAnimal; onRemove: () => void }) {
  const habitat = HABITAT_INFO[animal.habitat];
  return (
    <div className="flex items-center gap-2 px-3 py-[7px] rounded-xl" style={{ background: `${habitat.color}12`, border: `1px solid ${habitat.color}25` }}>
      <AnimalArt animal={animal} size={32} className="shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="m-0 text-[12px] font-bold truncate">
          {animal.name} <span className="font-normal text-tg-hint">· {animal.species_name}</span>
        </p>
        <div className="flex items-center gap-[6px]">
          <span className="text-[11px] font-bold text-[var(--c-green)]">₽{fmt(animal.income)}/мин</span>
          {animal.habitat_bonus && <span className="text-[10px] font-bold text-[var(--c-gold)]">(бонус среды)</span>}
        </div>
      </div>
      <button onClick={onRemove} aria-label={`Убрать ${animal.name} из местности`} className="w-6 h-6 rounded-full border-none grid place-items-center cursor-pointer text-[13px]" style={{ background: 'rgba(var(--c-red-rgb),0.12)', color: 'var(--c-red)' }}>×</button>
    </div>
  );
}

function LocalityCard({
  locality,
  unassignedCount,
  animals,
  hasMore,
  loadingAnimals,
  assigningMatching,
  onOpen,
  onLoadMore,
  onAdd,
  onAssignMatching,
  onRemove,
}: {
  locality: Locality;
  unassignedCount: number;
  animals: LocalityAnimal[];
  hasMore: boolean;
  loadingAnimals: boolean;
  assigningMatching: boolean;
  onOpen: () => void;
  onLoadMore: () => void;
  onAdd: () => void;
  onAssignMatching: () => void;
  onRemove: (id: number) => void;
}) {
  const habitat = HABITAT_INFO[locality.habitat];
  const hasAnimals = locality.animals_count > 0;
  const [collapsed, setCollapsed] = useState(true);

  const toggle = () => {
    if (!hasAnimals) return;
    const opening = collapsed;
    setCollapsed(!collapsed);
    if (opening && animals.length === 0) onOpen();
  };

  return (
    <div className="rounded-2xl overflow-hidden" style={{ background: 'rgba(26,29,43,0.9)', border: `1px solid color-mix(in srgb, ${habitat.color} 30%, transparent)` }}>
      <div onClick={toggle} className="w-full flex items-center gap-3 px-4 py-4 text-left" style={{ background: `linear-gradient(90deg, color-mix(in srgb, ${habitat.color} 48%, transparent) 0%, color-mix(in srgb, ${habitat.color} 20%, transparent) 55%, transparent 100%)`, cursor: hasAnimals ? 'pointer' : 'default' }}>
        {hasAnimals && <span className="text-[12px] shrink-0 transition-transform" style={{ color: habitat.color, transform: collapsed ? 'rotate(-90deg)' : 'none' }}>▾</span>}
        <div className="w-11 h-11 rounded-xl grid place-items-center text-[24px] shrink-0" style={{ background: `color-mix(in srgb, ${habitat.color} 24%, transparent)`, border: `1px solid color-mix(in srgb, ${habitat.color} 42%, transparent)` }}>{habitat.emoji}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-[7px]">
            <p className="m-0 font-extrabold text-[15px]">{habitat.name}</p>
            <span className="text-[13px] font-black" style={{ color: habitat.color }}>{locality.animals_count}</span>
          </div>
          {locality.income_rub_per_min > 0
            ? <p className="m-0 text-[11px] text-[var(--c-green)]">₽{fmt(locality.income_rub_per_min)}/мин суммарно</p>
            : <p className="m-0 text-[11px] text-tg-hint">Пусто</p>}
        </div>
        {unassignedCount > 0 && (
          <button onClick={event => { event.stopPropagation(); onAdd(); }} className="text-[13px] font-bold shrink-0 border-none bg-transparent cursor-pointer px-1" style={{ color: habitat.color }}>+ добавить</button>
        )}
      </div>

      {hasAnimals && !collapsed && (
        <div className="flex flex-col gap-[6px] px-4 py-3">
          {loadingAnimals && animals.length === 0 ? <div className="flex justify-center py-3"><div className="spinner" /></div> : animals.map(animal => (
            <AnimalChip key={animal.id} animal={animal} onRemove={() => onRemove(animal.id)} />
          ))}
          {hasMore && (
            <button type="button" onClick={onLoadMore} disabled={loadingAnimals} className="mt-1 w-full rounded-xl border-none py-2 text-[11px] font-bold cursor-pointer disabled:opacity-50" style={{ background: 'var(--surface-subtle)', color: habitat.color }}>
              {loadingAnimals ? 'Загружаем…' : `Показать ещё · ${Math.max(0, locality.animals_count - animals.length)}`}
            </button>
          )}
        </div>
      )}

      {locality.matching_count > 0 && (
        <div className="px-4 pt-3 pb-3">
          <button onClick={onAssignMatching} disabled={assigningMatching} data-testid={`assign-matching-${locality.habitat}`} className="w-full min-h-11 rounded-xl border-none cursor-pointer font-extrabold text-[12px] disabled:opacity-55 disabled:cursor-wait" style={{ background: `color-mix(in srgb, ${habitat.color} 16%, transparent)`, color: habitat.color, border: `1px solid color-mix(in srgb, ${habitat.color} 30%, transparent)` }}>
            {assigningMatching ? 'Распределяем...' : `Распределить сразу · ${locality.matching_count}`}
          </button>
        </div>
      )}

      {!hasAnimals && unassignedCount === 0 && <p className="m-0 px-4 py-3 text-center text-[12px] text-tg-hint">Нет свободных животных</p>}
    </div>
  );
}

function AnimalPicker({ localityHabitat, onPick, onClose }: {
  localityHabitat: Habitat;
  onPick: (animal: LocalityAnimal) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState('');
  const [animals, setAnimals] = useState<LocalityAnimal[]>([]);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const requestSeq = useRef(0);

  useEffect(() => {
    const seq = ++requestSeq.current;
    const timer = window.setTimeout(() => {
      setLoading(true);
      void apiGetLocalityAnimalsPage({ limit: PAGE_SIZE, query: query.trim(), preferredHabitat: localityHabitat })
        .then(result => {
          if (seq !== requestSeq.current) return;
          setAnimals(result.animals);
          setNextOffset(result.next_offset);
        })
        .finally(() => { if (seq === requestSeq.current) setLoading(false); });
    }, 140);
    return () => window.clearTimeout(timer);
  }, [localityHabitat, query]);

  const loadMore = async () => {
    if (loading || nextOffset === null) return;
    setLoading(true);
    try {
      const result = await apiGetLocalityAnimalsPage({ offset: nextOffset, limit: PAGE_SIZE, query: query.trim(), preferredHabitat: localityHabitat });
      setAnimals(current => mergeUnique(current, result.animals));
      setNextOffset(result.next_offset);
    } finally {
      setLoading(false);
    }
  };

  return createPortal(
    <div className="modal-backdrop fixed inset-0 z-[300] flex items-end justify-center" onClick={onClose}>
      <div className="sheet-panel w-full max-w-[480px] rounded-t-3xl p-4 flex flex-col gap-3 max-h-[76vh] overflow-y-auto" onClick={event => event.stopPropagation()}>
        <div className="flex items-center justify-between">
          <p className="m-0 font-extrabold text-[15px]">Выбери животное</p>
          <button onClick={onClose} aria-label="Закрыть" className="tap-target -mr-2 border-none bg-transparent text-[18px] cursor-pointer text-tg-hint">✕</button>
        </div>
        <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Поиск по имени или виду" className="w-full rounded-xl border-none px-3 py-2.5 text-[13px] bg-[var(--surface-subtle)] text-tg-text outline-none" />
        {loading && animals.length === 0 ? <div className="flex justify-center py-4"><div className="spinner" /></div> : animals.length === 0 ? (
          <p className="text-center py-4 text-[13px] text-tg-hint">Нет свободных животных</p>
        ) : animals.map(animal => {
          const habitat = HABITAT_INFO[animal.habitat];
          const isMatch = animal.habitat === localityHabitat;
          return (
            <button key={animal.id} onClick={() => onPick(animal)} className="flex items-center gap-3 px-3 py-[10px] rounded-xl border-none cursor-pointer text-left w-full" style={{ background: isMatch ? `${habitat.color}18` : 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)', border: `1px solid ${isMatch ? habitat.color + '35' : 'transparent'}` }}>
              <AnimalArt animal={animal} size={36} className="shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="text-[13px] font-bold truncate block">{animal.name} <span className="font-normal text-tg-hint">· {animal.species_name}</span></span>
                <span className="text-[11px] text-tg-hint">₽{fmt(animal.income)}/мин{isMatch && <span className="text-[var(--c-gold)]"> → ₽{fmt(Math.round(animal.income * BONUS_MULTIPLIER))} с бонусом</span>}</span>
              </div>
            </button>
          );
        })}
        {nextOffset !== null && <button type="button" onClick={() => void loadMore()} disabled={loading} className="w-full rounded-xl border-none py-2.5 text-[12px] font-bold cursor-pointer disabled:opacity-50 bg-[var(--surface-subtle)] text-tg-hint">{loading ? 'Загружаем…' : 'Показать ещё'}</button>}
      </div>
    </div>,
    document.body,
  );
}

export function LocalitiesPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [info, setInfo] = useState<LocalitiesInfo | null>(null);
  const [bucketAnimals, setBucketAnimals] = useState<Record<number, LocalityAnimal[]>>({});
  const [bucketNext, setBucketNext] = useState<Record<number, number | null>>({});
  const [unassignedAnimals, setUnassignedAnimals] = useState<LocalityAnimal[]>([]);
  const [unassignedNext, setUnassignedNext] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [buying, setBuying] = useState(false);
  const [selHabitat, setSelHab] = useState<Habitat | null>(null);
  const [assigningTo, setAssigning] = useState<{ localityId: number; habitat: Habitat } | null>(null);
  const [loadingBuckets, setLoadingBuckets] = useState<ReadonlySet<number>>(() => new Set());
  const loadingBucketsRef = useRef(new Set<number>());
  const [assigningMatchingIds, setAssigningMatchingIds] = useState<ReadonlySet<number>>(() => new Set());
  const assigningMatchingIdsRef = useRef(new Set<number>());
  const summarySeq = useRef(0);

  const refreshSummary = useCallback(async () => {
    const seq = ++summarySeq.current;
    const fresh = await apiGetLocalities();
    if (seq === summarySeq.current) setInfo(fresh);
    return fresh;
  }, []);

  const loadInitial = useCallback(async () => {
    try {
      setError(null);
      const [summary, unassigned] = await Promise.all([
        apiGetLocalities(),
        apiGetLocalityAnimalsPage({ limit: PAGE_SIZE }),
      ]);
      setInfo(summary);
      setUnassignedAnimals(unassigned.animals);
      setUnassignedNext(unassigned.next_offset);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось загрузить местности');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadInitial(); }, [loadInitial]);

  const loadBucket = async (localityId: number) => {
    if (loadingBucketsRef.current.has(localityId)) return;
    const current = bucketAnimals[localityId] ?? [];
    const knownNext = bucketNext[localityId];
    if (current.length > 0 && knownNext === null) return;
    loadingBucketsRef.current.add(localityId);
    setLoadingBuckets(previous => new Set(previous).add(localityId));
    try {
      const result = await apiGetLocalityAnimalsPage({ localityId, offset: current.length, limit: PAGE_SIZE });
      setBucketAnimals(previous => ({ ...previous, [localityId]: mergeUnique(previous[localityId] ?? [], result.animals) }));
      setBucketNext(previous => ({ ...previous, [localityId]: result.next_offset }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось загрузить животных');
    } finally {
      loadingBucketsRef.current.delete(localityId);
      setLoadingBuckets(previous => { const next = new Set(previous); next.delete(localityId); return next; });
    }
  };

  const loadMoreUnassigned = async () => {
    if (unassignedNext === null) return;
    const result = await apiGetLocalityAnimalsPage({ offset: unassignedNext, limit: PAGE_SIZE });
    setUnassignedAnimals(current => mergeUnique(current, result.animals));
    setUnassignedNext(result.next_offset);
  };

  const handleBuy = async () => {
    if (!selHabitat || buying) return;
    setBuying(true);
    setError(null);
    try {
      await apiBuyLocality(selHabitat);
      setSelHab(null);
      await refreshSummary();
      onRefresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось купить местность');
    } finally {
      setBuying(false);
    }
  };

  const handleAssign = async (animal: LocalityAnimal, localityId: number) => {
    setAssigning(null);
    const locality = info?.localities.find(item => item.id === localityId);
    const moved = locality && animal.habitat === locality.habitat
      ? { ...animal, habitat_bonus: true, income: Math.round(animal.income * BONUS_MULTIPLIER) }
      : animal;
    setUnassignedAnimals(current => current.filter(item => item.id !== animal.id));
    setBucketAnimals(current => ({ ...current, [localityId]: mergeUnique(current[localityId] ?? [], [moved]) }));
    try {
      await apiAssignLocality(animal.id, localityId);
      await refreshSummary();
      onRefresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось распределить животное');
      await loadInitial();
    }
  };

  const handleUnassign = async (animalId: number, localityId: number) => {
    const animal = (bucketAnimals[localityId] ?? []).find(item => item.id === animalId);
    if (animal) {
      setBucketAnimals(current => ({ ...current, [localityId]: (current[localityId] ?? []).filter(item => item.id !== animalId) }));
      const unassigned = animal.habitat_bonus
        ? { ...animal, habitat_bonus: false, income: Math.round(animal.income / BONUS_MULTIPLIER) }
        : animal;
      setUnassignedAnimals(current => mergeUnique(current, [unassigned]));
    }
    try {
      await apiAssignLocality(animalId, null);
      await refreshSummary();
      onRefresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось убрать животное');
      await loadInitial();
    }
  };

  const handleAssignMatching = async (locality: Locality) => {
    if (assigningMatchingIdsRef.current.has(locality.id)) return;
    assigningMatchingIdsRef.current.add(locality.id);
    setAssigningMatchingIds(previous => new Set(previous).add(locality.id));
    setInfo(current => current ? { ...current, localities: current.localities.map(item => item.id === locality.id ? { ...item, matching_count: 0 } : item) } : current);
    setUnassignedAnimals(current => current.filter(animal => animal.habitat !== locality.habitat));
    setBucketAnimals(current => {
      const next = { ...current };
      const moved: LocalityAnimal[] = [];
      for (const [key, animals] of Object.entries(current)) {
        const id = Number(key);
        if (id === locality.id) continue;
        moved.push(...animals.filter(animal => animal.habitat === locality.habitat));
        next[id] = animals.filter(animal => animal.habitat !== locality.habitat);
      }
      const fromUnassigned = unassignedAnimals.filter(animal => animal.habitat === locality.habitat);
      next[locality.id] = mergeUnique(next[locality.id] ?? [], [...moved, ...fromUnassigned].map(animal => ({ ...animal, habitat_bonus: true, income: animal.habitat_bonus ? animal.income : Math.round(animal.income * BONUS_MULTIPLIER) })));
      return next;
    });
    try {
      await apiAssignMatchingLocality(locality.id);
      await refreshSummary();
      onRefresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось распределить животных');
      await loadInitial();
    } finally {
      assigningMatchingIdsRef.current.delete(locality.id);
      setAssigningMatchingIds(previous => { const next = new Set(previous); next.delete(locality.id); return next; });
    }
  };

  return (
    <div className="px-[14px] pt-4 pb-4 flex flex-col gap-4">
      <div><p className="m-0 mb-[2px] font-extrabold text-[16px]">🌍 Местности</p><p className="m-0 text-[12px] text-tg-hint">Совпадение среды животного и местности даёт ×1.5 к доходу</p></div>
      <span className="self-start px-3 py-[5px] rounded-[20px] text-[13px] font-bold" style={{ background: 'rgba(var(--c-green-rgb),0.12)', color: 'var(--c-green)', border: '1px solid rgba(var(--c-green-rgb),0.25)' }}>₽ {fmt(gs.rub)}</span>
      {error && <div className="rounded-xl px-4 py-3 text-sm" style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.25)', color: 'var(--c-red)' }}>{error}</div>}

      {loading ? <div className="flex justify-center py-8"><div className="spinner" /></div> : info ? <>
        {info.localities.map(locality => (
          <LocalityCard
            key={locality.id}
            locality={locality}
            unassignedCount={info.unassigned_count}
            animals={bucketAnimals[locality.id] ?? []}
            hasMore={bucketNext[locality.id] !== null && (bucketAnimals[locality.id]?.length ?? 0) < locality.animals_count}
            loadingAnimals={loadingBuckets.has(locality.id)}
            assigningMatching={assigningMatchingIds.has(locality.id)}
            onOpen={() => void loadBucket(locality.id)}
            onLoadMore={() => void loadBucket(locality.id)}
            onAdd={() => setAssigning({ localityId: locality.id, habitat: locality.habitat })}
            onAssignMatching={() => void handleAssignMatching(locality)}
            onRemove={id => void handleUnassign(id, locality.id)}
          />
        ))}

        {info.unassigned_count > 0 && <div>
          <p className="m-0 mb-2 font-bold text-[13px]">Без местности <span className="ml-2 font-normal text-[12px] text-tg-hint">{info.unassigned_count} шт. — без бонуса ×1.5</span></p>
          <div className="rounded-2xl p-3 flex flex-col gap-[6px]" style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 6%, transparent)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)' }}>
            {unassignedAnimals.map(animal => <div key={animal.id} className="flex items-center gap-2 text-[12px]"><AnimalArt animal={animal} size={24} className="shrink-0" /><span className="font-semibold truncate">{animal.name}</span><span className="text-[10px] truncate text-tg-hint">{animal.species_name} {HABITAT_INFO[animal.habitat].emoji}</span><span className="ml-auto font-bold shrink-0 text-tg-hint">₽{fmt(animal.income)}/мин</span></div>)}
            {unassignedNext !== null && <button type="button" onClick={() => void loadMoreUnassigned()} className="w-full rounded-xl border-none py-2 text-[11px] font-bold cursor-pointer bg-[var(--surface-subtle)] text-tg-hint">Показать ещё · {Math.max(0, info.unassigned_count - unassignedAnimals.length)}</button>}
          </div>
        </div>}

        {info.next_price !== null ? <div className="rounded-2xl p-4 flex flex-col gap-3" style={{ background: 'rgba(var(--c-blue-rgb),0.08)', border: '1px solid rgba(var(--c-blue-rgb),0.2)' }}>
          <div className="flex items-center gap-2"><p className="m-0 font-extrabold text-[14px] flex-1">🔓 Открыть местность</p><span className="text-[13px] font-bold text-tg-hint">{info.next_price === 0 ? 'Бесплатно' : `₽${fmt(info.next_price)}`}</span></div>
          <div className="grid grid-cols-5 gap-[6px]">{ALL_HABITATS.map(habitatCode => { const taken = info.habitats_taken.includes(habitatCode); const selected = selHabitat === habitatCode; const habitat = HABITAT_INFO[habitatCode]; return <button key={habitatCode} onClick={() => !taken && setSelHab(selected ? null : habitatCode)} disabled={taken} className="flex flex-col items-center gap-1 py-[10px] rounded-xl cursor-pointer disabled:cursor-default" style={{ background: taken ? 'rgba(143,149,171,0.08)' : selected ? `${habitat.color}25` : `${habitat.color}10`, border: `1px solid ${taken ? 'rgba(143,149,171,0.15)' : selected ? habitat.color + '60' : habitat.color + '25'}`, opacity: taken ? 0.45 : 1 }}><span className="text-[20px]">{habitat.emoji}</span><span className="text-[9px] font-bold leading-none" style={{ color: taken ? 'var(--tg-theme-hint-color)' : habitat.color }}>{taken ? '✓' : habitat.name.split(' ')[0]}</span></button>; })}</div>
          <button onClick={() => void handleBuy()} disabled={!selHabitat || buying || (info.next_price > 0 && gs.rub < info.next_price)} className="w-full py-[11px] rounded-xl border-none font-extrabold text-[13px] cursor-pointer disabled:opacity-50" style={{ background: 'linear-gradient(135deg, var(--c-blue), #0066dd)', color: 'var(--tg-theme-button-text-color)' }}>{buying ? '...' : selHabitat ? `Открыть ${HABITAT_INFO[selHabitat].name}` : 'Выбери среду обитания'}</button>
        </div> : <p className="m-0 text-center text-[12px] py-2 text-tg-hint">✓ Все 5 местностей открыты</p>}
      </> : null}

      {assigningTo && <AnimalPicker localityHabitat={assigningTo.habitat} onPick={animal => void handleAssign(animal, assigningTo.localityId)} onClose={() => setAssigning(null)} />}
    </div>
  );
}
