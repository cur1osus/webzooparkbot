import { useEffect, useState } from 'react';
import { fmt } from '../utils/format';
import type { GameState, PackAnimal, PackInfo } from '../types';
import { apiGetPacksInfo, apiOpenPack } from '../api';

// ─── Display helpers ──────────────────────────────────────────────────────────

const HABITAT_INFO: Record<string, { emoji: string; name: string; color: string }> = {
  desert:     { emoji: '🐪', name: 'Пустыня',     color: 'var(--c-gold)' },
  mountains:  { emoji: '🦅', name: 'Горы',         color: 'var(--tg-theme-hint-color)' },
  forest:     { emoji: '🐆', name: 'Густой лес',   color: 'var(--c-green)' },
  fields:     { emoji: '🐴', name: 'Поля',          color: 'var(--c-teal)' },
  antarctica: { emoji: '🐧', name: 'Антарктида',   color: 'var(--c-cyan)' },
};

const GENE_LABELS: Record<string, Record<string, { label: string; color: string }>> = {
  survival: {
    low:    { label: 'Слабый',       color: 'var(--c-orange)' },
    medium: { label: 'Обычный',      color: 'var(--tg-theme-hint-color)' },
    high:   { label: 'Долгожитель',  color: 'var(--c-green)' },
  },
  reproduction: {
    low:    { label: 'Неохотно',   color: 'var(--c-orange)' },
    medium: { label: 'Обычно',     color: 'var(--tg-theme-hint-color)' },
    high:   { label: 'Активное',   color: 'var(--c-green)' },
  },
  appearance: {
    low:    { label: 'Уродец',         color: 'var(--c-orange)' },
    medium: { label: 'Обычный',        color: 'var(--tg-theme-hint-color)' },
    high:   { label: 'Привлекательный', color: 'var(--c-gold)' },
  },
  size_trait: {
    low:    { label: 'Маленький', color: 'var(--tg-theme-hint-color)' },
    medium: { label: 'Обычный',   color: 'var(--tg-theme-hint-color)' },
    high:   { label: 'Гигант',    color: 'var(--c-gold)' },
  },
};

function geneColor(key: string, val: string) {
  return GENE_LABELS[key]?.[val]?.color ?? 'var(--tg-theme-hint-color)';
}
function geneLabel(key: string, val: string) {
  return GENE_LABELS[key]?.[val]?.label ?? val;
}

function lifeLeft(diesAt: string | null): { label: string; color: string } | null {
  if (!diesAt) return null;
  const ms = new Date(diesAt).getTime() - Date.now();
  if (ms <= 0) return { label: 'Умер', color: 'var(--c-red)' };
  const totalHours = Math.floor(ms / 3_600_000);
  const days = Math.floor(totalHours / 24);
  const hours = totalHours % 24;
  const label = days > 0 ? `${days}д ${hours}ч` : `${hours}ч`;
  const color = totalHours < 24 ? 'var(--c-red)' : totalHours < 48 ? 'var(--c-amber)' : 'var(--c-green)';
  return { label, color };
}

function qualityScore(a: PackAnimal): number {
  const w = { low: 0, medium: 1, high: 2 } as Record<string, number>;
  return w[a.survival] + w[a.reproduction] + w[a.appearance] + w[a.size_trait];
}

function qualityLabel(score: number): { text: string; color: string } {
  if (score >= 7) return { text: 'Идеальный',    color: 'var(--c-gold)' };
  if (score >= 5) return { text: 'Отличный',     color: 'var(--c-blue)' };
  if (score >= 3) return { text: 'Хороший',      color: 'var(--c-green)' };
  if (score >= 1) return { text: 'Посредственный', color: 'var(--tg-theme-hint-color)' };
  return             { text: 'Слабый',          color: 'var(--c-orange)' };
}

// ─── Animal card ──────────────────────────────────────────────────────────────

function AnimalCard({ animal, isNew }: { animal: PackAnimal; isNew: boolean }) {
  const hab  = HABITAT_INFO[animal.habitat];
  const ql   = qualityLabel(qualityScore(animal));
  const genes: [string, string][] = [
    ['survival',     animal.survival],
    ['reproduction', animal.reproduction],
    ['appearance',   animal.appearance],
    ['size_trait',   animal.size_trait],
  ];

  return (
    <div
      className="rounded-2xl p-4 flex flex-col gap-3"
      style={{
        background:  `linear-gradient(135deg, ${hab.color}10, rgba(26,29,43,0.9))`,
        border:      `1px solid ${hab.color}35`,
        boxShadow:   isNew ? `0 0 20px ${hab.color}40` : 'none',
        animation:   isNew ? 'scale-in 0.35s var(--spring-bounce) both' : 'none',
      }}
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <div
          className="w-12 h-12 rounded-2xl grid place-items-center text-[26px] shrink-0"
          style={{ background: `${hab.color}20`, border: `1px solid ${hab.color}40` }}
        >
          {hab.emoji}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-extrabold text-[15px]">{hab.name}</span>
            <span
              className="text-[11px] font-bold px-2 py-[2px] rounded-full"
              style={{ background: `${ql.color}20`, color: ql.color, border: `1px solid ${ql.color}30` }}
            >
              {ql.text}
            </span>
            {isNew && (
              <span
                className="text-[11px] font-bold px-2 py-[2px] rounded-full"
                style={{ background: 'rgba(var(--c-green-rgb),0.15)', color: 'var(--c-green)', border: '1px solid rgba(var(--c-green-rgb),0.3)' }}
              >
                НОВЫЙ
              </span>
            )}
          </div>
          <p className="m-0 mt-[2px] text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            {new Date(animal.acquired_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })}
          </p>
        </div>
      </div>

      {/* Genes */}
      <div className="grid grid-cols-2 gap-[6px]">
        {genes.map(([key, val]) => (
          <div
            key={key}
            className="flex items-center gap-2 px-3 py-[7px] rounded-xl"
            style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 7%, transparent)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)' }}
          >
            <div className="w-2 h-2 rounded-full shrink-0" style={{ background: geneColor(key, val) }} />
            <span className="text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
              {key === 'survival' ? 'Выж' : key === 'reproduction' ? 'Разм' : key === 'appearance' ? 'Вид' : 'Размер'}
            </span>
            <span className="ml-auto text-[11px] font-bold" style={{ color: geneColor(key, val) }}>
              {geneLabel(key, val)}
            </span>
          </div>
        ))}
      </div>

      {/* Income + Lifespan */}
      <div className="grid grid-cols-2 gap-[6px]">
        <div
          className="flex items-center justify-between px-3 py-[8px] rounded-xl"
          style={{ background: 'rgba(var(--c-green-rgb),0.08)', border: '1px solid rgba(var(--c-green-rgb),0.2)' }}
        >
          <span className="text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>💰</span>
          <span className="text-[12px] font-extrabold" style={{ color: 'var(--c-green)' }}>
            ₽{fmt(animal.income)}/мин
          </span>
        </div>
        {(() => {
          const life = lifeLeft(animal.dies_at);
          return life ? (
            <div
              className="flex items-center justify-between px-3 py-[8px] rounded-xl"
              style={{ background: `${life.color}12`, border: `1px solid ${life.color}35` }}
            >
              <span className="text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>⏳</span>
              <span className="text-[12px] font-extrabold" style={{ color: life.color }}>
                {life.label}
              </span>
            </div>
          ) : null;
        })()}
      </div>
    </div>
  );
}

// ─── Pack card ────────────────────────────────────────────────────────────────

function PackCard({
  isFree, price, onOpen, loading,
}: {
  isFree: boolean; price: number; onOpen: () => void; loading: boolean;
}) {
  return (
    <div
      className="relative overflow-hidden rounded-2xl p-5"
      style={{
        background:  isFree
          ? 'linear-gradient(135deg, rgba(var(--c-green-rgb),0.15) 0%, rgba(var(--c-teal-rgb),0.08) 100%)'
          : 'linear-gradient(135deg, rgba(var(--c-blue-rgb),0.15) 0%, rgba(var(--c-blue-rgb),0.06) 100%)',
        border: isFree ? '1px solid rgba(var(--c-green-rgb),0.35)' : '1px solid rgba(var(--c-blue-rgb),0.3)',
      }}
    >
      {/* Glow orb */}
      <div
        className="absolute top-0 right-0 w-24 h-24 rounded-full pointer-events-none"
        style={{
          background: isFree ? 'radial-gradient(rgba(var(--c-green-rgb),0.2),transparent 70%)' : 'radial-gradient(rgba(var(--c-blue-rgb),0.2),transparent 70%)',
          transform: 'translate(30%, -30%)',
        }}
      />

      <div className="relative flex items-center gap-4">
        <div
          className="w-14 h-14 rounded-2xl grid place-items-center text-[28px] shrink-0"
          style={{
            background: isFree ? 'rgba(var(--c-green-rgb),0.15)' : 'rgba(var(--c-blue-rgb),0.15)',
            border:     isFree ? '1px solid rgba(var(--c-green-rgb),0.3)' : '1px solid rgba(var(--c-blue-rgb),0.25)',
          }}
        >
          📦
        </div>
        <div className="flex-1 min-w-0">
          <p className="m-0 font-extrabold text-[15px]">
            {isFree ? 'Бесплатный пак' : 'Купить пак'}
          </p>
          <p className="m-0 mt-[2px] text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            {isFree ? 'Ежедневный · 1 животное со случайными генами' : `1 животное · цена растёт каждый раз`}
          </p>
        </div>
        <button
          onClick={onOpen}
          disabled={loading}
          className="px-4 py-[10px] rounded-xl border-none font-extrabold text-[13px] shrink-0"
          style={{
            background: isFree
              ? 'linear-gradient(135deg, var(--c-green), #30b34e)'
              : 'linear-gradient(135deg, var(--c-blue), #0066dd)',
            color:      '#fff',
            boxShadow:  isFree ? '0 4px 12px rgba(var(--c-green-rgb),0.35)' : '0 4px 12px rgba(var(--c-blue-rgb),0.3)',
            opacity:    loading ? 0.6 : 1,
          }}
        >
          {loading ? '...' : isFree ? 'Открыть' : `₽${fmt(price)}`}
        </button>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function PacksPage({ gs }: { gs: GameState }) {
  const [info, setInfo]       = useState<PackInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [opening, setOpening] = useState(false);
  const [newId, setNewId]     = useState<number | null>(null);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    apiGetPacksInfo()
      .then(setInfo)
      .catch(() => setError('Ошибка загрузки'))
      .finally(() => setLoading(false));
  }, []);

  const openPack = async () => {
    if (!info || opening) return;
    setOpening(true);
    setError(null);
    try {
      const res = await apiOpenPack();
      setNewId(res.animal.id);
      setInfo(prev => prev ? {
        ...prev,
        packs_today:    res.packs_today,
        free_available: false,
        next_price:     res.next_price,
        animals:        [res.animal, ...prev.animals],
      } : prev);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setOpening(false);
    }
  };

  return (
    <div className="px-[14px] pt-4 pb-4 flex flex-col gap-4">

      {/* Header */}
      <div>
        <p className="m-0 mb-[2px] font-extrabold text-[16px]">🎁 Паки с животными</p>
        <p className="m-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
          Каждый день — 1 бесплатный пак. Дополнительные за ₽.
        </p>
      </div>

      {/* Balance chip */}
      <div className="flex gap-2">
        <span
          className="px-3 py-[5px] rounded-[20px] text-[13px] font-bold"
          style={{ background: 'rgba(var(--c-green-rgb),0.12)', color: 'var(--c-green)', border: '1px solid rgba(var(--c-green-rgb),0.25)' }}
        >
          ₽ {fmt(gs.rub)}
        </span>
        {info && (
          <span
            className="px-3 py-[5px] rounded-[20px] text-[13px] font-bold"
            style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 10%, transparent)', color: 'var(--tg-theme-hint-color)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 18%, transparent)' }}
          >
            Открыто сегодня: {info.packs_today}
          </span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl px-4 py-3 text-sm" style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.25)', color: 'var(--c-red)' }}>
          {error}
        </div>
      )}

      {/* Pack cards */}
      {loading ? (
        <div className="flex justify-center py-8">
          <div className="spinner" />
        </div>
      ) : info ? (
        <>
          {info.free_available && (
            <PackCard isFree price={0} onOpen={openPack} loading={opening} />
          )}
          {!info.free_available && (
            <PackCard isFree={false} price={info.next_price} onOpen={openPack} loading={opening} />
          )}
          {/* Used today indicator */}
          {info.packs_today > 0 && (
            <div
              className="rounded-xl px-4 py-3 text-[12px] flex items-center gap-2"
              style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 7%, transparent)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 12%, transparent)', color: 'var(--tg-theme-hint-color)' }}
            >
              <span>📦</span>
              <span>Следующий пак: <strong style={{ color: 'var(--tg-theme-text-color)' }}>₽{fmt(info.next_price)}</strong></span>
            </div>
          )}
        </>
      ) : null}

      {/* Rules */}
      <div className="card">
        <p className="m-0 mb-2 font-bold text-[13px]">Как работают паки</p>
        <div className="flex flex-col gap-[6px]">
          {[
            ['🎁', '1 бесплатный пак каждый день'],
            ['📈', 'Каждый следующий пак в тот же день дороже'],
            ['🧬', '4 гена: выживаемость, размножение, внешность, размер'],
            ['🌍', '5 сред обитания: даёт бонус дохода в нужном вольере'],
            ['✨', 'Редкость: Слабый 40% · Обычный 40% · Высокий 20%'],
          ].map(([icon, text]) => (
            <div key={text as string} className="flex items-start gap-2">
              <span className="text-[14px] shrink-0 mt-[1px]">{icon}</span>
              <span className="text-[12px] leading-relaxed" style={{ color: 'var(--tg-theme-hint-color)' }}>{text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Animal collection */}
      {info && info.animals.length > 0 && (
        <div>
          <p className="m-0 mb-3 font-extrabold text-[14px]">
            Мои животные
            <span className="ml-2 text-[12px] font-normal" style={{ color: 'var(--tg-theme-hint-color)' }}>
              {info.animals.length} шт.
            </span>
          </p>
          <div className="flex flex-col gap-3">
            {info.animals.map(a => (
              <AnimalCard key={a.id} animal={a} isNew={a.id === newId} />
            ))}
          </div>
        </div>
      )}

      {info && info.animals.length === 0 && !loading && (
        <div className="text-center py-8">
          <div className="text-[48px] mb-3">📦</div>
          <p className="m-0 font-bold">Коллекция пуста</p>
          <p className="mt-1 mb-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Открой первый пак и получи животное!
          </p>
        </div>
      )}
    </div>
  );
}
