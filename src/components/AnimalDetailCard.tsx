import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { AnimalArt } from '@/components/AnimalArt';
import type { Animal, GeneTier } from '@/types';
import { fmt, formatCountdown, formatDateShort } from '@/utils/format';
import {
  GENE_META,
  HABITAT_INFO,
  SPECIES_RARITY_META,
  geneLabel,
  expeditionPower,
  type GeneKey,
} from '@/data/packs';

// A resident's passport. The animal is a living asset that ages and dies, so the life
// countdown is the hero here — everything else (genes, income, habitat) sits quietly
// around it. Every field shown already arrives on the client; nothing new is fetched.

const ORIGIN_META: Record<Animal['origin'], { emoji: string; label: string }> = {
  pack: { emoji: '📦', label: 'Из пака' },
  merchant: { emoji: '🛒', label: 'От торговца' },
  breeding: { emoji: '🧬', label: 'Рождён в неволе' },
  expedition: { emoji: '🧭', label: 'Из экспедиции' },
};

// Survival drives both income and lifespan, so its card is ordered first and its
// four genes are shown in the order the player feels them: how long, how rich, how
// fertile, how big.
const GENE_ORDER: { key: GeneKey; title: string; hint: string }[] = [
  { key: 'survival', title: 'Выживаемость', hint: 'Срок жизни и доход' },
  { key: 'appearance', title: 'Внешность', hint: 'Множитель дохода' },
  { key: 'size_trait', title: 'Размер', hint: 'Множитель дохода' },
  { key: 'reproduction', title: 'Размножение', hint: 'Шанс потомства' },
];

const TIER_FILL: Record<GeneTier, number> = { low: 1, medium: 2, high: 3 };

function GeneRow({ animal, gene, first }: { animal: Animal; gene: (typeof GENE_ORDER)[number]; first: boolean }) {
  const value = animal[gene.key] as GeneTier;
  const meta = GENE_META[gene.key][value];
  const filled = TIER_FILL[value];
  return (
    <div
      className="flex items-center gap-3 py-[9px]"
      style={first ? undefined : { borderTop: '1px solid var(--card-border)' }}
    >
      <div className="min-w-0 flex-1">
        <p className="m-0 text-[13px] font-bold">{gene.title}</p>
        <p className="m-0 mt-[1px] text-[10.5px]" style={{ color: 'var(--tg-theme-hint-color)' }}>{gene.hint}</p>
      </div>
      {/* Three segments make the low/medium/high ladder legible at a glance */}
      <div className="flex gap-[3px]" aria-hidden>
        {[0, 1, 2].map(i => (
          <span
            key={i}
            className="block w-[16px] h-[6px] rounded-full"
            style={{ background: i < filled ? meta.color : 'var(--surface-subtle-strong)' }}
          />
        ))}
      </div>
      <span className="text-[12px] font-extrabold text-right w-[104px] shrink-0" style={{ color: meta.color }}>
        {geneLabel(gene.key, value)}
      </span>
    </div>
  );
}

function InfoRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between py-[7px]">
      <span className="text-[12.5px]" style={{ color: 'var(--tg-theme-hint-color)' }}>{label}</span>
      <span className="text-[12.5px] font-bold" style={{ color: color ?? 'var(--tg-theme-text-color)' }}>{value}</span>
    </div>
  );
}

function formatMultiplier(value: number): string {
  return `×${value.toFixed(3).replace(/0+$/, '').replace(/\.$/, '').replace('.', ',')}`;
}

export function AnimalDetailCard({ animal, onClose, onRelease }: {
  animal: Animal;
  onClose: () => void;
  /** When provided, a "release" action is shown — a voluntary, irreversible cull.
   *  Should resolve after the animal is gone (parent closes the card); rejects surface here. */
  onRelease?: (animal: Animal) => Promise<void>;
}) {
  // Advance `now` once a second so the countdown ticks live.
  const [now, setNow] = useState(() => Date.now());
  const [showIncomeDetails, setShowIncomeDetails] = useState(false);
  const [confirmRelease, setConfirmRelease] = useState(false);
  const [releasing, setReleasing] = useState(false);
  const [releaseError, setReleaseError] = useState<string | null>(null);

  const handleRelease = async () => {
    if (!onRelease || releasing) return;
    setReleasing(true);
    setReleaseError(null);
    try {
      await onRelease(animal);
      // On success the parent unmounts this card; nothing else to do here.
    } catch (e) {
      setReleaseError((e as Error).message);
      setReleasing(false);
    }
  };
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);

  const rarity = SPECIES_RARITY_META[animal.species_rarity];
  const origin = ORIGIN_META[animal.origin];
  const habitat = HABITAT_INFO[animal.habitat];

  const born = new Date(animal.acquired_at).getTime();
  const dies = new Date(animal.dies_at).getTime();
  const secondsLeft = Math.max(0, Math.floor((dies - now) / 1000));
  const isDead = dies <= now;
  const totalSpan = Math.max(1, dies - born);
  const lived = Math.min(1, Math.max(0, (now - born) / totalSpan));
  const totalHoursLeft = secondsLeft / 3600;

  // The countdown shifts green → amber → red as death approaches; the last day pulses.
  const lifeColor = isDead
    ? 'var(--c-red)'
    : totalHoursLeft < 24 ? 'var(--c-red)'
    : totalHoursLeft < 48 ? 'var(--c-amber)'
    : 'var(--c-green)';
  const urgent = !isDead && totalHoursLeft < 24;

  const power = expeditionPower(animal);
  const isFabled = animal.species_rarity === 'legendary' || animal.species_rarity === 'mythic';
  const incomeBreakdown = animal.income_breakdown;

  return createPortal(
    <div
      className="modal-backdrop fixed inset-0 z-[300] flex items-end justify-center"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Карточка животного: ${animal.species_name}`}
    >
      <div
        className="sheet-panel w-full max-w-[480px] rounded-t-3xl p-4 flex flex-col gap-3 max-h-[88vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* ── Hero: species identity ── */}
        <div className="flex items-center gap-3">
          <div
            className="shrink-0 w-[76px] h-[76px] rounded-2xl flex items-center justify-center overflow-hidden"
            style={{
              background: `linear-gradient(150deg, ${rarity.color}30, var(--surface-subtle))`,
              border: `1.5px solid ${rarity.color}70`,
              boxShadow: isFabled ? `0 0 22px ${rarity.color}44` : 'none',
            }}
          >
            <AnimalArt animal={animal} size={72} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="m-0 text-[18px] font-extrabold leading-tight truncate">{animal.name}</p>
            <p className="m-0 text-[12px] font-semibold" style={{ color: 'var(--tg-theme-hint-color)' }}>{animal.species_name}</p>
            <div className="mt-[4px] flex items-center gap-[6px] flex-wrap">
              <span
                className="px-[8px] py-[2px] rounded-full text-[10.5px] font-extrabold"
                style={{ background: `${rarity.color}22`, color: rarity.color, border: `1px solid ${rarity.color}66` }}
              >
                {rarity.label}
              </span>
              <span className="text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                {origin.emoji} {origin.label}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Закрыть"
            className="tap-target self-start -mr-1 -mt-1 border-none bg-transparent text-[18px] cursor-pointer"
            style={{ color: 'var(--tg-theme-hint-color)' }}
          >
            ✕
          </button>
        </div>

        {/* ── Signature: life countdown ── */}
        <div
          className="rounded-2xl px-4 py-[14px]"
          style={{
            background: `color-mix(in srgb, ${lifeColor} 9%, var(--surface-subtle))`,
            border: `1px solid color-mix(in srgb, ${lifeColor} 34%, transparent)`,
          }}
        >
          <p className="m-0 text-[10px] font-extrabold uppercase tracking-[1.5px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            {isDead ? 'Питомец' : 'Осталось жить'}
          </p>
          <p
            className="font-display m-0 mt-[3px] text-[30px] leading-none tabular-nums"
            style={{ color: lifeColor, animation: urgent ? 'glow-pulse 1.6s ease-in-out infinite' : undefined }}
          >
            {isDead ? 'Умер' : formatCountdown(secondsLeft)}
          </p>
          {/* Age progress from acquired_at to dies_at */}
          <div className="mt-[11px] h-[7px] w-full rounded-full overflow-hidden" style={{ background: 'var(--surface-subtle-strong)' }}>
            <div
              className="h-full rounded-full"
              style={{ width: `${(lived * 100).toFixed(1)}%`, background: lifeColor, transition: 'width 0.4s var(--spring-smooth)' }}
            />
          </div>
          <div className="mt-[7px] flex justify-between text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            <span>Заведён {formatDateShort(animal.acquired_at)}</span>
            <span>Умрёт {formatDateShort(animal.dies_at)}</span>
          </div>
        </div>

        {/* ── Income ── */}
        <div className="rounded-2xl px-4 py-3" style={{ background: 'var(--surface-subtle)', border: '1px solid var(--card-border)' }}>
          <button
            type="button"
            className="flex w-full items-center justify-between gap-3 border-none bg-transparent p-0 text-left"
            style={{ cursor: incomeBreakdown ? 'pointer' : 'default' }}
            onClick={() => incomeBreakdown && setShowIncomeDetails(value => !value)}
            aria-expanded={incomeBreakdown ? showIncomeDetails : undefined}
            aria-controls={incomeBreakdown ? 'animal-income-breakdown' : undefined}
          >
            <span className="text-[12px] font-bold" style={{ color: 'var(--tg-theme-hint-color)' }}>Доход</span>
            <span className="flex items-center gap-2">
              <span className="font-display text-[22px] tabular-nums" style={{ color: 'var(--c-green)' }}>
                ₽{fmt(animal.income)}<span className="text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}> /мин</span>
              </span>
              {incomeBreakdown && (
                <span className="text-[16px] leading-none" style={{ color: 'var(--tg-theme-hint-color)' }} aria-hidden>
                  {showIncomeDetails ? '⌃' : '⌄'}
                </span>
              )}
            </span>
          </button>
          {(animal.is_sick || animal.habitat_bonus) && (
            <div className="mt-[6px] flex flex-wrap gap-[6px]">
              {animal.is_sick && (
                <span className="px-[8px] py-[2px] rounded-full text-[10.5px] font-bold"
                      style={{ background: 'rgba(var(--c-red-rgb),0.14)', color: 'var(--c-red)' }}>
                  🤒 Болен — доход ×0.5
                </span>
              )}
              {animal.habitat_bonus && (
                <span className="px-[8px] py-[2px] rounded-full text-[10.5px] font-bold"
                      style={{ background: 'rgba(var(--c-green-rgb),0.14)', color: 'var(--c-green)' }}>
                  🌱 Бонус родной среды
                </span>
              )}
            </div>
          )}
          {incomeBreakdown && showIncomeDetails && (
            <div id="animal-income-breakdown" className="mt-3 pt-3 border-t" style={{ borderColor: 'var(--card-border)' }}>
              <p className="m-0 text-[10px] font-extrabold uppercase tracking-[1.2px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                Состав дохода
              </p>
              <div className="mt-2 flex flex-col gap-0">
                <div className="flex items-center justify-between gap-3 text-[11px]">
                  <span style={{ color: 'var(--tg-theme-hint-color)' }}>База вида · {rarity.label}</span>
                  <span className="font-bold tabular-nums">₽{fmt(incomeBreakdown.base)}</span>
                </div>
                {incomeBreakdown.factors.map(factor => (
                  <div key={factor.key} className="flex items-center justify-between gap-3 text-[11px]">
                    <span className="min-w-0 truncate" style={{ color: 'var(--tg-theme-hint-color)' }}>
                      {factor.label}{['habitat', 'sickness', 'species_item'].includes(factor.key) && factor.value ? ` · ${factor.value}` : ''}
                    </span>
                    <span className="shrink-0 font-bold tabular-nums" style={{ color: factor.multiplier === 1 ? 'var(--tg-theme-hint-color)' : 'var(--c-green)' }}>
                      {formatMultiplier(factor.multiplier)}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-2 pt-2 flex items-center justify-between gap-3 border-t" style={{ borderColor: 'var(--card-border)' }}>
                <span className="text-[11px] font-extrabold">Итого</span>
                <span className="text-[13px] font-extrabold tabular-nums" style={{ color: 'var(--c-green)' }}>₽{fmt(incomeBreakdown.total)} /мин</span>
              </div>
              <p className="m-0 mt-2 text-[10px] leading-snug" style={{ color: 'var(--tg-theme-hint-color)' }}>
                Общие бонусы зоопарка и бонус разнообразия считаются отдельно в общей скорости дохода.
              </p>
            </div>
          )}
        </div>

        {/* ── Genes ── */}
        <div className="rounded-2xl px-4 py-1" style={{ background: 'var(--surface-subtle)', border: '1px solid var(--card-border)' }}>
          <p className="m-0 pt-[10px] text-[10px] font-extrabold uppercase tracking-[1.5px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Гены
          </p>
          <div className="pb-1">
            {GENE_ORDER.map((gene, i) => <GeneRow key={gene.key} animal={animal} gene={gene} first={i === 0} />)}
          </div>
        </div>

        {/* ── Status facts ── */}
        <div className="rounded-2xl px-4 py-1" style={{ background: 'var(--surface-subtle)', border: '1px solid var(--card-border)' }}>
          <InfoRow label="Среда обитания" value={`${habitat.emoji} ${habitat.name}`} />
          <div className="border-t" style={{ borderColor: 'var(--card-border)' }} />
          <InfoRow
            label="Здоровье"
            value={animal.is_sick ? 'Болен' : 'Здоров'}
            color={animal.is_sick ? 'var(--c-red)' : 'var(--c-green)'}
          />
          <div className="border-t" style={{ borderColor: 'var(--card-border)' }} />
          <InfoRow
            label="Размножение"
            value={animal.can_breed ? 'Готов' : 'Недоступно'}
            color={animal.can_breed ? 'var(--c-green)' : 'var(--tg-theme-hint-color)'}
          />
          <div className="border-t" style={{ borderColor: 'var(--card-border)' }} />
          <InfoRow label="Сила в экспедициях" value={`⚔️ ${power}`} color="var(--c-gold)" />
        </div>

        {/* ── Release ── a voluntary, irreversible cull for population control */}
        {onRelease && (
          <div>
            {releaseError && (
              <p className="m-0 mb-2 text-[11.5px]" style={{ color: 'var(--c-red)' }}>{releaseError}</p>
            )}
            {confirmRelease ? (
              <div className="flex items-center gap-2">
                <span className="text-[11.5px] flex-1 leading-snug" style={{ color: 'var(--tg-theme-hint-color)' }}>
                  Отпустить навсегда? Животное исчезнет и перестанет приносить доход.
                </span>
                <button
                  onClick={() => void handleRelease()}
                  disabled={releasing}
                  className="shrink-0 px-3 py-[8px] rounded-xl border-none font-bold text-[12px] cursor-pointer disabled:opacity-50"
                  style={{ background: 'var(--c-red)', color: '#fff' }}
                >
                  {releasing ? '...' : 'Отпустить'}
                </button>
                <button
                  onClick={() => setConfirmRelease(false)}
                  disabled={releasing}
                  className="shrink-0 px-3 py-[8px] rounded-xl border-none font-bold text-[12px] cursor-pointer"
                  style={{ background: 'var(--surface-subtle-strong)', color: 'var(--tg-theme-hint-color)' }}
                >
                  Отмена
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmRelease(true)}
                className="w-full py-[11px] rounded-xl font-bold text-[13px] cursor-pointer"
                style={{ background: 'rgba(var(--c-red-rgb),0.1)', color: 'var(--c-red)', border: '1px solid rgba(var(--c-red-rgb),0.25)' }}
              >
                Отпустить животное
              </button>
            )}
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
