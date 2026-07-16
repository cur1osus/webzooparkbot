import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  apiDismissExpedition,
  apiFinishExpedition,
  apiGetExpeditions,
  apiStartExpedition,
} from '@/api';
import {
  formatDurationMinutes,
  expeditionGeneUpgradeChance,
  expeditionGradeFor,
  expeditionPower,
  geneColor,
  geneLabel,
  squadPower,
  EXPEDITION_GRADE_META,
  HABITAT_INFO,
  lifeLeft,
} from '@/data/packs';
import type {
  ActiveExpedition,
  ExpeditionDepthOption,
  ExpeditionInfo,
  ExpeditionLocality,
  ExpeditionResult,
  Habitat,
  Animal,
} from '@/types';
import { formatCountdown, fmt } from '@/utils/format';
import { AnimalArt } from '@/components/AnimalArt';

const GENE_ROWS = [
  ['survival', 'Выж'],
  ['reproduction', 'Разм'],
  ['appearance', 'Вид'],
  ['size_trait', 'Размер'],
] as const;

function GeneGrid({ animal }: { animal: Pick<Animal, 'survival' | 'reproduction' | 'appearance' | 'size_trait'> }) {
  return (
    <div className="grid grid-cols-2 gap-[6px]">
      {GENE_ROWS.map(([key, short]) => (
        <div
          key={key}
          className="flex items-center gap-2 px-3 py-[7px] rounded-xl"
          style={{
            background: 'color-mix(in srgb, var(--tg-theme-hint-color) 7%, transparent)',
            border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)',
          }}
        >
          <div className="w-2 h-2 rounded-full shrink-0" style={{ background: geneColor(key, animal[key]) }} />
          <span className="text-[10px]" style={{ color: 'var(--tg-theme-hint-color)' }}>{short}</span>
          <span className="ml-auto text-[11px] font-bold" style={{ color: geneColor(key, animal[key]) }}>
            {geneLabel(key, animal[key])}
          </span>
        </div>
      ))}
    </div>
  );
}

function WildAnimalSummary({ habitat, result }: { habitat: Habitat; result: ExpeditionResult }) {
  // The wild animal always comes from the expedition's own habitat.
  const wildHabitat = HABITAT_INFO[result.habitat ?? habitat];

  return (
    <div className="rounded-2xl p-4 flex flex-col gap-3"
         style={{ background: `${wildHabitat.color}10`, border: `1px solid ${wildHabitat.color}30` }}>
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-2xl grid place-items-center text-[26px] shrink-0"
             style={{ background: `${wildHabitat.color}20`, border: `1px solid ${wildHabitat.color}35` }}>
          <AnimalArt animal={result.wild} size={44} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="m-0 font-extrabold text-[15px]">{result.wild.species_name}</p>
          <p className="m-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            {wildHabitat.name} · {result.depth_name} · сила {result.wild_power}
          </p>
        </div>
      </div>
      <GeneGrid animal={result.wild} />
    </div>
  );
}

function ExpeditionAnimalCard({
  animal,
  selected,
  disabled,
  onToggle,
}: {
  animal: Animal;
  selected?: boolean;
  disabled?: boolean;
  onToggle?: () => void;
}) {
  const habitat = HABITAT_INFO[animal.habitat];
  const power = expeditionPower(animal);
  const ttl = lifeLeft(animal.dies_at);

  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled || !onToggle}
      className="w-full rounded-2xl p-4 flex flex-col gap-3 text-left border-none"
      style={{
        background: selected ? `${habitat.color}16` : `linear-gradient(135deg, ${habitat.color}10, rgba(26,29,43,0.9))`,
        border: `1px solid ${selected ? `${habitat.color}55` : `${habitat.color}30`}`,
        boxShadow: selected ? `0 0 0 1px ${habitat.color}20` : 'none',
        opacity: disabled && !selected ? 0.55 : 1,
        cursor: onToggle ? 'pointer' : 'default',
      }}
    >
      <div className="flex items-center gap-3">
        <div className="w-11 h-11 rounded-2xl grid place-items-center shrink-0 overflow-hidden"
             style={{ background: `color-mix(in srgb, ${habitat.color} 20%, transparent)`, border: `1px solid color-mix(in srgb, ${habitat.color} 35%, transparent)` }}>
          <AnimalArt animal={animal} size={40} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="m-0 font-extrabold text-[14px]">{animal.name}</p>
            <span className="text-[11px] font-bold px-2 py-[2px] rounded-full"
                  style={{ background: 'rgba(var(--c-blue-rgb),0.14)', color: 'var(--c-cyan)', border: '1px solid rgba(var(--c-cyan-rgb),0.28)' }}>
              Сила {power}
            </span>
            {selected && (
              <span className="text-[11px] font-bold px-2 py-[2px] rounded-full"
                    style={{ background: 'rgba(var(--c-green-rgb),0.14)', color: 'var(--c-green)', border: '1px solid rgba(var(--c-green-rgb),0.25)' }}>
                В отряде
              </span>
            )}
          </div>
          <p className="m-0 text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            {animal.species_name} · ₽{fmt(animal.income)}/мин
            {ttl ? ` · живёт ${ttl.label}` : ''}
          </p>
        </div>
      </div>
      <GeneGrid animal={animal} />
    </button>
  );
}

/**
 * The result of one fight. The old card only had "Победа" or "Провал" to show, because the
 * outcome was a bare `squad_power >= wild_power`. It is now a graded ratio, so this reports
 * how decisively it went — and what the squad's surplus power actually bought.
 */
function ResultCard({ expedition, result }: { expedition: ActiveExpedition; result: ExpeditionResult }) {
  const grade = EXPEDITION_GRADE_META[result.grade] ?? EXPEDITION_GRADE_META.victory;
  const caught = result.captured_animals ?? (result.captured_animal ? [result.captured_animal] : []);
  const upgrades = result.gene_upgrades ?? [];
  const loot = result.loot;
  const wounded = result.sick_animal_ids?.length ?? 0;

  return (
    <>
      <div className="rounded-2xl p-4 flex flex-col gap-3"
           style={{
             background: `color-mix(in srgb, ${grade.color} 10%, transparent)`,
             border: `1px solid color-mix(in srgb, ${grade.color} 30%, transparent)`,
           }}>
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="m-0 font-extrabold text-[15px]" style={{ color: grade.color }}>{result.grade_label}</p>
            <p className="m-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
              Отряд {result.squad_power} против зверя {result.wild_power} · перевес ×{result.ratio}
            </p>
          </div>
          <span className="text-[28px] shrink-0">{grade.emoji}</span>
        </div>

        {(loot?.rub || loot?.usd) && (
          <div className="flex gap-2">
            {loot.rub > 0 && (
              <span className="text-[12px] font-bold px-3 py-[6px] rounded-xl"
                    style={{ background: 'rgba(var(--c-gold-rgb),0.12)', color: 'var(--c-gold)', border: '1px solid rgba(var(--c-gold-rgb),0.25)' }}>
                Трофей ₽{fmt(loot.rub)}
              </span>
            )}
            {loot.usd > 0 && (
              <span className="text-[12px] font-bold px-3 py-[6px] rounded-xl"
                    style={{ background: 'rgba(var(--c-green-rgb),0.12)', color: 'var(--c-green)', border: '1px solid rgba(var(--c-green-rgb),0.25)' }}>
                ${fmt(loot.usd)}
              </span>
            )}
          </div>
        )}

        {upgrades.length > 0 && (
          <div className="rounded-xl px-3 py-[10px]"
               style={{ background: 'rgba(var(--c-teal-rgb),0.08)', border: '1px solid rgba(var(--c-teal-rgb),0.22)' }}>
            <p className="m-0 text-[11px] font-bold" style={{ color: 'var(--c-teal)' }}>
              ПЕРЕВЕС УЛУЧШИЛ ДОБЫЧУ
            </p>
            <p className="m-0 mt-1 text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
              Зверя взяли в лучшем состоянии: {upgrades
                .map(u => `${geneLabel(u.gene, u.from)} → ${geneLabel(u.gene, u.to)}`)
                .join(', ')}
            </p>
          </div>
        )}

        {caught.length > 0 && (
          <div>
            <p className="m-0 mb-2 text-[12px] font-bold" style={{ color: grade.color }}>
              {caught.length > 1 ? `ДОБЫЧА · ${caught.length} ЗВЕРЯ` : 'ДОБЫЧА'}
            </p>
            <div className="flex flex-col gap-2">
              {caught.map(animal => <ExpeditionAnimalCard key={animal.id} animal={animal} />)}
            </div>
          </div>
        )}

        {!result.captured_animal_id && (
          <p className="m-0 text-[13px]" style={{ color: grade.color }}>
            {result.killed_animal_id
              ? 'Отряд разбит. Одно случайное животное погибло, остальные вернулись домой.'
              : 'Зверь оказался сильнее и ушёл. Отряд вернулся ни с чем.'}
          </p>
        )}

        {wounded > 0 && (
          <p className="m-0 text-[12px]" style={{ color: 'var(--c-amber)' }}>
            Ранено животных: {wounded}. Их доход упал вдвое — вылечи их у ветеринара.
          </p>
        )}
      </div>

      <WildAnimalSummary habitat={expedition.habitat} result={result} />
    </>
  );
}

function CurrentExpeditionCard({
  expedition,
  nowMs,
  busy,
  onFinish,
  onDismiss,
}: {
  expedition: ActiveExpedition;
  nowMs: number;
  busy: boolean;
  onFinish: () => void;
  onDismiss: () => void;
}) {
  const habitat = HABITAT_INFO[expedition.habitat];
  const partyPower = expedition.animals.reduce((total, animal) => total + expeditionPower(animal), 0);
  const leftSeconds = Math.max(0, Math.floor((new Date(expedition.ends_at).getTime() - nowMs) / 1000));
  const isReadyToFinish = expedition.status === 'active' && leftSeconds <= 0;
  const result = expedition.result;

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-2xl p-4 flex flex-col gap-3"
           style={{ background: `${habitat.color}10`, border: `1px solid ${habitat.color}30` }}>
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl grid place-items-center text-[26px] shrink-0"
               style={{ background: `${habitat.color}20`, border: `1px solid ${habitat.color}35` }}>
            {habitat.emoji}
          </div>
          <div className="flex-1 min-w-0">
            <p className="m-0 font-extrabold text-[15px] truncate">{habitat.name} · {expedition.depth_name}</p>
            <p className="m-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
              {expedition.animals.length} животных · сила по генам {partyPower}
            </p>
          </div>
          {/* Status pill anchored to the right edge, centred against the habitat icon —
              off the title line so it never crowds the name. */}
          <span className="text-[11px] font-bold px-2 py-[3px] rounded-full shrink-0 whitespace-nowrap"
                style={{
                  background: expedition.status === 'finished' ? 'rgba(var(--c-green-rgb),0.15)' : 'rgba(var(--c-blue-rgb),0.14)',
                  color: expedition.status === 'finished' ? 'var(--c-green)' : 'var(--c-cyan)',
                  border: expedition.status === 'finished'
                    ? '1px solid rgba(var(--c-green-rgb),0.25)'
                    : '1px solid rgba(var(--c-cyan-rgb),0.28)',
                }}>
            {expedition.status === 'finished' ? 'Завершена' : isReadyToFinish ? 'Можно завершить' : 'В пути'}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-[6px]">
          <div className="rounded-xl px-3 py-[10px]"
               style={{ background: 'rgba(var(--c-blue-rgb),0.08)', border: '1px solid rgba(var(--c-blue-rgb),0.2)' }}>
            <p className="m-0 text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>Длительность</p>
            <p className="m-0 mt-1 font-extrabold text-[14px]">{formatDurationMinutes((new Date(expedition.ends_at).getTime() - new Date(expedition.started_at).getTime()) / 60_000)}</p>
          </div>
          <div className="rounded-xl px-3 py-[10px]"
               style={{ background: expedition.status === 'finished' ? 'rgba(var(--c-green-rgb),0.08)' : 'rgba(var(--c-gold-rgb),0.08)', border: expedition.status === 'finished' ? '1px solid rgba(var(--c-green-rgb),0.2)' : '1px solid rgba(var(--c-gold-rgb),0.2)' }}>
            <p className="m-0 text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
              {expedition.status === 'finished' ? 'Статус' : 'До завершения'}
            </p>
            <p className="m-0 mt-1 font-extrabold text-[14px]" style={{ color: expedition.status === 'finished' ? 'var(--c-green)' : 'var(--c-gold)' }}>
              {expedition.status === 'finished' ? 'Результат открыт' : formatCountdown(leftSeconds)}
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <p className="m-0 text-[12px] font-bold" style={{ color: 'var(--tg-theme-hint-color)' }}>ОТРЯД</p>
          {expedition.animals.map(animal => {
            const lost = result?.killed_animal_id === animal.id;
            const hurt = result?.sick_animal_ids?.includes(animal.id) ?? false;
            return (
              <div key={animal.id} className="rounded-xl px-3 py-[10px] flex items-center gap-3"
                   style={{
                     background: lost ? 'rgba(var(--c-red-rgb),0.1)' : 'color-mix(in srgb, var(--tg-theme-hint-color) 6%, transparent)',
                     border: lost ? '1px solid rgba(var(--c-red-rgb),0.25)' : '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)',
                   }}>
                <AnimalArt animal={animal} size={30} className="shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="m-0 text-[13px] font-bold truncate">
                    {animal.name} <span className="font-normal" style={{ color: 'var(--tg-theme-hint-color)' }}>· {animal.species_name}</span>
                  </p>
                  <p className="m-0 text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                    Сила {expeditionPower(animal)} · ₽{fmt(animal.income)}/мин
                  </p>
                </div>
                {lost && <span className="text-[11px] font-bold text-[var(--c-red-soft)] shrink-0">Погиб</span>}
                {!lost && hurt && <span className="text-[11px] font-bold shrink-0" style={{ color: 'var(--c-amber)' }}>Ранен</span>}
              </div>
            );
          })}
        </div>

        {isReadyToFinish && (
          <button
            onClick={onFinish}
            disabled={busy}
            className="w-full py-[14px] rounded-2xl border-none font-extrabold text-[15px] cursor-pointer disabled:opacity-60"
            style={{ background: 'var(--c-green)', color: 'var(--tg-theme-button-text-color)' }}
          >
            {busy ? 'Завершаем...' : 'Завершить экспедицию'}
          </button>
        )}
      </div>

      {result && (
        <>
          <ResultCard expedition={expedition} result={result} />
          <button
            onClick={onDismiss}
            disabled={busy}
            className="w-full py-[14px] rounded-2xl border-none font-extrabold text-[15px] cursor-pointer disabled:opacity-60"
            style={{ background: 'var(--surface-subtle)', color: 'var(--tg-theme-text-color)' }}
          >
            {busy ? 'Скрываем...' : 'Закрыть результат'}
          </button>
        </>
      )}
    </div>
  );
}

/**
 * The depth picker, and the whole point of the redesign. Depth multiplies the beast's power
 * and the quality of the catch, so the player chooses how hard a fight to take rather than
 * pressing one button forever. The forecast below each option is what makes that a decision
 * instead of a gamble.
 */
function DepthPicker({
  locality,
  depth,
  power,
  onPick,
}: {
  locality: ExpeditionLocality;
  depth: number;
  power: number;
  onPick: (depth: number) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      {locality.depths.map(option => {
        const selected = option.depth === depth;
        const forecast = forecastFor(option, power);
        return (
          <button
            type="button"
            key={option.depth}
            onClick={() => onPick(option.depth)}
            className="w-full rounded-2xl px-4 py-[12px] flex items-center gap-3 text-left border-none"
            style={{
              background: selected
                ? 'color-mix(in srgb, var(--c-gold) 14%, transparent)'
                : 'color-mix(in srgb, var(--tg-theme-hint-color) 6%, transparent)',
              border: `1px solid ${selected ? 'rgba(var(--c-gold-rgb),0.45)' : 'color-mix(in srgb, var(--tg-theme-hint-color) 14%, transparent)'}`,
              cursor: 'pointer',
            }}
          >
            <div className="w-8 h-8 rounded-xl grid place-items-center text-[13px] font-extrabold shrink-0"
                 style={{ background: 'rgba(0,0,0,0.16)', color: selected ? 'var(--c-gold)' : 'var(--tg-theme-hint-color)' }}>
              {option.depth}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <p className="m-0 font-extrabold text-[13px]">{option.name}</p>
                <span className="text-[10px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                  {formatDurationMinutes(option.minutes)}
                </span>
              </div>
              <p className="m-0 text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                зверь {option.wild_power_min}–{option.wild_power_max} · легендарные {option.rarity_percent.legendary}%
              </p>
            </div>
            {forecast && (
              <span className="text-[10px] font-bold px-2 py-[3px] rounded-full shrink-0 whitespace-nowrap"
                    style={{
                      background: `color-mix(in srgb, ${forecast.color} 14%, transparent)`,
                      color: forecast.color,
                      border: `1px solid color-mix(in srgb, ${forecast.color} 30%, transparent)`,
                    }}>
                {forecast.label}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/** Likely grade against this depth's *average* beast, given the squad already selected. */
function forecastFor(option: ExpeditionDepthOption, power: number) {
  if (power <= 0) return null;
  const grade = expeditionGradeFor(power / option.wild_power_avg);
  return EXPEDITION_GRADE_META[grade];
}

export function ExpeditionPage({
  onRefresh,
  onBack,
}: {
  onRefresh: () => void;
  onBack: () => void;
}) {
  const [info, setInfo] = useState<ExpeditionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [selectedLocalityId, setSelectedLocalityId] = useState<number | null>(null);
  const [selectedDepth, setSelectedDepth] = useState(1);
  const [selectedAnimalIds, setSelectedAnimalIds] = useState<number[]>([]);
  const [nowMs, setNowMs] = useState(Date.now());

  const load = useCallback(async () => {
    try {
      const nextInfo = await apiGetExpeditions();
      setInfo(nextInfo);
      setError(null);
      setSelectedLocalityId(current => {
        if (current && nextInfo.localities.some(locality => locality.id === current && !locality.busy)) return current;
        // Land on somewhere the player can actually launch from.
        return (nextInfo.localities.find(locality => !locality.busy) ?? nextInfo.localities[0])?.id ?? null;
      });
      setSelectedAnimalIds(current => current.filter(id => nextInfo.available_animals.some(animal => animal.id === id)));
    } catch (e) {
      setError((e as Error).message ?? 'Ошибка загрузки');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const expeditions = useMemo(() => info?.expeditions ?? [], [info?.expeditions]);

  useEffect(() => {
    // Refresh right after the earliest raid still running runs out. Ones that already
    // expired need no reload — the "Завершить" button appears off the per-second `nowMs`
    // tick, and reloading here would loop on the same still-active-but-expired expedition.
    const pending = expeditions
      .filter(e => e.status === 'active')
      .map(e => new Date(e.ends_at).getTime() - Date.now())
      .filter(leftMs => leftMs > 0);
    if (pending.length === 0) return undefined;
    const timeout = window.setTimeout(() => void load(), Math.min(...pending) + 250);
    return () => window.clearTimeout(timeout);
  }, [expeditions, load]);

  const selectedLocality = useMemo(
    () => info?.localities.find(locality => locality.id === selectedLocalityId) ?? null,
    [info?.localities, selectedLocalityId],
  );

  // Clamp the depth whenever the habitat changes: Fields tops out at 2, Antarctica at 5.
  useEffect(() => {
    if (!selectedLocality) return;
    setSelectedDepth(current => Math.min(current, selectedLocality.max_depth));
  }, [selectedLocality]);

  const availableAnimals = useMemo(
    () => [...(info?.available_animals ?? [])].sort((a, b) => expeditionPower(b) - expeditionPower(a) || b.income - a.income),
    [info?.available_animals],
  );

  const selectedAnimals = useMemo(
    () => availableAnimals.filter(animal => selectedAnimalIds.includes(animal.id)),
    [availableAnimals, selectedAnimalIds],
  );

  const powerMultiplier = info?.power_multiplier ?? 1;
  const genePower = useMemo(
    () => selectedAnimals.reduce((total, animal) => total + expeditionPower(animal), 0),
    [selectedAnimals],
  );
  const selectedPower = squadPower(selectedAnimals, powerMultiplier);

  const squadMin = info?.squad_min ?? 3;
  const squadMax = info?.squad_max ?? 5;
  const squadReady = selectedAnimalIds.length >= squadMin && selectedAnimalIds.length <= squadMax;
  const canStart = Boolean(selectedLocality) && !selectedLocality?.busy && squadReady;

  const depthOption = selectedLocality?.depths.find(option => option.depth === selectedDepth) ?? null;
  const forecast = depthOption ? forecastFor(depthOption, selectedPower) : null;
  const upgradeChance = depthOption && selectedPower > 0
    ? expeditionGeneUpgradeChance(selectedPower / depthOption.wild_power_avg)
    : 0;

  const toggleAnimal = (animalId: number) => {
    setSelectedAnimalIds(current => {
      if (current.includes(animalId)) return current.filter(id => id !== animalId);
      if (current.length >= squadMax) return current;
      return [...current, animalId];
    });
  };

  const run = async (key: string, action: () => Promise<unknown>, fallback: string) => {
    setBusyAction(key);
    setError(null);
    try {
      await action();
      await load();
      onRefresh();
    } catch (e) {
      setError((e as Error).message ?? fallback);
    } finally {
      setBusyAction(null);
    }
  };

  const handleStart = () => {
    if (!canStart || selectedLocalityId === null) return;
    void run('start', async () => {
      await apiStartExpedition(selectedLocalityId, selectedAnimalIds, selectedDepth);
      setSelectedAnimalIds([]);
    }, 'Не удалось отправить экспедицию');
  };

  const readyCount = expeditions.filter(
    e => e.status === 'active' && new Date(e.ends_at).getTime() <= nowMs,
  ).length;
  const freeLocalities = (info?.localities ?? []).filter(locality => !locality.busy).length;

  return (
    <div className="page-content-safe">
      <div className="sticky z-10 bg-tg-bg px-[14px] pt-3 pb-[10px] flex items-center gap-3 border-b" style={{ top: 0, borderColor: 'var(--surface-overlay-border)' }}>
        <button
          onClick={onBack}
          className="flex items-center gap-1 px-3 py-[6px] rounded-lg border bg-transparent text-tg-text cursor-pointer text-[13px]"
          style={{ borderColor: 'var(--surface-overlay-border)' }}
        >
          ‹ Назад
        </button>
        <h2 className="m-0 text-base font-bold flex-1">🧭 Экспедиции</h2>
      </div>

      <div className="px-[14px] pt-4 flex flex-col gap-4">
        <div>
          <p className="m-0 mb-[2px] font-extrabold text-[16px]">Отправляй отряд за новыми видами</p>
          <p className="m-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            По одной экспедиции на каждую местность. Отряд — {squadMin}–{squadMax} животных.
            Чем глубже рейд, тем сильнее зверь и тем ценнее добыча.
          </p>
        </div>

        {error && (
          <div className="rounded-xl px-4 py-3 text-sm"
               style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.25)', color: 'var(--c-red)' }}>
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-8"><div className="spinner" /></div>
        ) : info ? (
          <>
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-2xl p-3 flex flex-col justify-between text-center" style={{ background: 'rgba(var(--c-blue-rgb),0.08)', border: '1px solid rgba(var(--c-blue-rgb),0.2)' }}>
                <p className="m-0 text-[11px] text-tg-hint">Свободные направления</p>
                <p className="m-0 mt-1 text-[18px] font-extrabold leading-none">{freeLocalities}/{info.localities.length}</p>
              </div>
              <div className="rounded-2xl p-3 flex flex-col justify-between text-center" style={{ background: 'rgba(var(--c-green-rgb),0.08)', border: '1px solid rgba(var(--c-green-rgb),0.2)' }}>
                <p className="m-0 text-[11px] text-tg-hint">Свободные животные</p>
                <p className="m-0 mt-1 text-[18px] font-extrabold leading-none">{availableAnimals.length}</p>
              </div>
              <div className="rounded-2xl p-3 flex flex-col justify-between text-center" style={{ background: 'rgba(var(--c-gold-rgb),0.08)', border: '1px solid rgba(var(--c-gold-rgb),0.2)' }}>
                <p className="m-0 text-[11px] text-tg-hint">Бонус к силе</p>
                <p className="m-0 mt-1 text-[18px] font-extrabold leading-none" style={{ color: powerMultiplier > 1 ? 'var(--c-gold)' : 'var(--tg-theme-hint-color)' }}>
                  ×{powerMultiplier.toFixed(2)}
                </p>
              </div>
            </div>

            {powerMultiplier <= 1 && (
              <div className="rounded-xl px-4 py-3 text-[12px]"
                   style={{ background: 'rgba(var(--c-gold-rgb),0.07)', border: '1px solid rgba(var(--c-gold-rgb),0.2)', color: 'var(--tg-theme-hint-color)' }}>
                Гены отряда упираются в потолок: пять идеальных животных дают 90 силы. Дальше растёт
                только снаряжение — предметы кузницы со свойством «Сила в экспедиции» и Экспедиционный
                корпус во вкладке «Развитие». Вместе они дают ×2.2 и открывают глубокие рейды.
              </div>
            )}

            {expeditions.length > 0 && (
              <div className="flex flex-col gap-4">
                <div className="flex items-baseline justify-between gap-3">
                  <p className="m-0 text-[13px] font-bold text-tg-hint tracking-[0.5px]">
                    В ПУТИ · {expeditions.length}
                  </p>
                  {readyCount > 0 && (
                    <span className="text-[12px] font-bold" style={{ color: 'var(--c-green)' }}>
                      Готово к завершению: {readyCount}
                    </span>
                  )}
                </div>
                {expeditions.map(expedition => (
                  <CurrentExpeditionCard
                    key={expedition.id}
                    expedition={expedition}
                    nowMs={nowMs}
                    busy={busyAction === `finish-${expedition.id}` || busyAction === `dismiss-${expedition.id}`}
                    onFinish={() => void run(
                      `finish-${expedition.id}`,
                      () => apiFinishExpedition(expedition.id),
                      'Не удалось завершить экспедицию',
                    )}
                    onDismiss={() => void run(
                      `dismiss-${expedition.id}`,
                      () => apiDismissExpedition(expedition.id),
                      'Не удалось закрыть результат',
                    )}
                  />
                ))}
              </div>
            )}

            <div className="flex flex-col gap-3">
              <div>
                <p className="m-0 mb-2 text-[13px] font-bold text-tg-hint tracking-[0.5px]">НАПРАВЛЕНИЕ</p>
                <div className="flex flex-col gap-2">
                  {info.localities.map(locality => {
                    const habitat = HABITAT_INFO[locality.habitat];
                    const selected = locality.id === selectedLocalityId;
                    return (
                      <button
                        type="button"
                        key={locality.id}
                        disabled={locality.busy}
                        onClick={() => setSelectedLocalityId(locality.id)}
                        className="w-full rounded-2xl px-4 py-[16px] flex items-center gap-3 text-left border-none disabled:opacity-50"
                        style={{
                          // Horizontal gradient banner in the habitat's own colour, like localities.
                          background: `linear-gradient(90deg, color-mix(in srgb, ${habitat.color} ${selected ? 58 : 44}%, transparent) 0%, color-mix(in srgb, ${habitat.color} ${selected ? 26 : 18}%, transparent) 55%, transparent 100%)`,
                          border: `1px solid color-mix(in srgb, ${habitat.color} ${selected ? 55 : 32}%, transparent)`,
                          cursor: locality.busy ? 'default' : 'pointer',
                        }}
                      >
                        <div className="w-12 h-12 rounded-2xl grid place-items-center text-[26px] shrink-0"
                             style={{ background: `color-mix(in srgb, ${habitat.color} 24%, transparent)`, border: `1px solid color-mix(in srgb, ${habitat.color} 42%, transparent)` }}>
                          {habitat.emoji}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="m-0 font-extrabold text-[14px]">{habitat.name}</p>
                            {locality.busy
                              ? <span className="text-[11px] font-bold" style={{ color: 'var(--c-gold)' }}>занято</span>
                              : selected && <span className="text-[11px] font-bold text-[var(--c-green)]">выбрано</span>}
                          </div>
                          <p className="m-0 text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                            сложность {habitat.expeditionDifficulty} · глубина до {locality.max_depth}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {selectedLocality && !selectedLocality.busy && (
                <div>
                  <p className="m-0 mb-2 text-[13px] font-bold text-tg-hint tracking-[0.5px]">ГЛУБИНА РЕЙДА</p>
                  <DepthPicker
                    locality={selectedLocality}
                    depth={selectedDepth}
                    power={selectedPower}
                    onPick={setSelectedDepth}
                  />
                </div>
              )}

              <div>
                <div className="flex items-center justify-between gap-3 mb-2">
                  <p className="m-0 text-[13px] font-bold text-tg-hint tracking-[0.5px]">ЖИВОТНЫЕ ДЛЯ ОТРЯДА</p>
                  <span className="text-[12px]" style={{ color: squadReady ? 'var(--c-green)' : 'var(--tg-theme-hint-color)' }}>
                    {selectedAnimalIds.length}/{squadMax} · сила {selectedPower}
                    {powerMultiplier > 1 ? ` (${genePower}×${powerMultiplier.toFixed(2)})` : ''}
                  </span>
                </div>

                {availableAnimals.length === 0 ? (
                  <div className="card text-center py-8">
                    <p className="m-0 text-[36px] mb-2">🐾</p>
                    <p className="m-0 text-sm text-tg-hint">Нет свободных животных для экспедиции</p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-2">
                    {availableAnimals.map(animal => {
                      const isSelected = selectedAnimalIds.includes(animal.id);
                      const disableToggle = !isSelected && selectedAnimalIds.length >= squadMax;
                      return (
                        <ExpeditionAnimalCard
                          key={animal.id}
                          animal={animal}
                          selected={isSelected}
                          disabled={disableToggle}
                          onToggle={() => toggleAnimal(animal.id)}
                        />
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Sticky launch bar — stays reachable above the tab bar no matter how long
                  the animal list gets, so you never scroll to the very bottom to send. */}
              <div
                className="sticky z-20 -mx-[14px] px-[14px] pt-3 pb-1"
                style={{
                  bottom: 'var(--app-bottom-offset)',
                  background: 'linear-gradient(to top, var(--tg-theme-bg-color) 62%, transparent)',
                }}
              >
                <div className="rounded-2xl p-4 flex flex-col gap-3"
                     style={{ background: 'color-mix(in srgb, var(--c-gold) 10%, var(--tg-theme-bg-color))', border: '1px solid rgba(var(--c-gold-rgb),0.24)', boxShadow: '0 6px 24px rgba(0,0,0,0.4)' }}>
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="m-0 font-extrabold text-[14px]">Запуск экспедиции</p>
                      <p className="m-0 text-[12px] truncate" style={{ color: 'var(--tg-theme-hint-color)' }}>
                        {selectedLocality && depthOption
                          ? `${HABITAT_INFO[selectedLocality.habitat].name} · ${depthOption.name} · ${formatDurationMinutes(depthOption.minutes)}`
                          : 'Сначала выбери свободное направление'}
                      </p>
                    </div>
                    <span className="text-[12px] font-bold shrink-0" style={{ color: squadReady ? 'var(--c-green)' : 'var(--c-gold)' }}>
                      {squadReady ? 'Готово' : `${selectedAnimalIds.length}/${squadMin}–${squadMax}`}
                    </span>
                  </div>

                  {/* The forecast is what turns picking a depth into a decision rather than a
                      gamble: it names the likely grade against this depth's average beast. */}
                  {forecast && depthOption && squadReady && (
                    <div className="rounded-xl px-3 py-[10px]"
                         style={{
                           background: `color-mix(in srgb, ${forecast.color} 10%, transparent)`,
                           border: `1px solid color-mix(in srgb, ${forecast.color} 26%, transparent)`,
                         }}>
                      <p className="m-0 text-[12px] font-bold" style={{ color: forecast.color }}>
                        Вероятно: {forecast.label}
                      </p>
                      <p className="m-0 mt-[2px] text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                        Отряд {selectedPower} против зверя {depthOption.wild_power_min}–{depthOption.wild_power_max}
                        {' '}(в среднем {depthOption.wild_power_avg}). {forecast.blurb}
                        {upgradeChance > 0 && ` Шанс улучшить каждый ген добычи: ${Math.round(upgradeChance * 100)}%.`}
                      </p>
                    </div>
                  )}

                  <button
                    onClick={handleStart}
                    disabled={!canStart || busyAction === 'start'}
                    className="w-full py-[14px] rounded-2xl border-none font-extrabold text-[15px] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ background: 'var(--c-blue)', color: 'var(--tg-theme-button-text-color)' }}
                  >
                    {busyAction === 'start'
                      ? 'Отправляем...'
                      : freeLocalities === 0
                        ? 'Все направления заняты'
                        : 'Отправить в экспедицию'}
                  </button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="card text-center py-8">
            <p className="m-0 mb-3 text-sm text-tg-hint">Не удалось загрузить экспедиции</p>
            <button
              onClick={() => void load()}
              className="px-4 py-[10px] rounded-xl border-none font-bold text-sm cursor-pointer"
              style={{ background: 'var(--c-blue)', color: 'var(--tg-theme-button-text-color)' }}
            >
              Повторить
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
