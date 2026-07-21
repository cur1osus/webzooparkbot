import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import type { Animal, GameState, Habitat, Locality, LocalitiesInfo } from '@/types';
import { apiGetLocalities, apiBuyLocality, apiAssignLocality, apiAssignMatchingLocality } from '@/api';
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

// ─── Animal chip inside a locality card ───────────────────────────────────────

function AnimalChip({ animal, onRemove }: { animal: Animal; onRemove: () => void }) {
  const hab = HABITAT_INFO[animal.habitat];
  return (
    <div
      className="flex items-center gap-2 px-3 py-[7px] rounded-xl"
      style={{ background: `${hab.color}12`, border: `1px solid ${hab.color}25` }}
    >
      <AnimalArt animal={animal} size={32} className="shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="m-0 text-[12px] font-bold truncate">
          {animal.name} <span className="font-normal" style={{ color: 'var(--tg-theme-hint-color)' }}>· {animal.species_name}</span>
        </p>
        {/* income already includes the ×1.5 habitat bonus when it applies */}
        <div className="flex items-center gap-[6px]">
          <span className="text-[11px] font-bold" style={{ color: 'var(--c-green)' }}>
            ₽{fmt(animal.income)}/мин
          </span>
          {animal.habitat_bonus && (
            <span className="text-[10px] font-bold" style={{ color: 'var(--c-gold)' }}>
              (бонус среды)
            </span>
          )}
        </div>
      </div>
      <button
        onClick={onRemove}
        className="w-6 h-6 rounded-full border-none grid place-items-center cursor-pointer text-[13px]"
        style={{ background: 'rgba(var(--c-red-rgb),0.12)', color: 'var(--c-red)' }}
      >
        ×
      </button>
    </div>
  );
}

/** How many animals the "Распределить сразу" button would pull into this locality.
 *
 * Not just the homeless ones. An animal standing in another habitat earns two thirds of
 * what it would here, and the endpoint moves those too — so the count has to match, or the
 * button reports less than it does. */
function matchingCountFor(info: LocalitiesInfo, locality: Locality): number {
  const elsewhere = info.localities
    .filter(other => other.id !== locality.id)
    .flatMap(other => other.animals);
  return [...info.unassigned, ...elsewhere].filter(a => a.habitat === locality.habitat).length;
}

// ─── Locality card ─────────────────────────────────────────────────────────────

function LocalityCard({ locality, unassigned, matchingCount, onAdd, onAssignMatching, assigningMatching, onRemove }: {
  locality: Locality;
  unassigned: Animal[];
  onAdd: () => void;
  onAssignMatching: () => void;
  assigningMatching: boolean;
  matchingCount: number;
  onRemove: (id: number) => void;
}) {
  const hab = HABITAT_INFO[locality.habitat];
  const totalIncome = locality.animals.reduce((s, a) => s + a.income, 0);

  const canAdd = unassigned.length > 0;
  const hasAnimals = locality.animals.length > 0;
  const [collapsed, setCollapsed] = useState(hasAnimals);
  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{
        background: 'rgba(26,29,43,0.9)',
        border: `1px solid color-mix(in srgb, ${hab.color} 30%, transparent)`,
      }}
    >
      {/* Header — a full-width horizontal banner tinted with the habitat's own colour. Tapping
          it collapses/expands the animal list, so long localities can be folded away. The
          "+ добавить" action lives in its own nested button. Colours are CSS variables, so alpha
          comes from color-mix (a `${var}55` hex suffix would be invalid). */}
      <div
        onClick={hasAnimals ? () => setCollapsed(c => !c) : undefined}
        className="w-full flex items-center gap-3 px-4 py-[16px] text-left"
        style={{
          background: `linear-gradient(90deg, color-mix(in srgb, ${hab.color} 48%, transparent) 0%, color-mix(in srgb, ${hab.color} 20%, transparent) 55%, transparent 100%)`,
          cursor: hasAnimals ? 'pointer' : 'default',
        }}
      >
        {hasAnimals && (
          <span
            className="text-[12px] shrink-0 transition-transform"
            style={{ color: hab.color, transform: collapsed ? 'rotate(-90deg)' : 'none' }}
          >
            ▾
          </span>
        )}
        <div
          className="w-11 h-11 rounded-xl grid place-items-center text-[24px] shrink-0"
          style={{ background: `color-mix(in srgb, ${hab.color} 24%, transparent)`, border: `1px solid color-mix(in srgb, ${hab.color} 42%, transparent)` }}
        >
          {hab.emoji}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-[7px]">
            <p className="m-0 font-extrabold text-[15px]">{hab.name}</p>
            <span className="text-[13px] font-black" style={{ color: hab.color }}>{locality.animals.length}</span>
          </div>
          {totalIncome > 0 ? (
            <p className="m-0 text-[11px]" style={{ color: 'var(--c-green)' }}>
              ₽{fmt(totalIncome)}/мин суммарно
            </p>
          ) : (
            <p className="m-0 text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>Пусто</p>
          )}
        </div>
        {canAdd && (
          <button
            onClick={e => { e.stopPropagation(); onAdd(); }}
            className="text-[13px] font-bold shrink-0 flex items-center gap-1 border-none bg-transparent cursor-pointer px-1"
            style={{ color: hab.color }}
          >
            + добавить
          </button>
        )}
      </div>

      {/* Animals */}
      {hasAnimals && !collapsed && (
        <div className="flex flex-col gap-[6px] px-4 py-3">
          {locality.animals.map(a => (
            <AnimalChip key={a.id} animal={a} onRemove={() => onRemove(a.id)} />
          ))}
        </div>
      )}

      {matchingCount > 0 && (
        <div className="px-4 pt-3 pb-3">
          <button
            onClick={onAssignMatching}
            disabled={assigningMatching}
            className="w-full min-h-11 rounded-xl border-none cursor-pointer font-extrabold text-[12px] disabled:opacity-55 disabled:cursor-wait"
            style={{ background: `color-mix(in srgb, ${hab.color} 16%, transparent)`, color: hab.color, border: `1px solid color-mix(in srgb, ${hab.color} 30%, transparent)` }}
          >
            {assigningMatching ? 'Распределяем...' : `Распределить сразу · ${matchingCount}`}
          </button>
        </div>
      )}

      {locality.animals.length === 0 && !canAdd && (
        <p className="m-0 px-4 py-3 text-center text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
          Нет свободных животных
        </p>
      )}
    </div>
  );
}

// ─── Animal picker bottom sheet ────────────────────────────────────────────────

function AnimalPicker({ animals, localityHabitat, onPick, onClose }: {
  animals: Animal[];
  localityHabitat: Habitat;
  onPick: (id: number) => void;
  onClose: () => void;
}) {
  const sorted = [...animals].sort(
    (a, b) => (b.habitat === localityHabitat ? 1 : 0) - (a.habitat === localityHabitat ? 1 : 0)
  );

  return createPortal(
    <div
      className="modal-backdrop fixed inset-0 z-[300] flex items-end justify-center"
      onClick={onClose}
    >
      <div
        className="sheet-panel w-full max-w-[480px] rounded-t-3xl p-4 flex flex-col gap-3 max-h-[70vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <p className="m-0 font-extrabold text-[15px]">Выбери животное</p>
          <button
            onClick={onClose}
            aria-label="Закрыть"
            className="tap-target -mr-2 border-none bg-transparent text-[18px] cursor-pointer"
            style={{ color: 'var(--tg-theme-hint-color)' }}
          >
            ✕
          </button>
        </div>

        {sorted.length === 0 ? (
          <p className="text-center py-4 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Нет свободных животных
          </p>
        ) : sorted.map(a => {
          const hab = HABITAT_INFO[a.habitat];
          const isMatch = a.habitat === localityHabitat;
          return (
            <button
              key={a.id}
              onClick={() => onPick(a.id)}
              className="flex items-center gap-3 px-3 py-[10px] rounded-xl border-none cursor-pointer text-left w-full"
              style={{
                background: isMatch
                  ? `${hab.color}18`
                  : 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)',
                border: `1px solid ${isMatch ? hab.color + '35' : 'transparent'}`,
              }}
            >
              <AnimalArt animal={a} size={36} className="shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="text-[13px] font-bold truncate block">
                  {a.name} <span className="font-normal" style={{ color: 'var(--tg-theme-hint-color)' }}>· {a.species_name}</span>
                </span>
                <span className="text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                  {/* Base income, and where the habitat matches, the ×1.5 result too */}
                  ₽{fmt(a.income)}/мин
                  {isMatch && (
                    <span style={{ color: 'var(--c-gold)' }}> → ₽{fmt(Math.round(a.income * 1.5))} с бонусом среды</span>
                  )}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>,
    document.body,
  );
}

// ─── Main page ─────────────────────────────────────────────────────────────────

export function LocalitiesPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [info, setInfo]           = useState<LocalitiesInfo | null>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [buying, setBuying]       = useState(false);
  const [selHabitat, setSelHab]   = useState<Habitat | null>(null);
  const [assigningTo, setAssigning] = useState<{ localityId: number; habitat: Habitat } | null>(null);
  const [assigningMatchingId, setAssigningMatchingId] = useState<number | null>(null);

  const load = async () => {
    try {
      setInfo(await apiGetLocalities());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const handleBuy = async () => {
    if (!selHabitat || buying) return;
    setBuying(true);
    setError(null);
    try {
      await apiBuyLocality(selHabitat);
      setSelHab(null);
      await load();
      onRefresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBuying(false);
    }
  };

  const handleAssign = async (animalId: number, localityId: number) => {
    setAssigning(null);
    try {
      await apiAssignLocality(animalId, localityId);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const handleUnassign = async (animalId: number) => {
    try {
      await apiAssignLocality(animalId, null);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const handleAssignMatching = async (localityId: number) => {
    if (assigningMatchingId !== null) return;
    setAssigningMatchingId(localityId);
    setError(null);
    try {
      await apiAssignMatchingLocality(localityId);
      await load();
      onRefresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAssigningMatchingId(null);
    }
  };

  return (
    <div className="px-[14px] pt-4 pb-4 flex flex-col gap-4">

      {/* Header */}
      <div>
        <p className="m-0 mb-[2px] font-extrabold text-[16px]">🌍 Местности</p>
        <p className="m-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
          Совпадение среды животного и местности даёт ×1.5 к доходу
        </p>
      </div>

      {/* Balance */}
      <span
        className="self-start px-3 py-[5px] rounded-[20px] text-[13px] font-bold"
        style={{ background: 'rgba(var(--c-green-rgb),0.12)', color: 'var(--c-green)', border: '1px solid rgba(var(--c-green-rgb),0.25)' }}
      >
        ₽ {fmt(gs.rub)}
      </span>

      {error && (
        <div
          className="rounded-xl px-4 py-3 text-sm"
          style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.25)', color: 'var(--c-red)' }}
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-8"><div className="spinner" /></div>
      ) : info ? (
        <>
          {/* Locality cards */}
          {info.localities.map(loc => (
            <LocalityCard
              key={loc.id}
              locality={loc}
              unassigned={info.unassigned}
              matchingCount={matchingCountFor(info, loc)}
              onAdd={() => setAssigning({ localityId: loc.id, habitat: loc.habitat })}
              onAssignMatching={() => void handleAssignMatching(loc.id)}
              assigningMatching={assigningMatchingId === loc.id}
              onRemove={id => void handleUnassign(id)}
            />
          ))}

          {/* Unassigned pool */}
          {info.unassigned.length > 0 && (
            <div>
              <p className="m-0 mb-2 font-bold text-[13px]">
                Без местности
                <span className="ml-2 font-normal text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                  {info.unassigned.length} шт. — без бонуса ×1.5
                </span>
              </p>
              <div
                className="rounded-2xl p-3 flex flex-col gap-[6px]"
                style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 6%, transparent)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)' }}
              >
                {info.unassigned.map(a => {
                  const hab = HABITAT_INFO[a.habitat];
                  return (
                    <div key={a.id} className="flex items-center gap-2 text-[12px]">
                      <AnimalArt animal={a} size={24} className="shrink-0" />
                      <span className="font-semibold truncate">{a.name}</span>
                      <span className="text-[10px] truncate" style={{ color: 'var(--tg-theme-hint-color)' }}>{a.species_name} {hab.emoji}</span>
                      <span className="ml-auto font-bold shrink-0" style={{ color: 'var(--tg-theme-hint-color)' }}>
                        ₽{fmt(a.income)}/мин
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Buy new locality */}
          {info.next_price !== null ? (
            <div
              className="rounded-2xl p-4 flex flex-col gap-3"
              style={{ background: 'rgba(var(--c-blue-rgb),0.08)', border: '1px solid rgba(var(--c-blue-rgb),0.2)' }}
            >
              <div className="flex items-center gap-2">
                <p className="m-0 font-extrabold text-[14px] flex-1">🔓 Открыть местность</p>
                <span className="text-[13px] font-bold" style={{ color: info.next_price === 0 ? 'var(--c-green)' : 'var(--tg-theme-hint-color)' }}>
                  {info.next_price === 0 ? 'Бесплатно' : `₽${fmt(info.next_price)}`}
                </span>
              </div>

              {/* Habitat picker */}
              <div className="grid grid-cols-5 gap-[6px]">
                {ALL_HABITATS.map(h => {
                  const taken = info.habitats_taken.includes(h);
                  const sel   = selHabitat === h;
                  const hab   = HABITAT_INFO[h];
                  return (
                    <button
                      key={h}
                      onClick={() => !taken && setSelHab(sel ? null : h)}
                      disabled={taken}
                      className="flex flex-col items-center gap-1 py-[10px] rounded-xl border-none cursor-pointer disabled:cursor-default"
                      style={{
                        background: taken ? 'rgba(143,149,171,0.08)' : sel ? `${hab.color}25` : `${hab.color}10`,
                        border: `1px solid ${taken ? 'rgba(143,149,171,0.15)' : sel ? hab.color + '60' : hab.color + '25'}`,
                        opacity: taken ? 0.45 : 1,
                      }}
                    >
                      <span className="text-[20px]">{hab.emoji}</span>
                      <span className="text-[9px] font-bold leading-none" style={{ color: taken ? 'var(--tg-theme-hint-color)' : hab.color }}>
                        {taken ? '✓' : hab.name.split(' ')[0]}
                      </span>
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => void handleBuy()}
                disabled={!selHabitat || buying || (info.next_price > 0 && gs.rub < info.next_price)}
                className="w-full py-[11px] rounded-xl border-none font-extrabold text-[13px] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: 'linear-gradient(135deg, var(--c-blue), #0066dd)', color: 'var(--tg-theme-button-text-color)' }}
              >
                {buying ? '...' : selHabitat ? `Открыть ${HABITAT_INFO[selHabitat].name}` : 'Выбери среду обитания'}
              </button>
            </div>
          ) : (
            <p className="m-0 text-center text-[12px] py-2" style={{ color: 'var(--tg-theme-hint-color)' }}>
              ✓ Все 5 местностей открыты
            </p>
          )}
        </>
      ) : null}

      {/* Animal picker overlay */}
      {assigningTo && info && (
        <AnimalPicker
          animals={info.unassigned}
          localityHabitat={assigningTo.habitat}
          onPick={id => void handleAssign(id, assigningTo.localityId)}
          onClose={() => setAssigning(null)}
        />
      )}
    </div>
  );
}
