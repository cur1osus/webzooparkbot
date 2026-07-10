import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import type { Animal, BreedResult, GameState, GeneTier, Habitat } from '@/types';
import { apiBreed, apiGetAnimals } from '@/api';
import { fmt } from '@/utils/format';

const HABITAT_INFO: Record<Habitat, { emoji: string; name: string; color: string }> = {
  desert:     { emoji: '🐪', name: 'Пустыня',   color: 'var(--c-gold)' },
  mountains:  { emoji: '🦅', name: 'Горы',       color: 'var(--tg-theme-hint-color)' },
  forest:     { emoji: '🐆', name: 'Густой лес', color: 'var(--c-green)' },
  fields:     { emoji: '🐴', name: 'Поля',        color: 'var(--c-teal)' },
  antarctica: { emoji: '🐧', name: 'Антарктида', color: 'var(--c-cyan)' },
};

const GENE_LABEL: Record<string, Record<GeneTier, string>> = {
  survival:     { low: 'Слабый',       medium: 'Обычный', high: 'Долгожитель'    },
  reproduction: { low: 'Неохотно',     medium: 'Обычно',  high: 'Активное'       },
  appearance:   { low: 'Уродец',       medium: 'Обычный', high: 'Привлекательный'},
  size_trait:   { low: 'Маленький',    medium: 'Обычный', high: 'Гигант'         },
};

const GENE_COLOR: Record<GeneTier, string> = {
  low: 'var(--c-orange)', medium: 'var(--tg-theme-hint-color)', high: 'var(--c-green)',
};

// success rate table matching GDD §6
const BREED_RATE: Record<string, number> = {
  'low+low': 0.30, 'low+medium': 0.45, 'medium+low': 0.45,
  'medium+medium': 0.60, 'medium+high': 0.75, 'high+medium': 0.75,
  'high+high': 0.90,
};

function breedRate(a: Animal | null, b: Animal | null): number | null {
  if (!a || !b) return null;
  const key = `${a.reproduction}+${b.reproduction}`;
  return BREED_RATE[key] ?? null;
}

// ─── Animal mini-card for result display ─────────────────────────────────────

function AnimalResultCard({ animal }: { animal: Animal }) {
  const hab = HABITAT_INFO[animal.habitat];
  const genes: [string, GeneTier][] = [
    ['survival', animal.survival], ['reproduction', animal.reproduction],
    ['appearance', animal.appearance], ['size_trait', animal.size_trait],
  ];
  return (
    <div className="rounded-2xl p-4 flex flex-col gap-3"
         style={{ background: `linear-gradient(135deg, ${hab.color}12, rgba(26,29,43,0.9))`, border: `1px solid ${hab.color}35` }}>
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-2xl grid place-items-center text-[26px] shrink-0"
             style={{ background: `${hab.color}20`, border: `1px solid ${hab.color}40` }}>
          {hab.emoji}
        </div>
        <div>
          <p className="m-0 font-extrabold text-[15px]">{hab.name}</p>
          <p className="m-0 text-[11px]" style={{ color: 'var(--c-green)' }}>₽{fmt(animal.income)}/мин</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-[6px]">
        {genes.map(([key, val]) => (
          <div key={key} className="flex items-center gap-2 px-3 py-[7px] rounded-xl"
               style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 7%, transparent)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)' }}>
            <div className="w-2 h-2 rounded-full shrink-0" style={{ background: GENE_COLOR[val] }} />
            <span className="text-[10px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
              {key === 'survival' ? 'Выж' : key === 'reproduction' ? 'Разм' : key === 'appearance' ? 'Вид' : 'Размер'}
            </span>
            <span className="ml-auto text-[11px] font-bold" style={{ color: GENE_COLOR[val] }}>
              {GENE_LABEL[key][val]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Parent selector card ─────────────────────────────────────────────────────

function ParentSlot({ label, animal, onClick }: {
  label: string;
  animal: Animal | null;
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

  const hab = HABITAT_INFO[animal.habitat];
  return (
    <button onClick={onClick}
            className="flex-1 rounded-2xl border-none cursor-pointer flex flex-col gap-2 p-3 text-left"
            style={{ background: `${hab.color}12`, border: `1px solid ${hab.color}35` }}>
      <div className="flex items-center gap-2">
        <span className="text-[22px]">{hab.emoji}</span>
        <div className="flex-1 min-w-0">
          <p className="m-0 text-[12px] font-bold truncate">{hab.name}</p>
          <p className="m-0 text-[10px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            {GENE_LABEL.reproduction[animal.reproduction]}
          </p>
        </div>
      </div>
      <span className="text-[10px] px-2 py-[3px] rounded-full self-start"
            style={{ background: 'rgba(143,149,171,0.15)', color: 'var(--tg-theme-hint-color)' }}>
        сменить
      </span>
    </button>
  );
}

// ─── Animal picker overlay ────────────────────────────────────────────────────

function AnimalPicker({ animals, exclude, onPick, onClose }: {
  animals: Animal[];
  exclude: number | null;
  onPick: (a: Animal) => void;
  onClose: () => void;
}) {
  const available = animals.filter(a => a.can_breed && a.id !== exclude);

  return createPortal(
    <div className="modal-backdrop fixed inset-0 z-[300] flex items-end justify-center" onClick={onClose}>
      <div className="sheet-panel w-full max-w-[480px] rounded-t-3xl p-4 flex flex-col gap-3 max-h-[75vh] overflow-y-auto"
           onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-1">
          <p className="m-0 font-extrabold text-[15px]">Выбери родителя</p>
          <button onClick={onClose} aria-label="Закрыть" className="tap-target -mr-2 border-none bg-transparent text-[18px] cursor-pointer"
                  style={{ color: 'var(--tg-theme-hint-color)' }}>✕</button>
        </div>

        {available.length === 0 ? (
          <p className="text-center py-6 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Нет доступных животных<br />
            <span className="text-[11px]">Все уже скрещивались сегодня</span>
          </p>
        ) : available.map(a => {
          const hab = HABITAT_INFO[a.habitat];
          return (
            <button key={a.id} onClick={() => onPick(a)}
                    className="flex items-center gap-3 px-3 py-[10px] rounded-xl border-none cursor-pointer text-left w-full"
                    style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)', border: '1px solid transparent' }}>
              <span className="text-[24px]">{hab.emoji}</span>
              <div className="flex-1 min-w-0">
                <p className="m-0 text-[13px] font-bold">{hab.name}</p>
                <p className="m-0 text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                  Разм: <span style={{ color: GENE_COLOR[a.reproduction] }}>{GENE_LABEL.reproduction[a.reproduction]}</span>
                  {' · '}₽{fmt(a.income)}/мин
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>,
    document.body,
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function LabPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  void gs;
  const [animals, setAnimals]   = useState<Animal[]>([]);
  const [loading, setLoading]   = useState(true);
  const [parent1, setParent1]   = useState<Animal | null>(null);
  const [parent2, setParent2]   = useState<Animal | null>(null);
  const [picking, setPicking]   = useState<1 | 2 | null>(null);
  const [breeding, setBreeding] = useState(false);
  const [result, setResult]     = useState<BreedResult | null>(null);
  const [error, setError]       = useState<string | null>(null);

  const load = async () => {
    try {
      const { animals } = await apiGetAnimals();
      setAnimals(animals);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const handleBreed = async () => {
    if (!parent1 || !parent2 || breeding) return;
    setBreeding(true);
    setError(null);
    setResult(null);
    try {
      const res = await apiBreed(parent1.id, parent2.id);
      setResult(res);
      // Both parents are now `can_breed: false`.
      const { animals: fresh } = await apiGetAnimals();
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

  const rate = breedRate(parent1, parent2);
  const canBreed = parent1?.can_breed && parent2?.can_breed && !breeding;

  return (
    <div className="page-content-safe flex flex-col gap-4">

      {/* Header */}
      <div className="px-[14px] pt-4">
        <p className="font-display m-0 mb-[2px] text-[15px]">🧪 Лаборатория</p>
        <p className="m-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
          Скрещивай животных — каждое животное 1 раз в день
        </p>
      </div>

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

          {!parent1 || !parent2
            ? null
            : (!parent1.can_breed || !parent2.can_breed) && (
              <p className="m-0 text-center text-[12px]" style={{ color: 'var(--c-amber)' }}>
                ⚠️ Одно из животных уже скрещивалось сегодня
              </p>
            )
          }

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
                <AnimalResultCard animal={result.animal} />
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

          {/* Breed rate table */}
          <div className="card">
            <p className="m-0 mb-2 font-bold text-[13px]">Таблица шансов</p>
            <div className="flex flex-col gap-[4px] text-[12px]">
              {[
                ['Неохотно + Неохотно', '30%'],
                ['Неохотно + Обычно',   '45%'],
                ['Обычно + Обычно',     '60%'],
                ['Обычно + Активное',   '75%'],
                ['Активное + Активное', '90%'],
              ].map(([combo, chance]) => (
                <div key={combo} className="flex justify-between py-[3px]">
                  <span style={{ color: 'var(--tg-theme-hint-color)' }}>{combo}</span>
                  <span className="font-bold">{chance}</span>
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
          exclude={picking === 1 ? parent2?.id ?? null : parent1?.id ?? null}
          onPick={a => {
            if (picking === 1) setParent1(a);
            else setParent2(a);
            setPicking(null);
          }}
          onClose={() => setPicking(null)}
        />
      )}
    </div>
  );
}
