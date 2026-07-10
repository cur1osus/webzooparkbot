import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import type { Animal, GameState, Habitat, Locality, LocalitiesInfo } from '@/types';
import { apiGetLocalities, apiBuyLocality, apiAssignLocality } from '@/api';
import { fmt } from '@/utils/format';

const HABITAT_INFO: Record<Habitat, { emoji: string; name: string; color: string }> = {
  desert:     { emoji: '🐪', name: 'Пустыня',   color: 'var(--c-gold)' },
  mountains:  { emoji: '🦅', name: 'Горы',       color: 'var(--tg-theme-hint-color)' },
  forest:     { emoji: '🐆', name: 'Густой лес', color: 'var(--c-green)' },
  fields:     { emoji: '🐴', name: 'Поля',        color: 'var(--c-teal)' },
  antarctica: { emoji: '🐧', name: 'Антарктида', color: 'var(--c-cyan)' },
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
      <span className="text-[18px]">{hab.emoji}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-[6px]">
          <span className="text-[12px] font-bold" style={{ color: 'var(--c-green)' }}>
            ₽{fmt(animal.income)}/мин
          </span>
          {animal.habitat_bonus && (
            <span className="text-[10px] font-bold px-[5px] py-[1px] rounded-full"
                  style={{ background: 'var(--c-gold)20', color: 'var(--c-gold)', border: '1px solid var(--c-gold)30' }}>
              ×1.5
            </span>
          )}
        </div>
        <span className="text-[10px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
          {animal.survival === 'high' ? 'Долгожитель' : animal.survival === 'medium' ? 'Обычный' : 'Слабый'}
        </span>
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

// ─── Locality card ─────────────────────────────────────────────────────────────

function LocalityCard({ locality, unassignedCount, onAdd, onRemove }: {
  locality: Locality;
  unassignedCount: number;
  onAdd: () => void;
  onRemove: (id: number) => void;
}) {
  const hab = HABITAT_INFO[locality.habitat];
  const totalIncome = locality.animals.reduce((s, a) => s + a.income, 0);

  return (
    <div
      className="rounded-2xl p-4 flex flex-col gap-3"
      style={{
        background: `linear-gradient(135deg, ${hab.color}10, rgba(26,29,43,0.9))`,
        border: `1px solid ${hab.color}30`,
      }}
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-xl grid place-items-center text-[22px] shrink-0"
          style={{ background: `${hab.color}20`, border: `1px solid ${hab.color}35` }}
        >
          {hab.emoji}
        </div>
        <div className="flex-1 min-w-0">
          <p className="m-0 font-extrabold text-[14px]">{hab.name}</p>
          {totalIncome > 0 && (
            <p className="m-0 text-[11px]" style={{ color: 'var(--c-green)' }}>
              ₽{fmt(totalIncome)}/мин суммарно
            </p>
          )}
        </div>
        <span
          className="text-[11px] px-2 py-[3px] rounded-full shrink-0"
          style={{ background: `${hab.color}15`, color: hab.color, border: `1px solid ${hab.color}30` }}
        >
          {locality.animals.length}
        </span>
      </div>

      {/* Animals */}
      {locality.animals.length > 0 && (
        <div className="flex flex-col gap-[6px]">
          {locality.animals.map(a => (
            <AnimalChip key={a.id} animal={a} onRemove={() => onRemove(a.id)} />
          ))}
        </div>
      )}

      {/* Add button */}
      {unassignedCount > 0 ? (
        <button
          onClick={onAdd}
          className="w-full py-[8px] rounded-xl border-none text-[12px] font-bold cursor-pointer"
          style={{ background: `${hab.color}12`, color: hab.color, border: `1px dashed ${hab.color}40` }}
        >
          + Добавить животное
        </button>
      ) : locality.animals.length === 0 ? (
        <p className="m-0 text-center text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
          Нет свободных животных
        </p>
      ) : null}
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
              <span className="text-[24px]">{hab.emoji}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-bold">{hab.name}</span>
                  {isMatch && (
                    <span
                      className="text-[10px] font-bold px-[6px] py-[2px] rounded-full"
                      style={{ background: 'var(--c-gold)25', color: 'var(--c-gold)', border: '1px solid var(--c-gold)30' }}
                    >
                      ×1.5 бонус
                    </span>
                  )}
                </div>
                <span className="text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                  {a.survival === 'high' ? 'Долгожитель' : a.survival === 'medium' ? 'Обычный' : 'Слабый'}
                  {' · '}₽{fmt(a.income)}/мин
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
              unassignedCount={info.unassigned.length}
              onAdd={() => setAssigning({ localityId: loc.id, habitat: loc.habitat })}
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
                      <span>{hab.emoji}</span>
                      <span style={{ color: 'var(--tg-theme-hint-color)' }}>{hab.name}</span>
                      <span className="ml-auto font-bold" style={{ color: 'var(--tg-theme-hint-color)' }}>
                        ₽{fmt(a.income)}/мин (без бонуса)
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
