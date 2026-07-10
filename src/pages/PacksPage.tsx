import { useEffect, useRef, useState } from 'react';
import { fmt } from '@/utils/format';
import type { Animal, GameState, PackInfo } from '@/types';
import { apiGetPacksInfo, apiOpenPack } from '@/api';
import { GENE_META, lifeLeft } from '@/data/packs';

// ─── Pack tiers ───────────────────────────────────────────────────────────────

type TierKey = 'rare' | 'epic' | 'legendary' | 'mythic';

const TIERS: Record<TierKey, {
  name: string;
  color: string;
  glow: string;
  bg: string;
  border: string;
  image: string;
  openVideo: string;
  description: string;
}> = {
  rare: {
    name: 'Редкий',
    color: '#4A9EDD',
    glow: 'rgba(74,158,221,0.55)',
    bg: 'radial-gradient(ellipse at 50% 34%, rgba(74,158,221,0.20) 0%, rgba(10,15,30,0.98) 72%)',
    border: 'rgba(74,158,221,0.45)',
    image: '/packs/pack-rare.png',
    openVideo: '/packs/zoopark-rare.mp4',
    description: 'Первый пак дня — бесплатный',
  },
  epic: {
    name: 'Эпический',
    color: '#A855F7',
    glow: 'rgba(168,85,247,0.55)',
    bg: 'radial-gradient(ellipse at 50% 34%, rgba(168,85,247,0.20) 0%, rgba(12,8,30,0.98) 72%)',
    border: 'rgba(168,85,247,0.45)',
    image: '/packs/pack-epic.png',
    openVideo: '/packs/zoopark-epic.mp4',
    description: 'Второй пак дня. Шансы генов те же, цена выше',
  },
  legendary: {
    name: 'Легендарный',
    color: '#F59E0B',
    glow: 'rgba(245,158,11,0.55)',
    bg: 'radial-gradient(ellipse at 50% 34%, rgba(245,158,11,0.20) 0%, rgba(20,14,4,0.98) 72%)',
    border: 'rgba(245,158,11,0.45)',
    image: '/packs/pack-legendary.png',
    openVideo: '/packs/zoopark-legendary.mp4',
    description: 'Третий пак дня. Шансы генов те же, цена выше',
  },
  mythic: {
    name: 'Мифический',
    color: '#EF4444',
    glow: 'rgba(239,68,68,0.55)',
    bg: 'radial-gradient(ellipse at 50% 34%, rgba(239,68,68,0.20) 0%, rgba(20,6,6,0.98) 72%)',
    border: 'rgba(239,68,68,0.45)',
    image: '/packs/pack-mythic.png',
    openVideo: '/packs/zoopark-mythic.mp4',
    description: 'Четвёртый и далее. Шансы генов те же, цена выше',
  },
};

const TIER_ORDER: TierKey[] = ['rare', 'epic', 'legendary', 'mythic'];

/** The server decides which tier is next; the client used to recompute it and could drift. */
function getCurrentTierKey(info: PackInfo): TierKey {
  return info.tier;
}

// ─── Habitat & quality helpers ────────────────────────────────────────────────

const HABITAT_INFO: Record<string, { emoji: string; name: string; color: string }> = {
  desert:     { emoji: '🐪', name: 'Пустыня',   color: 'var(--c-gold)' },
  mountains:  { emoji: '🦅', name: 'Горы',       color: 'var(--tg-theme-hint-color)' },
  forest:     { emoji: '🐆', name: 'Лес',        color: 'var(--c-green)' },
  fields:     { emoji: '🐴', name: 'Поля',        color: 'var(--c-teal)' },
  antarctica: { emoji: '🐧', name: 'Антарктида', color: 'var(--c-cyan)' },
};

function qualityScore(a: Animal): number {
  const w: Record<string, number> = { low: 0, medium: 1, high: 2 };
  return w[a.survival] + w[a.reproduction] + w[a.appearance] + w[a.size_trait];
}

type QualityTier = { text: string; glowColor: string; glowShadow: string; accentColor: string };

function qualityTier(score: number): QualityTier {
  if (score >= 7) return {
    text: 'Идеальный',
    accentColor: '#FBBF24',
    glowColor: 'rgba(251,191,36,0.55)',
    glowShadow: '0 0 36px rgba(251,191,36,0.45), 0 0 72px rgba(251,191,36,0.18), 0 12px 32px rgba(0,0,0,0.75)',
  };
  if (score >= 5) return {
    text: 'Отличный',
    accentColor: '#60A5FA',
    glowColor: 'rgba(96,165,250,0.45)',
    glowShadow: '0 0 28px rgba(96,165,250,0.4), 0 0 56px rgba(96,165,250,0.14), 0 12px 32px rgba(0,0,0,0.75)',
  };
  if (score >= 3) return {
    text: 'Хороший',
    accentColor: '#34D399',
    glowColor: 'rgba(52,211,153,0.4)',
    glowShadow: '0 0 22px rgba(52,211,153,0.35), 0 0 44px rgba(52,211,153,0.1), 0 12px 32px rgba(0,0,0,0.75)',
  };
  if (score >= 1) return {
    text: 'Посредственный',
    accentColor: '#94A3B8',
    glowColor: 'rgba(148,163,184,0.25)',
    glowShadow: '0 0 16px rgba(148,163,184,0.2), 0 12px 28px rgba(0,0,0,0.7)',
  };
  return {
    text: 'Слабый',
    accentColor: '#6B7280',
    glowColor: 'rgba(107,114,128,0.15)',
    glowShadow: '0 8px 24px rgba(0,0,0,0.65)',
  };
}

const GENE_DOTS: Record<string, number> = { low: 1, medium: 2, high: 3 };
const GENE_DOT_COLOR: Record<string, string> = {
  low: 'rgba(251,146,60,0.7)',
  medium: 'rgba(148,163,184,0.55)',
  high: 'rgba(255,255,255,0.85)',
};
const GENE_LABELS: Record<string, string> = {
  survival: 'Выживаемость',
  reproduction: 'Размножение',
  appearance: 'Внешность',
  size_trait: 'Размер',
};

function GeneDots({ tier }: { tier: string }) {
  const filled = GENE_DOTS[tier] ?? 1;
  const color  = GENE_DOT_COLOR[tier] ?? 'rgba(148,163,184,0.55)';
  return (
    <span className="flex gap-[3px] items-center">
      {[1, 2, 3].map(i => (
        <span
          key={i}
          className="inline-block rounded-full"
          style={{
            width: 6, height: 6,
            background: i <= filled ? color : 'rgba(255,255,255,0.1)',
          }}
        />
      ))}
    </span>
  );
}

// ─── Animal result card ───────────────────────────────────────────────────────

function AnimalCard({ animal }: { animal: Animal }) {
  const hab   = HABITAT_INFO[animal.habitat];
  const score = qualityScore(animal);
  const qt    = qualityTier(score);
  const life  = lifeLeft(animal.dies_at);
  const genes: [string, string][] = [
    ['survival',     animal.survival],
    ['reproduction', animal.reproduction],
    ['appearance',   animal.appearance],
    ['size_trait',   animal.size_trait],
  ];

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{
        background: 'rgba(13,15,26,0.98)',
        border:     `1px solid ${qt.glowColor}`,
        boxShadow:  qt.glowShadow,
        animation:  'scale-in 0.4s var(--spring-bounce) both',
      }}
    >
      {/* Header */}
      <div className="px-4 pt-4 pb-3 flex items-center gap-3">
        <div
          className="w-[52px] h-[52px] rounded-2xl grid place-items-center text-[26px] shrink-0"
          style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
        >
          {animal.species_emoji}
        </div>

        <div className="flex-1 min-w-0">
          <p className="m-0 font-extrabold text-[15px] leading-tight truncate">
            {animal.species_name}
          </p>
          <p className="m-0 mt-[3px] text-[11px]" style={{ color: 'rgba(148,163,184,0.7)' }}>
            {hab.emoji} {hab.name}
          </p>
        </div>

        <div className="flex flex-col items-end gap-[4px] shrink-0">
          <span
            className="text-[11px] font-bold px-[9px] py-[3px] rounded-full"
            style={{
              background: `${qt.accentColor}18`,
              color: qt.accentColor,
              border: `1px solid ${qt.accentColor}40`,
            }}
          >
            {qt.text}
          </span>
          <span className="text-[13px] font-extrabold" style={{ color: 'rgba(255,255,255,0.9)' }}>
            ₽{fmt(animal.income)}
            <span className="text-[10px] font-normal" style={{ color: 'rgba(148,163,184,0.6)' }}> /мин</span>
          </span>
        </div>
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: 'rgba(255,255,255,0.05)', margin: '0 16px' }} />

      {/* Genes */}
      <div className="px-4 py-3 flex flex-col gap-[7px]">
        {genes.map(([key, val]) => {
          const meta = GENE_META[key as keyof typeof GENE_META]?.[val as 'low' | 'medium' | 'high'];
          return (
            <div key={key} className="flex items-center justify-between">
              <span className="text-[11px]" style={{ color: 'rgba(148,163,184,0.55)' }}>
                {GENE_LABELS[key]}
              </span>
              <div className="flex items-center gap-2">
                <GeneDots tier={val} />
                <span className="text-[11px] font-semibold w-[88px] text-right" style={{ color: 'rgba(255,255,255,0.75)' }}>
                  {meta?.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Lifetime */}
      {life && (
        <>
          <div style={{ height: 1, background: 'rgba(255,255,255,0.05)', margin: '0 16px' }} />
          <div className="px-4 py-3 flex items-center justify-between">
            <span className="text-[11px]" style={{ color: 'rgba(148,163,184,0.55)' }}>Срок жизни</span>
            <span className="text-[12px] font-bold" style={{ color: life.color }}>{life.label}</span>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Pack art (levitating still, replaces the looped video) ──────────────────

function PackArt({ tier }: { tier: (typeof TIERS)[TierKey] }) {
  return (
    <div className="absolute inset-0 overflow-hidden">
      {/* Ambient tier glow — our own light, no video glare */}
      <div
        className="absolute inset-0"
        aria-hidden
        style={{ background: `radial-gradient(ellipse 62% 44% at 50% 40%, ${tier.glow} 0%, transparent 66%)` }}
      />
      {/* Levitating pack with a grounding shadow that breathes in counter-phase */}
      <div className="absolute inset-0 grid place-items-center">
        <div className="relative" style={{ width: '66%', aspectRatio: '210 / 345' }}>
          <div
            className="pack-shadow absolute left-1/2"
            aria-hidden
            style={{
              bottom: '-8%',
              width: '74%',
              height: '11%',
              background: `radial-gradient(ellipse, ${tier.glow} 0%, transparent 72%)`,
              filter: 'blur(3px)',
            }}
          />
          <img
            src={tier.image}
            alt=""
            draggable={false}
            className="pack-float w-full h-full object-contain select-none"
            style={{ filter: 'drop-shadow(0 12px 20px rgba(0,0,0,0.55))' }}
          />
        </div>
      </div>
    </div>
  );
}

// ─── Pack tile (idle card in grid) ───────────────────────────────────────────

function PackTile({
  tier, isCurrent, isFree, onClick,
}: {
  tier: (typeof TIERS)[TierKey];
  isCurrent: boolean;
  isFree: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="relative overflow-hidden rounded-2xl border-none p-0"
      style={{
        aspectRatio: '3/4',
        background: tier.bg,
        border: `1.5px solid ${isCurrent ? tier.color : tier.border}`,
        boxShadow: isCurrent
          ? `0 0 24px ${tier.glow}, 0 6px 20px rgba(0,0,0,0.5)`
          : `0 4px 16px rgba(0,0,0,0.4)`,
        cursor: 'pointer',
        transition: 'transform 0.15s ease, box-shadow 0.15s ease',
      }}
    >
      <PackArt tier={tier} />

      {/* Tier name badge */}
      <div
        className="absolute bottom-[10px] left-0 right-0 flex justify-center"
        style={{ pointerEvents: 'none' }}
      >
        <span
          className="px-3 py-[4px] rounded-full text-[11px] font-extrabold tracking-wide"
          style={{
            background: `${tier.color}28`,
            color: tier.color,
            border: `1px solid ${tier.color}55`,
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
          }}
        >
          {tier.name}
        </span>
      </div>

      {/* Free badge */}
      {isFree && (
        <div className="absolute top-[8px] right-[8px]">
          <span
            className="px-2 py-[3px] rounded-full text-[10px] font-extrabold"
            style={{
              background: 'rgba(34,197,94,0.25)',
              color: 'var(--c-green)',
              border: '1px solid rgba(34,197,94,0.45)',
              backdropFilter: 'blur(6px)',
              WebkitBackdropFilter: 'blur(6px)',
            }}
          >
            FREE
          </span>
        </div>
      )}

      {/* Active indicator ring */}
      {isCurrent && (
        <div
          className="absolute inset-0 rounded-2xl"
          style={{
            border: `2px solid ${tier.color}`,
            pointerEvents: 'none',
          }}
        />
      )}
    </button>
  );
}

// ─── Pack modal ───────────────────────────────────────────────────────────────

type ModalOpenState = 'idle' | 'opening';

function PackModal({
  tierKey, info, gs,
  onClose, onSuccess,
}: {
  tierKey: TierKey;
  info: PackInfo;
  gs: GameState;
  onClose: () => void;
  onSuccess: (updatedInfo: PackInfo, animal: Animal) => void;
}) {
  const tier      = TIERS[tierKey];
  const isCurrent = tierKey === getCurrentTierKey(info);
  const isFree    = tierKey === 'rare' && info.free_available;
  const canOpen   = isCurrent;

  const [openState, setOpenState] = useState<ModalOpenState>('idle');
  const [newAnimal, setNewAnimal] = useState<Animal | null>(null);
  const [apiDone, setApiDone]     = useState(false);
  const [animDone, setAnimDone]   = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Imperatively attach 'ended' listener
  useEffect(() => {
    if (openState !== 'opening') return;
    const video = videoRef.current;
    if (!video) return;

    let fired = false;
    const trigger = () => {
      if (fired) return;
      fired = true;
      setAnimDone(true);
    };

    if (video.ended) { trigger(); return; }
    video.addEventListener('ended', trigger, { once: true });

    let fallback: ReturnType<typeof setTimeout>;
    const scheduleFallback = () => {
      const remaining = (video.duration - video.currentTime) * 1000;
      fallback = setTimeout(trigger, Math.max(remaining, 0) + 400);
    };
    if (isFinite(video.duration) && video.duration > 0) {
      scheduleFallback();
    } else {
      video.addEventListener('loadedmetadata', scheduleFallback, { once: true });
    }
    return () => {
      video.removeEventListener('ended', trigger);
      clearTimeout(fallback);
    };
  }, [openState]);

  const handleOpen = async () => {
    if (openState !== 'idle') return;
    setOpenState('opening');
    setApiDone(false);
    setAnimDone(false);
    setError(null);
    try {
      const res = await apiOpenPack();
      const updatedInfo: PackInfo = {
        ...info,
        packs_today: res.packs_today,
        free_available: false,
        tier: res.next_tier,
        next_price: res.next_price,
      };
      setNewAnimal(res.animal);
      setApiDone(true);
      onSuccess(updatedInfo, res.animal);
    } catch (e) {
      setError((e as Error).message);
      setOpenState('idle');
    }
  };

  // Reveal is derived: the card flips once both the animation and the request are done.
  const isRevealed = openState === 'opening' && apiDone && animDone;
  const isOpening  = openState === 'opening' && !isRevealed;

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-end justify-center"
      style={{ background: 'rgba(0,0,0,0.72)', backdropFilter: 'blur(6px)', WebkitBackdropFilter: 'blur(6px)' }}
      onClick={isOpening ? undefined : onClose}
    >
      {/* Sheet */}
      <div
        className="w-full rounded-t-3xl flex flex-col overflow-hidden"
        style={{
          maxHeight: '92vh',
          background: 'linear-gradient(180deg, rgba(12,14,26,0.99) 0%, rgba(8,10,20,1) 100%)',
          border: `1px solid ${tier.border}`,
          borderBottom: 'none',
          boxShadow: `0 -8px 40px ${tier.glow}`,
          animation: 'slide-up 0.3s var(--spring-bounce) both',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Handle */}
        <div className="flex justify-center pt-3 pb-1 shrink-0">
          <div className="w-10 h-1 rounded-full" style={{ background: `${tier.color}40` }} />
        </div>

        {/* Scrollable content */}
        <div className="overflow-y-auto flex flex-col gap-4 px-4 pt-2 pb-6">

          {/* Video */}
          {!isRevealed && (
            <div
              className="relative mx-auto overflow-hidden rounded-3xl shrink-0"
              style={{
                width: '100%',
                maxWidth: 280,
                aspectRatio: '3/4',
                background: tier.bg,
                border: `1.5px solid ${tier.border}`,
                boxShadow: `0 0 40px ${tier.glow}, 0 10px 30px rgba(0,0,0,0.6)`,
              }}
            >
              {isOpening ? (
                <video
                  ref={videoRef}
                  key="opening"
                  src={tier.openVideo}
                  autoPlay
                  muted
                  playsInline
                  className="w-full h-full object-cover"
                  style={{ display: 'block' }}
                />
              ) : (
                <PackArt tier={tier} />
              )}
              <div className="absolute bottom-3 left-0 right-0 flex justify-center" style={{ pointerEvents: 'none' }}>
                <span
                  className="px-4 py-[5px] rounded-full text-[12px] font-extrabold tracking-wide"
                  style={{
                    background: `${tier.color}25`,
                    color: tier.color,
                    border: `1px solid ${tier.color}50`,
                    backdropFilter: 'blur(8px)',
                    WebkitBackdropFilter: 'blur(8px)',
                  }}
                >
                  {tier.name}
                </span>
              </div>
            </div>
          )}

          {/* Revealed animal */}
          {isRevealed && newAnimal && (
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-center">
                <span
                  className="px-4 py-[6px] rounded-full text-[13px] font-extrabold tracking-wide"
                  style={{
                    background: `${tier.color}20`,
                    color: tier.color,
                    border: `1px solid ${tier.color}40`,
                  }}
                >
                  ✨ {tier.name} пак
                </span>
              </div>
              <AnimalCard animal={newAnimal} />
            </div>
          )}

          {/* Info block */}
          {!isRevealed && (
            <div className="flex flex-col gap-2">
              <p className="m-0 font-extrabold text-[16px]" style={{ color: tier.color }}>{tier.name} пак</p>
              <p className="m-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                {tier.description}
              </p>

              {/* Price / availability */}
              <div
                className="flex items-center justify-between px-3 py-[10px] rounded-xl mt-1"
                style={{ background: `${tier.color}10`, border: `1px solid ${tier.color}25` }}
              >
                <span className="text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>Цена</span>
                <span className="font-extrabold text-[14px]" style={{ color: isFree ? 'var(--c-green)' : tier.color }}>
                  {/* `next_price` belongs to the tier the server says is next. Showing it on
                      any other tile promised a price that tile does not have. */}
                  {isFree ? '🎁 Бесплатно' : isCurrent ? `₽${fmt(info.next_price)}` : '—'}
                </span>
              </div>

              {/* Balance */}
              <div className="flex items-center justify-between px-3 py-[8px] rounded-xl">
                <span className="text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>Баланс</span>
                <span className="text-[13px] font-bold" style={{ color: 'var(--c-green)' }}>₽{fmt(gs.rub)}</span>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div
              className="rounded-xl px-4 py-3 text-[13px]"
              style={{ background: 'rgba(var(--c-red-rgb),0.1)', border: '1px solid rgba(var(--c-red-rgb),0.25)', color: 'var(--c-red)' }}
            >
              {error}
            </div>
          )}

          {/* Actions */}
          {!isRevealed && (
            <div className="flex flex-col gap-2">
              {canOpen ? (
                <button
                  onClick={handleOpen}
                  disabled={isOpening}
                  className="w-full py-[14px] rounded-2xl font-extrabold text-[16px] border-none"
                  style={{
                    background: isOpening
                      ? `${tier.color}30`
                      : `linear-gradient(135deg, ${tier.color}, ${tier.color}cc)`,
                    color: isOpening ? tier.color : '#fff',
                    boxShadow: isOpening ? 'none' : `0 6px 20px ${tier.glow}`,
                    transition: 'all 0.2s ease',
                  }}
                >
                  {isOpening
                    ? '⏳ Открываем...'
                    : isFree
                    ? '🎁 Открыть бесплатно'
                    : `🔓 Открыть · ₽${fmt(info.next_price)}`}
                </button>
              ) : (
                <div
                  className="w-full py-[13px] rounded-2xl text-center text-[14px] font-bold"
                  style={{
                    background: 'rgba(255,255,255,0.04)',
                    color: 'var(--tg-theme-hint-color)',
                    border: '1px solid rgba(255,255,255,0.08)',
                  }}
                >
                  {TIER_ORDER.indexOf(tierKey) < TIER_ORDER.indexOf(getCurrentTierKey(info))
                    ? '✅ Уже открыт сегодня'
                    : `🔒 Откроется после ${TIER_ORDER.indexOf(tierKey)} пак${TIER_ORDER.indexOf(tierKey) === 1 ? 'а' : 'ов'}`}
                </div>
              )}
              <button
                onClick={onClose}
                className="w-full py-[12px] rounded-2xl font-bold text-[14px] border-none"
                style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--tg-theme-hint-color)' }}
              >
                Закрыть
              </button>
            </div>
          )}

          {isRevealed && (
            <button
              onClick={onClose}
              className="w-full py-[14px] rounded-2xl font-extrabold text-[15px] border-none"
              style={{
                background: `${tier.color}18`,
                color: tier.color,
                border: `1px solid ${tier.color}35`,
              }}
            >
              Готово
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Daily pack banner ────────────────────────────────────────────────────────

function DailyPackBanner({ available, onClick }: { available: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full rounded-2xl border-none flex items-center gap-3 px-4 py-[14px]"
      style={{
        background: available
          ? 'linear-gradient(135deg, rgba(34,197,94,0.15) 0%, rgba(16,185,129,0.08) 100%)'
          : 'rgba(255,255,255,0.04)',
        border: available
          ? '1px solid rgba(34,197,94,0.35)'
          : '1px solid rgba(255,255,255,0.08)',
        boxShadow: available ? '0 4px 20px rgba(34,197,94,0.15)' : 'none',
        cursor: 'pointer',
        textAlign: 'left',
      }}
    >
      <div
        className="w-12 h-12 rounded-2xl grid place-items-center text-[24px] shrink-0"
        style={{
          background: available ? 'rgba(34,197,94,0.15)' : 'rgba(255,255,255,0.05)',
          border: available ? '1px solid rgba(34,197,94,0.3)' : '1px solid rgba(255,255,255,0.08)',
        }}
      >
        🎁
      </div>
      <div className="flex-1 min-w-0">
        <p className="m-0 font-extrabold text-[15px]">Ежедневный пак</p>
        <p className="m-0 mt-[2px] text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
          {available ? 'Бесплатный пак доступен сегодня' : 'Уже получен сегодня'}
        </p>
      </div>
      <span
        className="text-[12px] font-bold px-3 py-[5px] rounded-full shrink-0"
        style={{
          background: available ? 'rgba(34,197,94,0.2)' : 'rgba(255,255,255,0.06)',
          color: available ? 'var(--c-green)' : 'var(--tg-theme-hint-color)',
          border: available ? '1px solid rgba(34,197,94,0.35)' : '1px solid rgba(255,255,255,0.1)',
        }}
      >
        {available ? 'FREE' : '✓'}
      </span>
    </button>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function PacksPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [info, setInfo]       = useState<PackInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [modalTier, setModalTier] = useState<TierKey | null>(null);

  useEffect(() => {
    apiGetPacksInfo()
      .then(setInfo)
      .catch(() => setLoadError('Ошибка загрузки'))
      .finally(() => setLoading(false));
  }, []);

  const handleSuccess = (updatedInfo: PackInfo) => {
    setInfo(updatedInfo);
    onRefresh();
  };

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="spinner" />
      </div>
    );
  }

  if (loadError || !info) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="text-[14px]" style={{ color: 'var(--c-red)' }}>{loadError ?? 'Ошибка загрузки'}</p>
      </div>
    );
  }

  const currentTierKey = getCurrentTierKey(info);

  return (
    <div className="px-[14px] pt-4 pb-6 flex flex-col gap-4">

      {/* Header */}
      <div>
        <p className="m-0 font-extrabold text-[17px]">🎁 Паки с животными</p>
        <p className="m-0 mt-[2px] text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
          Открывай паки и получай животных для зоопарка
        </p>
      </div>

      {/* Daily pack */}
      <DailyPackBanner
        available={info.free_available}
        onClick={() => setModalTier('rare')}
      />

      {/* 2×2 tier grid */}
      <div className="grid grid-cols-2 gap-3">
        {TIER_ORDER.map(tk => (
          <PackTile
            key={tk}
            tier={TIERS[tk]}
            isCurrent={tk === currentTierKey}
            isFree={tk === 'rare' && info.free_available}
            onClick={() => setModalTier(tk)}
          />
        ))}
      </div>

      {/* Pack modal */}
      {modalTier && (
        <PackModal
          tierKey={modalTier}
          info={info}
          gs={gs}
          onClose={() => setModalTier(null)}
          onSuccess={handleSuccess}
        />
      )}
    </div>
  );
}
