import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { createPortal } from 'react-dom';
import { fmt } from '@/utils/format';
import type { Animal, GameState, GeneTier, PackInfo, PackOpenResult } from '@/types';
import { apiGetPacksInfo, apiOpenPack } from '@/api';
import { SPECIES_RARITY_META, GENE_META, HABITAT_INFO, PACK_TIER_META, PACK_TIER_ORDER, geneLabel, lifeLeft, type GeneKey } from '@/data/packs';
import { AnimalArt } from '@/components/AnimalArt';
import { RARITY_RANK } from '@/lib/animalQuality';

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
}> = {
  rare: {
    ...PACK_TIER_META.rare,
    glow: 'rgba(74,158,221,0.55)',
    bg: 'radial-gradient(ellipse at 50% 34%, rgba(74,158,221,0.20) 0%, rgba(10,15,30,0.98) 72%)',
    border: 'rgba(74,158,221,0.45)',
    image: '/packs/pack-rare.webp',
    openVideo: '/packs/zoopark-rare.mp4',
  },
  epic: {
    ...PACK_TIER_META.epic,
    glow: 'rgba(168,85,247,0.55)',
    bg: 'radial-gradient(ellipse at 50% 34%, rgba(168,85,247,0.20) 0%, rgba(12,8,30,0.98) 72%)',
    border: 'rgba(168,85,247,0.45)',
    image: '/packs/pack-epic.webp',
    openVideo: '/packs/zoopark-epic.mp4',
  },
  legendary: {
    ...PACK_TIER_META.legendary,
    glow: 'rgba(245,158,11,0.55)',
    bg: 'radial-gradient(ellipse at 50% 34%, rgba(245,158,11,0.20) 0%, rgba(20,14,4,0.98) 72%)',
    border: 'rgba(245,158,11,0.45)',
    image: '/packs/pack-legendary.webp',
    openVideo: '/packs/zoopark-legendary.mp4',
  },
  mythic: {
    ...PACK_TIER_META.mythic,
    glow: 'rgba(239,68,68,0.55)',
    bg: 'radial-gradient(ellipse at 50% 34%, rgba(239,68,68,0.20) 0%, rgba(20,6,6,0.98) 72%)',
    border: 'rgba(239,68,68,0.45)',
    image: '/packs/pack-mythic.webp',
    openVideo: '/packs/zoopark-mythic.mp4',
  },
};

const BATCH_SIZES = [1, 5, 10, 50, 100] as const;
const PACK_SKIP_INTRO_STORAGE_KEY = 'zoopark_pack_skip_intro_v1';

function packSkipIntroStorageKey(playerId: number): string {
  return `${PACK_SKIP_INTRO_STORAGE_KEY}:${playerId}`;
}

function readPackSkipIntro(playerId: number): boolean {
  try {
    return window.localStorage.getItem(packSkipIntroStorageKey(playerId)) === '1';
  } catch {
    return false;
  }
}

function writePackSkipIntro(playerId: number, value: boolean): void {
  try {
    window.localStorage.setItem(packSkipIntroStorageKey(playerId), value ? '1' : '0');
  } catch {
    // Storage can be unavailable in a restricted Telegram/browser context.
  }
}

// ─── Pack art (levitating still) ──────────────────────────────────────────────

function PackArt({ tier, big = false }: { tier: (typeof TIERS)[TierKey]; big?: boolean }) {
  return (
    <div className="absolute inset-0 overflow-hidden">
      <div
        className="absolute inset-0"
        aria-hidden
        style={{ background: `radial-gradient(ellipse 62% 44% at 50% 40%, ${tier.glow} 0%, transparent 66%)` }}
      />
      <div className="absolute inset-0 grid place-items-center">
        <div className="relative" style={{ height: big ? '76%' : '82%', maxWidth: big ? '80%' : '66%', aspectRatio: '210 / 345' }}>
          <div
            className="pack-shadow absolute left-1/2"
            aria-hidden
            style={{ bottom: '-8%', width: '74%', height: '11%', background: `radial-gradient(ellipse, ${tier.glow} 0%, transparent 72%)`, filter: 'blur(3px)' }}
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

// ─── Tile status ──────────────────────────────────────────────────────────────
// Tiers are a daily unlock ladder, but an UNLOCKED tier never locks after opening — it
// stays buyable and can be reopened all day. Only not-yet-reached tiers are locked.

function PackTile({ tierKey, unlocked, price, onClick }: {
  tierKey: TierKey;
  unlocked: boolean;
  price: number;
  onClick: () => void;
}) {
  const info = TIERS[tierKey];
  const idx = PACK_TIER_ORDER.indexOf(tierKey);
  const lockReason = idx > 0 ? `Открой ${TIERS[PACK_TIER_ORDER[idx - 1]].name.toLowerCase()}` : '';
  return (
    <button
      onClick={onClick}
      disabled={!unlocked}
      className="relative overflow-hidden rounded-2xl border-none p-0"
      style={{
        aspectRatio: '3/4',
        background: info.bg,
        border: `1.5px solid ${unlocked ? info.color : info.border}`,
        boxShadow: unlocked ? `0 0 22px ${info.glow}, 0 6px 20px rgba(0,0,0,0.5)` : '0 4px 16px rgba(0,0,0,0.4)',
        cursor: unlocked ? 'pointer' : 'default',
      }}
    >
      <div style={{ opacity: unlocked ? 1 : 0.4 }}>
        <PackArt tier={info} />
      </div>

      <div className="absolute bottom-[8px] left-0 right-0 flex flex-col items-center gap-[5px]" style={{ pointerEvents: 'none' }}>
        <span
          className="px-3 py-[4px] rounded-full text-[11px] font-extrabold tracking-wide"
          style={{ background: `${info.color}28`, color: info.color, border: `1px solid ${info.color}55`, backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)' }}
        >
          {info.name}
        </span>
        {unlocked && (
          <span className="text-[12px] font-black tabular-nums" style={{ color: '#fff', textShadow: '0 1px 4px rgba(0,0,0,0.8)' }}>
            ${fmt(price)}
          </span>
        )}
      </div>

      {!unlocked && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 px-2 text-center" style={{ background: 'rgba(7,9,17,0.55)', pointerEvents: 'none' }}>
          <span className="text-[22px]" aria-hidden>🔒</span>
          <span className="text-[10.5px] font-bold leading-tight" style={{ color: 'rgba(255,255,255,0.9)' }}>{lockReason}</span>
        </div>
      )}
    </button>
  );
}

// ─── Reward reveal (Brawl-style, one at a time) ───────────────────────────────

const GENE_ROW: { key: GeneKey; label: string }[] = [
  { key: 'survival', label: 'Выживаемость' },
  { key: 'appearance', label: 'Внешность' },
  { key: 'size_trait', label: 'Размер' },
  { key: 'reproduction', label: 'Размножение' },
];
const TIER_FILL: Record<GeneTier, number> = { low: 1, medium: 2, high: 3 };

function RewardParticles({ color }: { color: string }) {
  // A ring of particles bursting outward — the "casino" pop on each reveal.
  return (
    <div className="pointer-events-none absolute inset-0 grid place-items-center" aria-hidden>
      {Array.from({ length: 14 }).map((_, i) => (
        <span
          key={i}
          className="absolute block rounded-full"
          style={{
            width: 7, height: 7, background: color,
            boxShadow: `0 0 8px ${color}`,
            ['--angle' as string]: `${(360 / 14) * i}deg`,
            animation: `reward-particle 0.9s ease-out ${0.05 + (i % 5) * 0.03}s both`,
          } as CSSProperties}
        />
      ))}
    </div>
  );
}

function AnimalRevealCard({ animal }: { animal: Animal }) {
  const rarity = SPECIES_RARITY_META[animal.species_rarity];
  const life = lifeLeft(animal.dies_at);
  const habitat = HABITAT_INFO[animal.habitat];
  return (
    <div
      className="relative mx-auto w-full max-w-[340px] rounded-3xl px-5 pt-5 pb-4"
      style={{
        background: `linear-gradient(160deg, ${rarity.color}26, rgba(10,12,22,0.94))`,
        border: `1.5px solid ${rarity.color}`,
        boxShadow: `0 0 40px ${rarity.color}55, inset 0 1px 0 rgba(255,255,255,0.08)`,
      }}
    >
      <RewardParticles color={rarity.color} />
      <div className="relative">
        <div className="mx-auto grid h-[150px] w-[150px] place-items-center rounded-2xl" style={{ background: `radial-gradient(circle at 50% 45%, ${rarity.color}33, transparent 70%)` }}>
          <AnimalArt animal={animal} size={140} />
        </div>
        <p className="m-0 mt-2 text-center text-[19px] font-black">{animal.name}</p>
        <p className="m-0 text-center text-[12px] font-semibold" style={{ color: 'var(--tg-theme-hint-color)' }}>{animal.species_name}</p>
        <p className="m-0 text-center text-[11px] font-extrabold uppercase tracking-wide" style={{ color: rarity.color }}>{rarity.label}</p>

        {/* Genes */}
        <div className="mt-3 rounded-2xl px-3 py-2" style={{ background: 'rgba(0,0,0,0.28)' }}>
          {GENE_ROW.map(g => {
            const val = animal[g.key] as GeneTier;
            const meta = GENE_META[g.key][val];
            const filled = TIER_FILL[val];
            return (
              <div key={g.key} className="flex items-center gap-2 py-[4px]">
                <span className="flex-1 text-left text-[11.5px] font-semibold">{g.label}</span>
                <span className="flex gap-[3px]" aria-hidden>
                  {[0, 1, 2].map(i => (
                    <span key={i} className="block h-[6px] w-[14px] rounded-full" style={{ background: i < filled ? meta.color : 'rgba(255,255,255,0.14)' }} />
                  ))}
                </span>
                <span className="w-[92px] text-right text-[11px] font-bold" style={{ color: meta.color }}>{geneLabel(g.key, val)}</span>
              </div>
            );
          })}
        </div>

        <div className="mt-2 flex items-center justify-between text-[12px]">
          <span style={{ color: 'var(--tg-theme-hint-color)' }}>{habitat.emoji} {habitat.name}</span>
          <span className="font-bold" style={{ color: 'var(--c-green)' }}>₽{fmt(animal.income)}/мин</span>
          {life && <span className="font-bold tabular-nums" style={{ color: life.color }}>⏳ {life.label}</span>}
        </div>
      </div>
    </div>
  );
}

function CurrencyRevealCard({ kind, amount }: { kind: 'rub' | 'usd'; amount: number }) {
  const color = kind === 'rub' ? 'var(--c-green)' : 'var(--c-gold)';
  const rgb = kind === 'rub' ? '99,194,104' : '243,181,63';
  return (
    <div
      className="relative mx-auto w-full max-w-[300px] rounded-3xl px-6 py-8 text-center"
      style={{ background: `radial-gradient(circle at 50% 40%, rgba(${rgb},0.22), rgba(10,12,22,0.94))`, border: `1.5px solid rgba(${rgb},0.6)`, boxShadow: `0 0 40px rgba(${rgb},0.4)` }}
    >
      <RewardParticles color={`rgb(${rgb})`} />
      <div className="relative">
        <p className="m-0 text-[52px] leading-none">{kind === 'rub' ? '💰' : '💵'}</p>
        <p className="m-0 mt-3 text-[11px] font-bold uppercase tracking-widest" style={{ color }}>{kind === 'rub' ? 'Рубли' : 'Доллары'}</p>
        <p className="m-0 mt-1 text-[38px] font-black tabular-nums" style={{ color }}>
          {kind === 'rub' ? `+₽${fmt(amount)}` : `+$${fmt(amount)}`}
        </p>
      </div>
    </div>
  );
}

// ─── Full-screen pack opening ─────────────────────────────────────────────────

type ModalOpenState = 'idle' | 'opening';
type RevealItem = { kind: 'animal'; animal: Animal } | { kind: 'rub' | 'usd'; amount: number };

function PackModal({ tierKey, isGift, batchPrices, playerId, onClose, onSuccess }: {
  tierKey: TierKey;
  isGift: boolean;
  batchPrices?: Record<string, number>;
  playerId: number;
  onClose: () => void;
  onSuccess: (res: PackOpenResult) => void;
}) {
  const [openState, setOpenState] = useState<ModalOpenState>('idle');
  const [revealedTier, setRevealedTier] = useState<TierKey | null>(null);
  const [items, setItems] = useState<RevealItem[]>([]);
  const [step, setStep] = useState(0);
  const [quantity, setQuantity] = useState<(typeof BATCH_SIZES)[number]>(1);
  const [skipIntro, setSkipIntro] = useState(() => readPackSkipIntro(playerId));
  const [totals, setTotals] = useState<{ rub: number; usd: number } | null>(null);
  const [apiDone, setApiDone] = useState(false);
  const [animDone, setAnimDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const tier = TIERS[revealedTier ?? tierKey];

  const updateSkipIntro = (value: boolean) => {
    setSkipIntro(value);
    writePackSkipIntro(playerId, value);
  };

  useEffect(() => {
    if (openState !== 'opening') return;
    const video = videoRef.current;
    if (!video) {
      const t = setTimeout(() => setAnimDone(true), 50);
      return () => clearTimeout(t);
    }
    let fired = false;
    const trigger = () => { if (!fired) { fired = true; setAnimDone(true); } };
    if (video.ended) { trigger(); return; }
    video.addEventListener('ended', trigger, { once: true });
    const fallback = setTimeout(trigger, 4200);
    return () => { video.removeEventListener('ended', trigger); clearTimeout(fallback); };
  }, [openState]);

  useEffect(() => {
    if (!error) return;
    const t = window.setTimeout(() => setError(null), 3500);
    return () => window.clearTimeout(t);
  }, [error]);

  const handleOpen = async () => {
    if (openState !== 'idle') return;
    setOpenState('opening');
    setApiDone(false);
    setAnimDone(false);
    setError(null);
    try {
      const selectedQuantity = isGift ? 1 : quantity;
      const res = await apiOpenPack(isGift ? undefined : tierKey, selectedQuantity);
      setRevealedTier(res.tier);
      // Reveal order builds suspense: currencies first, then animals rarest-last.
      const animals = [...res.animals].sort((a, b) => RARITY_RANK[a.species_rarity] - RARITY_RANK[b.species_rarity]);
      const list: RevealItem[] = [];
      if (res.rewards.rub) list.push({ kind: 'rub', amount: res.rewards.rub });
      if (res.rewards.usd) list.push({ kind: 'usd', amount: res.rewards.usd });
      animals.forEach(animal => list.push({ kind: 'animal', animal }));
      setItems(list);
      setTotals(res.rewards);
      // Batch requests go straight to the compact ledger summary. A single pack
      // retains the tactile reveal unless the keeper explicitly skips it.
      setStep(selectedQuantity > 1 ? list.length : 0);
      setApiDone(true);
      if (selectedQuantity > 1 || skipIntro) setAnimDone(true);
      onSuccess(res);
    } catch (e) {
      setError((e as Error).message);
      setOpenState('idle');
    }
  };

  // Derived phases: once the API and the unwrap animation are both done, we're revealing.
  const revealing = openState === 'opening' && apiDone && animDone;
  const opening = openState === 'opening' && !revealing;
  const atSummary = step >= items.length;
  const current = items[step];
  const isBigDrop = (revealedTier === 'legendary' || revealedTier === 'mythic')
    || (current?.kind === 'animal' && (current.animal.species_rarity === 'legendary' || current.animal.species_rarity === 'mythic'));

  const advance = () => { if (revealing && !atSummary) setStep(s => s + 1); };

  return createPortal(
    <section
      className="fixed inset-0 z-[200] flex min-h-0 flex-col overflow-hidden"
      role="dialog"
      aria-modal="true"
      style={{
        backgroundColor: '#0d0b16',
        backgroundImage: `radial-gradient(circle at 50% 36%, ${tier.color}30 0%, transparent 46%), radial-gradient(circle at 50% 92%, ${tier.color}14 0%, transparent 50%)`,
        minHeight: '100dvh',
      }}
    >
      {/* Reveal drama layers */}
      {revealing && !atSummary && (
        <>
          <div key={step} className="reveal-flash" />
          {isBigDrop && <div className="reveal-rays" style={{ '--ray': `${tier.color}55` } as CSSProperties} />}
          <div className="reveal-aura" style={{ '--aura': `${tier.color}44` } as CSSProperties} />
        </>
      )}

      <header className="relative z-20 flex shrink-0 items-center justify-between px-4 pb-3" style={{ paddingTop: 'calc(var(--safe-top) + 12px)' }}>
        <span className="text-[12px] font-extrabold uppercase tracking-[0.16em]" style={{ color: tier.color }}>
          {isGift ? 'Подарок' : `${tier.name} пак`}
        </span>
        {openState === 'idle' && (
          <button onClick={onClose} className="tap-target rounded-full border-none px-4 text-[13px] font-extrabold" style={{ background: 'rgba(7,9,17,0.52)', color: 'rgba(255,255,255,0.92)', border: '1px solid rgba(255,255,255,0.14)' }}>
            Закрыть
          </button>
        )}
      </header>

      {error && (
        <div className="fixed left-4 right-4 z-30 rounded-2xl px-4 py-3" role="alert" style={{ top: 'calc(var(--safe-top) + 66px)', background: 'rgba(56,13,20,0.98)', border: '1px solid rgba(232,86,76,0.78)', animation: 'slide-down 0.22s var(--spring-smooth) both' }}>
          <p className="m-0 text-[13px] leading-snug" style={{ color: 'rgba(255,255,255,0.9)' }}>{error}</p>
        </div>
      )}

      {/* ── IDLE: full-screen pack, tap to open ── */}
      {openState === 'idle' && (
        <div className="relative z-10 flex min-h-0 flex-1 flex-col">
          <button
            onClick={handleOpen}
            className="relative min-h-0 flex-1 border-none bg-transparent p-0"
            aria-label={`Открыть ${tier.name.toLowerCase()} пак`}
          >
            <div className="absolute inset-0"><PackArt tier={tier} big /></div>
            <span
              className="absolute bottom-[12%] left-1/2 -translate-x-1/2 rounded-full px-6 py-3 text-[14px] font-black tracking-wide whitespace-nowrap"
              style={{ background: `${tier.color}22`, color: '#fff', border: `1.5px solid ${tier.color}`, boxShadow: `0 0 24px ${tier.color}66`, animation: 'glow-pulse 1.6s ease-in-out infinite' }}
            >
              {isGift ? 'ТАПНИ, ЧТОБЫ ОТКРЫТЬ' : `ОТКРЫТЬ · $${fmt(batchPrices?.[String(quantity)] ?? 0)}`}
            </span>
          </button>
          {!isGift && (
            <div className="shrink-0 px-5 pb-4" style={{ paddingBottom: 'calc(var(--safe-bottom) + 16px)' }}>
              <div className="rounded-2xl px-3 py-3" style={{ background: 'rgba(7,9,17,0.52)', border: '1px solid rgba(255,255,255,0.12)' }}>
                <div className="flex items-center justify-between gap-3">
                  <p className="m-0 text-[11px] font-extrabold uppercase tracking-[0.12em]" style={{ color: 'var(--tg-theme-hint-color)' }}>Сколько открыть</p>
                  <span className="text-[12px] font-black" style={{ color: tier.color }}>${fmt(batchPrices?.[String(quantity)] ?? 0)}</span>
                </div>
                <div className="mt-2 grid grid-cols-5 gap-1">
                  {BATCH_SIZES.map(size => (
                    <button
                      key={size}
                      type="button"
                      onClick={() => { setQuantity(size); if (size > 1) updateSkipIntro(true); }}
                      className="min-h-[40px] rounded-xl border-none text-[12px] font-black"
                      style={{ background: quantity === size ? `${tier.color}2d` : 'rgba(255,255,255,0.07)', color: quantity === size ? tier.color : 'rgba(255,255,255,0.72)', border: `1px solid ${quantity === size ? tier.color : 'rgba(255,255,255,0.08)'}` }}
                    >
                      {size}
                    </button>
                  ))}
                </div>
                <label className="mt-2 flex items-center justify-center gap-2 text-[11px] font-bold" style={{ color: 'rgba(255,255,255,0.72)' }}>
                  <input type="checkbox" checked={skipIntro} onChange={event => updateSkipIntro(event.target.checked)} />
                  Пропустить заставку
                </label>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── OPENING: unwrap video ── */}
      {opening && (
        <div className="relative z-10 flex-1">
          <video ref={videoRef} src={tier.openVideo} autoPlay muted playsInline className="pack-video-screen h-full w-full object-contain" />
        </div>
      )}

      {/* ── REVEALING: one reward at a time ── */}
      {revealing && (
        <main className="relative z-10 flex min-h-0 flex-1 flex-col px-5 pb-4" onClick={advance}>
          {!atSummary && current && (
            <div className="flex min-h-0 flex-1 flex-col items-center justify-center">
              {/* progress dots */}
              <div className="mb-4 flex gap-[6px]">
                {items.map((_, i) => (
                  <span key={i} className="block h-[6px] w-[6px] rounded-full" style={{ background: i <= step ? tier.color : 'rgba(255,255,255,0.2)' }} />
                ))}
              </div>
              <div key={step} style={{ animation: 'reveal-pop 0.5s var(--spring-bounce) both', width: '100%' }}>
                {current.kind === 'animal'
                  ? <AnimalRevealCard animal={current.animal} />
                  : <CurrencyRevealCard kind={current.kind} amount={current.amount} />}
              </div>
              <p className="mt-5 text-[12px] font-semibold" style={{ color: 'var(--tg-theme-hint-color)', animation: 'glow-pulse 1.6s ease-in-out infinite' }}>
                {step + 1 < items.length ? 'Нажми, чтобы продолжить →' : 'Нажми, чтобы завершить →'}
              </p>
            </div>
          )}

          {/* ── SUMMARY ── */}
          {atSummary && totals && (
            <div className="mx-auto flex min-h-0 w-full max-w-[420px] flex-1 flex-col pt-2" style={{ animation: 'scale-in 0.35s var(--spring-bounce) both' }}>
              <div className="text-center">
                <p className="m-0 text-[12px] font-black uppercase tracking-[0.2em]" style={{ color: tier.color }}>
                  {revealedTier ? `${TIERS[revealedTier].name} — ` : ''}{quantity > 1 ? `${quantity} паков открыто` : 'открыто'}
                </p>
                <h2 className="m-0 mt-1 text-[26px] font-black">Твои награды</h2>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div className="rounded-2xl px-4 py-3 text-left" style={{ background: 'rgba(99,194,104,0.14)', border: '1px solid rgba(99,194,104,0.45)' }}>
                  <p className="m-0 text-[11px] font-bold uppercase" style={{ color: 'var(--c-green)' }}>Рубли</p>
                  <p className="m-0 mt-1 text-[22px] font-black">+₽{fmt(totals.rub)}</p>
                </div>
                <div className="rounded-2xl px-4 py-3 text-left" style={{ background: 'rgba(243,181,63,0.14)', border: '1px solid rgba(243,181,63,0.45)' }}>
                  <p className="m-0 text-[11px] font-bold uppercase" style={{ color: 'var(--c-gold)' }}>Доллары</p>
                  <p className="m-0 mt-1 text-[22px] font-black">+${fmt(totals.usd)}</p>
                </div>
              </div>
              <div className="mt-3 flex-1 overflow-y-auto">
                <p className="m-0 mb-2 text-left text-[12px] font-extrabold" style={{ color: 'var(--tg-theme-hint-color)' }}>
                  ЖИВОТНЫЕ · {items.filter(i => i.kind === 'animal').length} шт.
                </p>
                {quantity > 1 && (
                  <div className="mb-3 grid grid-cols-2 gap-2">
                    {(['rare', 'epic', 'legendary', 'mythic'] as const).map(rarity => {
                      const count = items.filter(i => i.kind === 'animal' && i.animal.species_rarity === rarity).length;
                      return <div key={rarity} className="rounded-xl px-3 py-2" style={{ background: `${SPECIES_RARITY_META[rarity].color}14`, border: `1px solid ${SPECIES_RARITY_META[rarity].color}38` }}>
                        <span className="block text-[10px] font-bold" style={{ color: SPECIES_RARITY_META[rarity].color }}>{SPECIES_RARITY_META[rarity].label}</span>
                        <strong className="block mt-1 text-[18px]">{count}</strong>
                      </div>;
                    })}
                  </div>
                )}
                <div className="grid grid-cols-4 gap-2">
                  {items.filter(i => i.kind === 'animal').slice(0, quantity > 1 ? 24 : undefined).map((it, i) => {
                    const a = (it as { animal: Animal }).animal;
                    const rc = SPECIES_RARITY_META[a.species_rarity].color;
                    return (
                      <div key={i} className="rounded-xl p-1" style={{ background: `${rc}18`, border: `1px solid ${rc}55` }}>
                        <AnimalArt animal={a} size={56} className="mx-auto" />
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </main>
      )}

      {revealing && atSummary && (
        <footer className="relative z-10 shrink-0 px-5 pt-3" style={{ paddingBottom: 'calc(var(--safe-bottom) + 16px)' }}>
          <button onClick={onClose} className="w-full rounded-2xl border-none py-4 text-[16px] font-extrabold" style={{ background: `${tier.color}24`, color: tier.color, border: `1px solid ${tier.color}60` }}>
            В зоопарк
          </button>
        </footer>
      )}
    </section>,
    document.body,
  );
}

// ─── Daily gift banner ────────────────────────────────────────────────────────

function DailyGiftBanner({ available, odds, onClick }: { available: boolean; odds?: PackInfo['gift_odds']; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      disabled={!available}
      className="w-full rounded-2xl border-none flex items-center gap-3 px-4 py-[14px]"
      style={{
        background: available ? 'linear-gradient(135deg, rgba(34,197,94,0.15), rgba(16,185,129,0.08))' : 'rgba(255,255,255,0.04)',
        border: available ? '1px solid rgba(34,197,94,0.35)' : '1px solid rgba(255,255,255,0.08)',
        boxShadow: available ? '0 4px 20px rgba(34,197,94,0.15)' : 'none',
        cursor: available ? 'pointer' : 'default',
        textAlign: 'left',
      }}
    >
      <div className="w-12 h-12 rounded-2xl grid place-items-center text-[24px] shrink-0" style={{ background: available ? 'rgba(34,197,94,0.15)' : 'rgba(255,255,255,0.05)', border: available ? '1px solid rgba(34,197,94,0.3)' : '1px solid rgba(255,255,255,0.08)' }}>
        🎁
      </div>
      <div className="flex-1 min-w-0">
        <p className="m-0 font-extrabold text-[15px]">Ежедневный подарок</p>
        <p className="m-0 mt-[2px] text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
          {available ? 'Случайная редкость — открой и узнай' : 'Уже получен сегодня'}
        </p>
        {available && odds && odds.length > 0 && (
          <div className="mt-[6px] flex flex-wrap gap-x-[10px] gap-y-[2px]">
            {odds.map(o => (
              <span key={o.tier} className="text-[10.5px] font-bold" style={{ color: TIERS[o.tier].color }}>{TIERS[o.tier].name} {o.percent}%</span>
            ))}
          </div>
        )}
      </div>
      <span className="text-[12px] font-bold px-3 py-[5px] rounded-full shrink-0" style={{ background: available ? 'rgba(34,197,94,0.2)' : 'rgba(255,255,255,0.06)', color: available ? 'var(--c-green)' : 'var(--tg-theme-hint-color)', border: available ? '1px solid rgba(34,197,94,0.35)' : '1px solid rgba(255,255,255,0.1)' }}>
        {available ? 'FREE' : '✓'}
      </span>
    </button>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function PacksPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [info, setInfo] = useState<PackInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  // 'gift' opens the daily gift; a TierKey opens that paid tier.
  const [modal, setModal] = useState<TierKey | 'gift' | null>(null);

  useEffect(() => {
    apiGetPacksInfo()
      .then(setInfo)
      .catch(() => setLoadError('Ошибка загрузки'))
      .finally(() => setLoading(false));
  }, []);

  const handleSuccess = (res: PackOpenResult) => {
    // Reflect unlocks immediately, then refresh prices because every paid opening raises
    // the next pack price by 5% for the current day.
    setInfo(prev => prev && {
      ...prev,
      gift_available: res.gift_available,
      tiers: prev.tiers.map(t => ({ ...t, unlocked: res.unlocked_tiers.includes(t.tier) })),
    });
    void apiGetPacksInfo().then(setInfo).catch(() => undefined);
    onRefresh();
  };

  if (loading) {
    return <div className="flex justify-center py-16"><div className="spinner" /></div>;
  }
  if (loadError || !info) {
    return <div className="px-4 py-8 text-center"><p className="text-[14px]" style={{ color: 'var(--c-red)' }}>{loadError ?? 'Ошибка загрузки'}</p></div>;
  }

  const byTier = (t: TierKey) => info.tiers.find(x => x.tier === t)!;

  return (
    <div className="px-[14px] pt-4 pb-6 flex flex-col gap-4">
      <div>
        <p className="m-0 font-extrabold text-[17px]">🎁 Паки с животными</p>
        <p className="m-0 mt-[2px] text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
          Открой тир по лестнице · каждая следующая покупка до конца сезона дороже на 35% от базовой цены
        </p>
      </div>

      <DailyGiftBanner available={info.gift_available} odds={info.gift_odds} onClick={() => setModal('gift')} />

      <div className="grid grid-cols-2 gap-3">
        {PACK_TIER_ORDER.map(tk => {
          const t = byTier(tk);
          return <PackTile key={tk} tierKey={tk} unlocked={t.unlocked} price={t.price} onClick={() => t.unlocked && setModal(tk)} />;
        })}
      </div>

      <p className="m-0 text-center text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
        Баланс: <strong style={{ color: 'var(--c-gold)' }}>${fmt(gs.usd)}</strong> · доллары купишь в банке за рубли
      </p>

      {modal && (
        <PackModal
          tierKey={modal === 'gift' ? 'rare' : modal}
          isGift={modal === 'gift'}
          batchPrices={modal === 'gift' ? undefined : byTier(modal).batch_prices}
          playerId={gs.tg_id}
          onClose={() => setModal(null)}
          onSuccess={handleSuccess}
        />
      )}
    </div>
  );
}
