import { useEffect, useState } from 'react';
import type { DevelopmentTrack, GameState, Habitat, LocalitiesInfo } from '@/types';
import { apiGetLocalities, apiUpgradeDevelopment, apiUpgradeLocality } from '@/api';
import { fmt } from '@/utils/format';

const HABITATS: Record<Habitat, { emoji: string; name: string; color: string }> = {
  desert: { emoji: '🏜️', name: 'Пустыня', color: 'var(--c-gold)' },
  mountains: { emoji: '⛰️', name: 'Горы', color: 'var(--tg-theme-hint-color)' },
  forest: { emoji: '🌲', name: 'Лес', color: 'var(--c-green)' },
  fields: { emoji: '🌾', name: 'Поля', color: 'var(--c-teal)' },
  antarctica: { emoji: '🏔️', name: 'Антарктида', color: 'var(--c-cyan)' },
};

type GlobalTrack = DevelopmentTrack;
type TrackLevel = { level: number; cost: number; effects: string[] };

const TRACKS: Record<GlobalTrack, {
  icon: string;
  title: string;
  summary: string;
  accent: string;
  levels: TrackLevel[];
}> = {
  vet: {
    icon: '🩺',
    title: 'Ветеринарный блок',
    summary: 'Животные реже болеют, а лечение обходится дешевле.',
    accent: 'var(--c-cyan)',
    levels: [
      { level: 1, cost: 20_000, effects: ['болезни случаются на 1% реже', 'лечение дешевле на 1%'] },
      { level: 2, cost: 100_000, effects: ['болезни случаются на 3% реже', 'лечение дешевле на 3%'] },
      { level: 3, cost: 400_000, effects: ['болезни случаются на 6% реже', 'лечение дешевле на 6%'] },
      { level: 4, cost: 1_500_000, effects: ['болезни случаются на 9% реже', 'лечение дешевле на 9%'] },
      { level: 5, cost: 5_000_000, effects: ['болезни случаются на 12% реже', 'лечение дешевле на 12%'] },
    ],
  },
  genetics: {
    icon: '🧬',
    title: 'Генетический центр',
    summary: 'Больше удачных потомков и меньше шансов получить слабые гены.',
    accent: 'var(--c-purple)',
    levels: [
      { level: 1, cost: 30_000, effects: ['к шансу успешного скрещивания добавляется 1%', 'шанс получить слабейший ген ниже на 1%'] },
      { level: 2, cost: 150_000, effects: ['к шансу успешного скрещивания добавляется 3%', 'шанс получить слабейший ген ниже на 3%'] },
      { level: 3, cost: 600_000, effects: ['к шансу успешного скрещивания добавляется 6%', 'шанс получить слабейший ген ниже на 6%'] },
      { level: 4, cost: 2_000_000, effects: ['к шансу успешного скрещивания добавляется 9%', 'шанс получить слабейший ген ниже на 9%'] },
      { level: 5, cost: 7_000_000, effects: ['к шансу успешного скрещивания добавляется 12%', 'шанс получить слабейший ген ниже на 12%'] },
    ],
  },
  // Mirrors `catalog.EXPEDITION_CORPS_POWER_PERCENT_BY_LEVEL`. Unlike the other two tracks
  // this one is not a gentle nudge: genes cap a five-animal squad at 90 power, so without a
  // multiplier no amount of breeding could ever reach the deepest raids.
  expedition: {
    icon: '🧭',
    title: 'Экспедиционный корпус',
    summary: 'Отряд бьёт сильнее, чем позволяют гены, — и открывает глубокие рейды.',
    accent: 'var(--c-gold)',
    levels: [
      { level: 1, cost: 50_000, effects: ['сила отряда выше на 8%'] },
      { level: 2, cost: 250_000, effects: ['сила отряда выше на 18%'] },
      { level: 3, cost: 900_000, effects: ['сила отряда выше на 30%'] },
      { level: 4, cost: 3_000_000, effects: ['сила отряда выше на 44%'] },
      { level: 5, cost: 9_000_000, effects: ['сила отряда выше на 60%'] },
    ],
  },
};

function LevelDots({ level, max = 5 }: { level: number; max?: number }) {
  return (
    <div className="flex gap-1" aria-label={`Уровень ${level} из ${max}`}>
      {Array.from({ length: max }, (_, index) => index + 1).map(step => (
        <span key={step} className="w-2 h-2 rounded-full" style={{ background: step <= level ? 'var(--c-gold)' : 'rgba(255,255,255,0.16)', boxShadow: step <= level ? '0 0 8px rgba(var(--c-gold-rgb),0.5)' : 'none' }} />
      ))}
    </div>
  );
}

function EffectLines({ effects }: { effects: string[] }) {
  return <ul className="m-0 pl-4 text-[11px] leading-[1.55] text-tg-hint">{effects.map(effect => <li key={effect}>{effect}</li>)}</ul>;
}

function animalLabel(count: number) {
  const mod10 = count % 10;
  const mod100 = count % 100;
  const noun = mod10 === 1 && mod100 !== 11 ? 'животное' : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14) ? 'животных' : 'животных';
  return `${count} ${noun}`;
}

function TrackCard({ kind, level, busy, onUpgrade }: { kind: GlobalTrack; level: number; busy: boolean; onUpgrade: () => void }) {
  const track = TRACKS[kind];
  const current = track.levels[level - 1];
  const next = track.levels[level];
  const maxed = !next;

  return (
    <div className="rounded-2xl p-3" style={{ background: `linear-gradient(140deg, color-mix(in srgb, ${track.accent} 14%, transparent), var(--surface-subtle) 62%)`, border: `1px solid color-mix(in srgb, ${track.accent} 30%, transparent)` }}>
      <div className="flex items-start gap-3">
        <div className="w-11 h-11 rounded-[14px] grid place-items-center text-[23px] shrink-0" style={{ background: `color-mix(in srgb, ${track.accent} 16%, transparent)` }}>{track.icon}</div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2"><p className="m-0 text-[14px] font-extrabold">{track.title}</p><LevelDots level={level} /></div>
          <p className="m-0 mt-1 text-[11px] leading-[1.45] text-tg-hint">{track.summary}</p>
        </div>
      </div>

      <div className="mt-3 rounded-xl px-3 py-2" style={{ background: 'rgba(0,0,0,0.12)' }}>
        <p className="m-0 text-[10px] font-extrabold uppercase tracking-[0.6px] text-tg-hint">Сейчас · уровень {level}</p>
        {current ? <EffectLines effects={current.effects} /> : <p className="m-0 mt-1 text-[11px] text-tg-hint">Базовый уровень без дополнительных бонусов.</p>}
      </div>

      {!maxed && next && <div className="mt-2 rounded-xl px-3 py-2" style={{ background: `color-mix(in srgb, ${track.accent} 10%, transparent)`, border: `1px solid color-mix(in srgb, ${track.accent} 18%, transparent)` }}>
        <p className="m-0 text-[10px] font-extrabold uppercase tracking-[0.6px]" style={{ color: track.accent }}>Следующий шаг · уровень {next.level}</p>
        <EffectLines effects={next.effects} />
      </div>}

      <details className="mt-2">
        <summary className="cursor-pointer text-[11px] font-bold text-tg-hint">Показать все 5 уровней</summary>
        <div className="mt-2 flex flex-col gap-1">{track.levels.map(item => <div key={item.level} className="flex gap-2 rounded-lg px-2 py-1.5 text-[10px]" style={{ background: item.level <= level ? 'rgba(var(--c-gold-rgb),0.08)' : 'rgba(255,255,255,0.035)', opacity: item.level < level ? 0.62 : 1 }}><span className="w-8 shrink-0 font-extrabold">{item.level <= level ? '✓' : `Ур. ${item.level}`}</span><span className="flex-1 text-tg-hint">{item.effects[0]}</span><span className="shrink-0 font-bold">₽{fmt(item.cost)}</span></div>)}</div>
      </details>

      <button type="button" disabled={busy || maxed} onClick={onUpgrade} className="w-full mt-3 rounded-xl py-2 border-none text-[12px] font-extrabold" style={{ background: maxed ? 'rgba(255,255,255,0.08)' : track.accent, color: maxed ? 'var(--tg-theme-hint-color)' : 'var(--tg-theme-button-text-color)' }}>
        {maxed ? 'Все уровни открыты' : `Улучшить за ₽${fmt(next?.cost ?? 0)}`}
      </button>
    </div>
  );
}

export function DevelopmentTab({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [info, setInfo] = useState<LocalitiesInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setError(null);
      setInfo(await apiGetLocalities());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось загрузить развитие');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const upgradeTrack = async (kind: GlobalTrack) => {
    setBusy(kind);
    try {
      await apiUpgradeDevelopment(kind);
      onRefresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось улучшить направление');
    } finally {
      setBusy(null);
    }
  };

  const upgradeLocality = async (id: number) => {
    setBusy(`locality-${id}`);
    try {
      await apiUpgradeLocality(id);
      await load();
      onRefresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось улучшить местность');
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="px-[14px] pt-3 pb-5 flex flex-col gap-3">
      <div className="rounded-[22px] p-4" style={{ background: 'radial-gradient(circle at 100% 0%, rgba(var(--c-gold-rgb),0.24), transparent 48%), linear-gradient(145deg, rgba(var(--c-gold-rgb),0.12), var(--surface-subtle) 68%)', border: '1px solid rgba(var(--c-gold-rgb),0.28)' }}>
        <div className="flex items-center gap-2"><span className="text-[25px]">🏗️</span><div><p className="m-0 font-extrabold text-[16px]">Развитие зоопарка</p><p className="m-0 mt-1 text-[11px] text-tg-hint">Выбирай, куда направить рубли: стабильность, генетику, экспедиции или содержание.</p></div></div>
      </div>

      {error && <div className="rounded-xl px-3 py-2 text-[12px]" style={{ color: 'var(--c-red-soft)', background: 'rgba(var(--c-red-rgb),0.11)', border: '1px solid rgba(var(--c-red-rgb),0.25)' }}>⚠️ {error}</div>}

      <div><p className="m-0 mb-2 px-1 text-[11px] font-extrabold uppercase tracking-[0.7px] text-tg-hint">Глобальные направления</p><div className="flex flex-col gap-2"><TrackCard kind="vet" level={gs.vet_level} busy={busy !== null} onUpgrade={() => void upgradeTrack('vet')} /><TrackCard kind="genetics" level={gs.genetics_level} busy={busy !== null} onUpgrade={() => void upgradeTrack('genetics')} /><TrackCard kind="expedition" level={gs.expedition_level} busy={busy !== null} onUpgrade={() => void upgradeTrack('expedition')} /></div></div>

      <div>
        <div className="flex items-baseline justify-between gap-3 mb-2 px-1"><p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.7px] text-tg-hint">Инфраструктура местностей</p><span className="text-[10px] text-tg-hint">до 5 уровней</span></div>
        {loading ? <div className="card text-center text-[12px] text-tg-hint">Загружаем местности…</div> : <div className="flex flex-col gap-2">{info?.localities.map(locality => {
          const habitat = HABITATS[locality.habitat];
          const maxed = locality.upgrade_cost_rub === null;
          const nextDiscount = locality.next_upkeep_discount_percent;
          return (
            <div key={locality.id} className="rounded-2xl p-3" style={{ background: 'var(--surface-subtle)', border: `1px solid color-mix(in srgb, ${habitat.color} 28%, transparent)` }}>
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl grid place-items-center text-[22px] shrink-0" style={{ background: `color-mix(in srgb, ${habitat.color} 16%, transparent)` }}>{habitat.emoji}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2"><p className="m-0 text-[13px] font-extrabold">{habitat.name}</p><LevelDots level={locality.level} /></div>
                  <div className="mt-2 rounded-xl px-3 py-2" style={{ background: 'rgba(0,0,0,0.12)' }}>
                    <p className="m-0 text-[10px] font-extrabold uppercase tracking-[0.6px] text-tg-hint">Сейчас</p>
                    <p className="m-0 mt-1 text-[11px] text-tg-hint">Содержание животных дешевле на {locality.upkeep_discount_percent}%.</p>
                    <p className="m-0 mt-1 text-[11px] text-tg-hint">Внутри: {animalLabel(locality.animals.length)}.</p>
                  </div>
                  {!maxed && <div className="mt-2 rounded-xl px-3 py-2" style={{ background: `color-mix(in srgb, ${habitat.color} 10%, transparent)`, border: `1px solid color-mix(in srgb, ${habitat.color} 18%, transparent)` }}>
                    <p className="m-0 text-[10px] font-extrabold uppercase tracking-[0.6px]" style={{ color: habitat.color }}>Что даст улучшение</p>
                    <p className="m-0 mt-1 text-[11px] text-tg-hint">Содержание животных будет дешевле на {nextDiscount}%.</p>
                  </div>}
                </div>
              </div>
              <button type="button" disabled={busy !== null || maxed} onClick={() => void upgradeLocality(locality.id)} className="w-full mt-3 rounded-xl py-2 border-none text-[11px] font-extrabold" style={{ background: maxed ? 'rgba(255,255,255,0.08)' : habitat.color, color: maxed ? 'var(--tg-theme-hint-color)' : '#161616' }}>{maxed ? 'Местность улучшена полностью' : `Улучшить за ₽${fmt(locality.upgrade_cost_rub ?? 0)}`}</button>
            </div>
          );
        })}</div>}
      </div>
    </div>
  );
}
