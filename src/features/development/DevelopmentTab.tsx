import { useEffect, useState } from 'react';
import type { GameState, Habitat, LocalitiesInfo } from '@/types';
import { apiGetLocalities, apiUpgradeDevelopment, apiUpgradeLocality } from '@/api';
import { fmt } from '@/utils/format';

const HABITATS: Record<Habitat, { emoji: string; name: string; color: string }> = {
  desert: { emoji: '🏜️', name: 'Пустыня', color: 'var(--c-gold)' },
  mountains: { emoji: '⛰️', name: 'Горы', color: 'var(--tg-theme-hint-color)' },
  forest: { emoji: '🌲', name: 'Лес', color: 'var(--c-green)' },
  fields: { emoji: '🌾', name: 'Поля', color: 'var(--c-teal)' },
  antarctica: { emoji: '🏔️', name: 'Антарктида', color: 'var(--c-cyan)' },
};

type GlobalTrack = 'vet' | 'genetics';

function LevelDots({ level }: { level: number }) {
  return <div className="flex gap-1" aria-label={`Уровень ${level} из 3`}>{[1, 2, 3].map(step => <span key={step} className="w-2 h-2 rounded-full" style={{ background: step <= level ? 'var(--c-gold)' : 'rgba(255,255,255,0.16)', boxShadow: step <= level ? '0 0 8px rgba(var(--c-gold-rgb),0.5)' : 'none' }} />)}</div>;
}

function TrackCard({ kind, level, busy, onUpgrade }: { kind: GlobalTrack; level: number; busy: boolean; onUpgrade: () => void }) {
  const vet = kind === 'vet';
  const nextCost = vet ? [750, 2_000, 5_000][level] : [1_000, 2_500, 6_000][level];
  const maxed = level >= 3;
  return (
    <div className="rounded-2xl p-3" style={{ background: vet ? 'linear-gradient(140deg, rgba(var(--c-cyan-rgb),0.13), var(--surface-subtle) 62%)' : 'linear-gradient(140deg, rgba(var(--c-purple-rgb),0.14), var(--surface-subtle) 62%)', border: `1px solid ${vet ? 'rgba(var(--c-cyan-rgb),0.28)' : 'rgba(var(--c-purple-rgb),0.30)'}` }}>
      <div className="flex items-start gap-3">
        <div className="w-11 h-11 rounded-[14px] grid place-items-center text-[23px] shrink-0" style={{ background: vet ? 'rgba(var(--c-cyan-rgb),0.14)' : 'rgba(var(--c-purple-rgb),0.15)' }}>{vet ? '🩺' : '🧬'}</div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2"><p className="m-0 text-[14px] font-extrabold">{vet ? 'Ветеринарный блок' : 'Генетический центр'}</p><LevelDots level={level} /></div>
          <p className="m-0 mt-1 text-[11px] leading-[1.4] text-tg-hint">{vet ? 'Меньше болезней и дешевле лечение.' : 'Лучше шанс на потомство и сильные гены.'}</p>
        </div>
      </div>
      <div className="mt-3 rounded-xl px-3 py-2 text-[11px]" style={{ background: 'rgba(0,0,0,0.12)' }}>
        {level === 0 && (vet ? 'Базовая клиника' : 'Базовая лаборатория')}
        {level > 0 && vet && `−${level * 15}% шанс болезни · −${level * 10}% лечение`}
        {level > 0 && !vet && `+${level * 5} п.п. к скрещиванию · лучшее наследование генов`}
      </div>
      <button type="button" disabled={busy || maxed} onClick={onUpgrade} className="w-full mt-3 rounded-xl py-2 border-none text-[12px] font-extrabold" style={{ background: maxed ? 'rgba(255,255,255,0.08)' : vet ? 'var(--c-cyan)' : 'var(--c-purple)', color: maxed ? 'var(--tg-theme-hint-color)' : 'var(--tg-theme-button-text-color)' }}>
        {maxed ? 'Максимальный уровень' : `Улучшить за ₽${fmt(nextCost)}`}
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
        <div className="flex items-center gap-2"><span className="text-[25px]">🏗️</span><div><p className="m-0 font-extrabold text-[16px]">Развитие зоопарка</p><p className="m-0 mt-1 text-[11px] text-tg-hint">Вкладывай рубли в то, что важнее именно сейчас.</p></div></div>
        <div className="mt-3 flex items-center justify-between gap-3"><span className="text-[11px] text-tg-hint">Чистый доход</span><span className="font-display text-[17px]" style={{ color: gs.income_rub_per_min - gs.upkeep_rub_per_min >= 0 ? 'var(--c-green)' : 'var(--c-orange)' }}>₽ {fmt(gs.income_rub_per_min - gs.upkeep_rub_per_min)}/мин</span></div>
      </div>

      {error && <div className="rounded-xl px-3 py-2 text-[12px]" style={{ color: 'var(--c-red-soft)', background: 'rgba(var(--c-red-rgb),0.11)', border: '1px solid rgba(var(--c-red-rgb),0.25)' }}>⚠️ {error}</div>}

      <div><p className="m-0 mb-2 px-1 text-[11px] font-extrabold uppercase tracking-[0.7px] text-tg-hint">Глобальные направления</p><div className="flex flex-col gap-2"><TrackCard kind="vet" level={gs.vet_level} busy={busy !== null} onUpgrade={() => void upgradeTrack('vet')} /><TrackCard kind="genetics" level={gs.genetics_level} busy={busy !== null} onUpgrade={() => void upgradeTrack('genetics')} /></div></div>

      <div><div className="flex items-baseline justify-between gap-3 mb-2 px-1"><p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.7px] text-tg-hint">Инфраструктура местностей</p><span className="text-[10px] text-tg-hint">бонус содержания</span></div>{loading ? <div className="card text-center text-[12px] text-tg-hint">Загружаем местности…</div> : <div className="flex flex-col gap-2">{info?.localities.map(locality => { const habitat = HABITATS[locality.habitat]; const maxed = locality.upgrade_cost_rub === null; return <div key={locality.id} className="rounded-2xl p-3" style={{ background: 'var(--surface-subtle)', border: `1px solid color-mix(in srgb, ${habitat.color} 28%, transparent)` }}><div className="flex items-center gap-3"><div className="w-10 h-10 rounded-xl grid place-items-center text-[22px]" style={{ background: `color-mix(in srgb, ${habitat.color} 16%, transparent)` }}>{habitat.emoji}</div><div className="flex-1 min-w-0"><div className="flex items-center gap-2"><p className="m-0 text-[13px] font-extrabold">{habitat.name}</p><LevelDots level={locality.level} /></div><p className="m-0 mt-1 text-[11px] text-tg-hint">{locality.animals.length} животных · −{locality.upkeep_discount_percent}% содержания</p></div><button type="button" disabled={busy !== null || maxed} onClick={() => void upgradeLocality(locality.id)} className="rounded-xl px-3 py-2 border-none text-[11px] font-extrabold" style={{ background: maxed ? 'rgba(255,255,255,0.08)' : habitat.color, color: maxed ? 'var(--tg-theme-hint-color)' : '#161616' }}>{maxed ? 'MAX' : `₽${fmt(locality.upgrade_cost_rub ?? 0)}`}</button></div></div>; })}</div>}</div>
    </div>
  );
}
