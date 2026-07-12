import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  apiDismissExpedition,
  apiFinishExpedition,
  apiGetExpeditions,
  apiStartExpedition,
} from '@/api';
import {
  formatDurationMinutes,
  expeditionPower,
  geneColor,
  geneLabel,
  HABITAT_INFO,
  lifeLeft,
} from '@/data/packs';
import type { ActiveExpedition, ExpeditionInfo, ExpeditionResult, Habitat, Animal } from '@/types';
import { formatCountdown, fmt } from '@/utils/format';
import { AnimalArt } from '@/components/AnimalArt';

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
            Дикое животное · {wildHabitat.name} · сила {result.wild_power}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-[6px]">
        {[
          ['survival', result.wild.survival, 'Выж'],
          ['reproduction', result.wild.reproduction, 'Разм'],
          ['appearance', result.wild.appearance, 'Вид'],
          ['size_trait', result.wild.size_trait, 'Размер'],
        ].map(([key, value, short]) => (
          <div
            key={String(key)}
            className="flex items-center gap-2 px-3 py-[7px] rounded-xl"
            style={{
              background: 'color-mix(in srgb, var(--tg-theme-hint-color) 7%, transparent)',
              border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)',
            }}
          >
            <div className="w-2 h-2 rounded-full shrink-0" style={{ background: geneColor(key as never, value as never) }} />
            <span className="text-[10px]" style={{ color: 'var(--tg-theme-hint-color)' }}>{short}</span>
            <span className="ml-auto text-[11px] font-bold" style={{ color: geneColor(key as never, value as never) }}>
              {geneLabel(key as never, value as never)}
            </span>
          </div>
        ))}
      </div>
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

      <div className="grid grid-cols-2 gap-[6px]">
        {[
          ['survival', animal.survival, 'Выж'],
          ['reproduction', animal.reproduction, 'Разм'],
          ['appearance', animal.appearance, 'Вид'],
          ['size_trait', animal.size_trait, 'Размер'],
        ].map(([key, value, short]) => (
          <div
            key={String(key)}
            className="flex items-center gap-2 px-3 py-[7px] rounded-xl"
            style={{
              background: 'color-mix(in srgb, var(--tg-theme-hint-color) 7%, transparent)',
              border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)',
            }}
          >
            <div className="w-2 h-2 rounded-full shrink-0" style={{ background: geneColor(key as never, value as never) }} />
            <span className="text-[10px]" style={{ color: 'var(--tg-theme-hint-color)' }}>{short}</span>
            <span className="ml-auto text-[11px] font-bold" style={{ color: geneColor(key as never, value as never) }}>
              {geneLabel(key as never, value as never)}
            </span>
          </div>
        ))}
      </div>
    </button>
  );
}

function CurrentExpeditionCard({
  expedition,
  nowMs,
  finishing,
  dismissing,
  onFinish,
  onDismiss,
}: {
  expedition: ActiveExpedition;
  nowMs: number;
  finishing: boolean;
  dismissing: boolean;
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
            <p className="m-0 font-extrabold text-[15px] truncate">Экспедиция в {habitat.name}</p>
            <p className="m-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
              {expedition.animals.length} животных · сила отряда {partyPower}
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
                {lost && <span className="text-[11px] font-bold text-[var(--c-red-soft)]">Погиб</span>}
              </div>
            );
          })}
        </div>

        {isReadyToFinish && (
          <button
            onClick={onFinish}
            disabled={finishing}
            className="w-full py-[14px] rounded-2xl border-none font-extrabold text-[15px] cursor-pointer disabled:opacity-60"
            style={{ background: 'var(--c-green)', color: 'var(--tg-theme-button-text-color)' }}
          >
            {finishing ? 'Завершаем...' : 'Завершить экспедицию'}
          </button>
        )}
      </div>

      {result && (
        <>
          <div className="rounded-2xl p-4 flex flex-col gap-3"
               style={{
                 background: result.outcome === 'victory' ? 'rgba(var(--c-green-rgb),0.08)' : 'rgba(var(--c-red-rgb),0.08)',
                 border: result.outcome === 'victory' ? '1px solid rgba(var(--c-green-rgb),0.25)' : '1px solid rgba(var(--c-red-rgb),0.25)',
               }}>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="m-0 font-extrabold text-[15px]">
                  {result.outcome === 'victory' ? 'Победа' : 'Провал'}
                </p>
                <p className="m-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                  Сила отряда {result.squad_power} vs дикая сила {result.wild_power}
                </p>
              </div>
              <span className="text-[28px]">{result.outcome === 'victory' ? '🏆' : '💀'}</span>
            </div>

            {result.outcome === 'victory' && result.captured_animal && (
              <div>
                <p className="m-0 mb-2 text-[12px] font-bold text-[var(--c-green)]">НАГРАДА</p>
                <ExpeditionAnimalCard animal={result.captured_animal} />
              </div>
            )}

            {result.outcome === 'defeat' && (
              <p className="m-0 text-[13px] text-[var(--c-red-soft)]">
                Отряд оказался слабее. Одно случайное животное погибло, остальные вернулись домой.
              </p>
            )}
          </div>

          <WildAnimalSummary habitat={expedition.habitat} result={result} />

          <button
            onClick={onDismiss}
            disabled={dismissing}
            className="w-full py-[14px] rounded-2xl border-none font-extrabold text-[15px] cursor-pointer disabled:opacity-60"
            style={{ background: 'var(--surface-subtle)', color: 'var(--tg-theme-text-color)' }}
          >
            {dismissing ? 'Скрываем...' : 'Закрыть результат'}
          </button>
        </>
      )}
    </div>
  );
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
  const [busyAction, setBusyAction] = useState<'start' | 'finish' | 'dismiss' | null>(null);
  const [selectedLocalityId, setSelectedLocalityId] = useState<number | null>(null);
  const [selectedAnimalIds, setSelectedAnimalIds] = useState<number[]>([]);
  const [nowMs, setNowMs] = useState(Date.now());

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const nextInfo = await apiGetExpeditions();
      setInfo(nextInfo);
      setError(null);
      setSelectedLocalityId(current => {
        if (current && nextInfo.localities.some(locality => locality.id === current)) return current;
        return nextInfo.localities[0]?.id ?? null;
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

  const activeExpedition = info?.active;

  useEffect(() => {
    const active = activeExpedition;
    if (!active || active.status !== 'active') return undefined;
    const leftMs = new Date(active.ends_at).getTime() - Date.now();
    // Already expired: the "Завершить" button appears via the per-second `nowMs` tick, so
    // there's nothing to reload. Reloading here would loop — `load()` returns the same
    // still-active-but-expired expedition, whose new object reference re-fires this effect.
    if (leftMs <= 0) return undefined;
    // Still running: refresh once, right after the timer runs out.
    const timeout = window.setTimeout(() => void load(), leftMs + 250);
    return () => window.clearTimeout(timeout);
  }, [activeExpedition, load]);

  const selectedLocality = useMemo(
    () => info?.localities.find(locality => locality.id === selectedLocalityId) ?? null,
    [info?.localities, selectedLocalityId],
  );

  const availableAnimals = useMemo(
    () => [...(info?.available_animals ?? [])].sort((a, b) => expeditionPower(b) - expeditionPower(a) || b.income - a.income),
    [info?.available_animals],
  );

  const selectedAnimals = useMemo(
    () => availableAnimals.filter(animal => selectedAnimalIds.includes(animal.id)),
    [availableAnimals, selectedAnimalIds],
  );

  const selectedPower = useMemo(
    () => selectedAnimals.reduce((total, animal) => total + expeditionPower(animal), 0),
    [selectedAnimals],
  );

  const canStart = !info?.active && selectedLocalityId !== null && selectedAnimalIds.length >= 3 && selectedAnimalIds.length <= 5;

  const toggleAnimal = (animalId: number) => {
    setSelectedAnimalIds(current => {
      if (current.includes(animalId)) return current.filter(id => id !== animalId);
      if (current.length >= 5) return current;
      return [...current, animalId];
    });
  };

  const handleStart = async () => {
    if (!canStart || selectedLocalityId === null) return;
    setBusyAction('start');
    setError(null);
    try {
      await apiStartExpedition(selectedLocalityId, selectedAnimalIds);
      setSelectedAnimalIds([]);
      await load();
      onRefresh();
    } catch (e) {
      setError((e as Error).message ?? 'Не удалось отправить экспедицию');
    } finally {
      setBusyAction(null);
    }
  };

  const handleFinish = async () => {
    setBusyAction('finish');
    setError(null);
    try {
      await apiFinishExpedition();
      await load();
      onRefresh();
    } catch (e) {
      setError((e as Error).message ?? 'Не удалось завершить экспедицию');
    } finally {
      setBusyAction(null);
    }
  };

  const handleDismiss = async () => {
    setBusyAction('dismiss');
    setError(null);
    try {
      await apiDismissExpedition();
      await load();
      onRefresh();
    } catch (e) {
      setError((e as Error).message ?? 'Не удалось закрыть результат');
    } finally {
      setBusyAction(null);
    }
  };

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
            1 активная экспедиция одновременно. В отряд можно взять от 3 до 5 животных.
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
                <p className="m-0 text-[11px] text-tg-hint">Направления</p>
                <p className="m-0 mt-1 text-[18px] font-extrabold leading-none">{info.localities.length}</p>
              </div>
              <div className="rounded-2xl p-3 flex flex-col justify-between text-center" style={{ background: 'rgba(var(--c-green-rgb),0.08)', border: '1px solid rgba(var(--c-green-rgb),0.2)' }}>
                <p className="m-0 text-[11px] text-tg-hint">Свободные животные</p>
                <p className="m-0 mt-1 text-[18px] font-extrabold leading-none">{availableAnimals.length}</p>
              </div>
              <div className="rounded-2xl p-3 flex flex-col justify-between text-center" style={{ background: 'rgba(var(--c-gold-rgb),0.08)', border: '1px solid rgba(var(--c-gold-rgb),0.2)' }}>
                <p className="m-0 text-[11px] text-tg-hint">Статус</p>
                <p className="m-0 mt-1 text-[16px] font-extrabold leading-none" style={{ color: info.active ? 'var(--c-gold)' : 'var(--c-green)' }}>
                  {info.active ? 'Занята' : 'Свободна'}
                </p>
              </div>
            </div>

            {info.active && (
              <CurrentExpeditionCard
                expedition={info.active}
                nowMs={nowMs}
                finishing={busyAction === 'finish'}
                dismissing={busyAction === 'dismiss'}
                onFinish={() => void handleFinish()}
                onDismiss={() => void handleDismiss()}
              />
            )}

            <div className="flex flex-col gap-3">
              <div>
                <p className="m-0 mb-2 text-[13px] font-bold text-tg-hint tracking-[0.5px]">НАПРАВЛЕНИЕ</p>
                <div className="flex flex-col gap-2">
                  {info.localities.map(locality => {
                    const habitat = HABITAT_INFO[locality.habitat];
                    const selected = locality.id === selectedLocalityId;
                    const duration = info.expedition_minutes[locality.habitat];
                    return (
                      <button
                        type="button"
                        key={locality.id}
                        disabled={Boolean(info.active)}
                        onClick={() => setSelectedLocalityId(locality.id)}
                        className="w-full rounded-2xl px-4 py-[16px] flex items-center gap-3 text-left border-none disabled:opacity-65"
                        style={{
                          // Horizontal gradient banner in the habitat's own colour, like localities.
                          background: `linear-gradient(90deg, color-mix(in srgb, ${habitat.color} ${selected ? 58 : 44}%, transparent) 0%, color-mix(in srgb, ${habitat.color} ${selected ? 26 : 18}%, transparent) 55%, transparent 100%)`,
                          border: `1px solid color-mix(in srgb, ${habitat.color} ${selected ? 55 : 32}%, transparent)`,
                          cursor: info.active ? 'default' : 'pointer',
                        }}
                      >
                        <div className="w-12 h-12 rounded-2xl grid place-items-center text-[26px] shrink-0"
                             style={{ background: `color-mix(in srgb, ${habitat.color} 24%, transparent)`, border: `1px solid color-mix(in srgb, ${habitat.color} 42%, transparent)` }}>
                          {habitat.emoji}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="m-0 font-extrabold text-[14px]">{habitat.name}</p>
                            {selected && <span className="text-[11px] font-bold text-[var(--c-green)]">выбрано</span>}
                          </div>
                          <p className="m-0 text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                            {formatDurationMinutes(duration)} · сложность {habitat.expeditionDifficulty} · награда {habitat.expeditionReward}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between gap-3 mb-2">
                  <p className="m-0 text-[13px] font-bold text-tg-hint tracking-[0.5px]">ЖИВОТНЫЕ ДЛЯ ОТРЯДА</p>
                  <span className="text-[12px]" style={{ color: selectedAnimalIds.length >= 3 && selectedAnimalIds.length <= 5 ? 'var(--c-green)' : 'var(--tg-theme-hint-color)' }}>
                    {selectedAnimalIds.length}/5 · сила {selectedPower}
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
                      const disableToggle = Boolean(info.active) || (!isSelected && selectedAnimalIds.length >= 5);
                      return (
                        <ExpeditionAnimalCard
                          key={animal.id}
                          animal={animal}
                          selected={isSelected}
                          disabled={disableToggle}
                          onToggle={info.active ? undefined : () => toggleAnimal(animal.id)}
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
                        {selectedLocality
                          ? `Направление: ${HABITAT_INFO[selectedLocality.habitat].name}`
                          : 'Сначала выбери направление'}
                      </p>
                    </div>
                    <span className="text-[12px] font-bold shrink-0" style={{ color: selectedAnimalIds.length >= 3 && selectedAnimalIds.length <= 5 ? 'var(--c-green)' : 'var(--c-gold)' }}>
                      {selectedAnimalIds.length >= 3 && selectedAnimalIds.length <= 5 ? 'Готово' : `${selectedAnimalIds.length}/3–5`}
                    </span>
                  </div>

                  <button
                    onClick={() => void handleStart()}
                    disabled={!canStart || busyAction === 'start'}
                    className="w-full py-[14px] rounded-2xl border-none font-extrabold text-[15px] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ background: 'var(--c-blue)', color: 'var(--tg-theme-button-text-color)' }}
                  >
                    {busyAction === 'start' ? 'Отправляем...' : info.active ? 'Сначала заверши текущую экспедицию' : 'Отправить в экспедицию'}
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
