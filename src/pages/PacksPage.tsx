import { useEffect, useRef, useState } from 'react';
import { fmt } from '@/utils/format';
import type { GameState, PackAnimal, PackInfo } from '@/types';
import { apiGetPacksInfo, apiOpenPack } from '@/api';
import { getAnimalByInfoId } from '@/data/animals';
import { GENE_META, lifeLeft } from '@/data/packs';

// ─── Pack tiers ───────────────────────────────────────────────────────────────

type TierKey = 'rare' | 'epic' | 'legendary' | 'mythic';

const TIERS: Record<TierKey, {
  name: string;
  color: string;
  glow: string;
  bg: string;
  border: string;
  idleVideo: string;
  openVideo: string;
}> = {
  rare: {
    name: 'Редкий',
    color: '#4A9EDD',
    glow: 'rgba(74,158,221,0.55)',
    bg: 'radial-gradient(ellipse at 50% 30%, rgba(74,158,221,0.18) 0%, rgba(10,15,30,0.95) 70%)',
    border: 'rgba(74,158,221,0.45)',
    idleVideo: '/packs/zoopark-idle-rare.mp4',
    openVideo: '/packs/zoopark-rare.mp4',
  },
  epic: {
    name: 'Эпический',
    color: '#A855F7',
    glow: 'rgba(168,85,247,0.55)',
    bg: 'radial-gradient(ellipse at 50% 30%, rgba(168,85,247,0.18) 0%, rgba(12,8,30,0.95) 70%)',
    border: 'rgba(168,85,247,0.45)',
    idleVideo: '/packs/zoopark-idle-epic.mp4',
    openVideo: '/packs/zoopark-epic.mp4',
  },
  legendary: {
    name: 'Легендарный',
    color: '#F59E0B',
    glow: 'rgba(245,158,11,0.55)',
    bg: 'radial-gradient(ellipse at 50% 30%, rgba(245,158,11,0.18) 0%, rgba(20,14,4,0.95) 70%)',
    border: 'rgba(245,158,11,0.45)',
    idleVideo: '/packs/zoopark-idle-legendary.mp4',
    openVideo: '/packs/zoopark-legendary.mp4',
  },
  mythic: {
    name: 'Мифический',
    color: '#EF4444',
    glow: 'rgba(239,68,68,0.55)',
    bg: 'radial-gradient(ellipse at 50% 30%, rgba(239,68,68,0.18) 0%, rgba(20,6,6,0.95) 70%)',
    border: 'rgba(239,68,68,0.45)',
    idleVideo: '/packs/zoopark-idle-mythic.mp4',
    openVideo: '/packs/zoopark-mythic.mp4',
  },
};

function getTierKey(packsToday: number, freeAvailable: boolean): TierKey {
  if (freeAvailable) return 'rare';
  if (packsToday <= 1) return 'epic';
  if (packsToday <= 2) return 'legendary';
  return 'mythic';
}

// ─── Animal result card ───────────────────────────────────────────────────────

const HABITAT_INFO: Record<string, { emoji: string; name: string; color: string }> = {
  desert:     { emoji: '🐪', name: 'Пустыня',   color: 'var(--c-gold)' },
  mountains:  { emoji: '🦅', name: 'Горы',       color: 'var(--tg-theme-hint-color)' },
  forest:     { emoji: '🐆', name: 'Лес',        color: 'var(--c-green)' },
  fields:     { emoji: '🐴', name: 'Поля',        color: 'var(--c-teal)' },
  antarctica: { emoji: '🐧', name: 'Антарктида', color: 'var(--c-cyan)' },
};

function qualityScore(a: PackAnimal): number {
  const w: Record<string, number> = { low: 0, medium: 1, high: 2 };
  return w[a.survival] + w[a.reproduction] + w[a.appearance] + w[a.size_trait];
}

function qualityLabel(score: number): { text: string; color: string } {
  if (score >= 7) return { text: 'Идеальный',     color: 'var(--c-gold)' };
  if (score >= 5) return { text: 'Отличный',       color: 'var(--c-blue)' };
  if (score >= 3) return { text: 'Хороший',        color: 'var(--c-green)' };
  if (score >= 1) return { text: 'Посредственный', color: 'var(--tg-theme-hint-color)' };
  return             { text: 'Слабый',            color: 'var(--c-orange)' };
}

function AnimalCard({ animal, glow }: { animal: PackAnimal; glow: string }) {
  const hab  = HABITAT_INFO[animal.habitat];
  const def  = getAnimalByInfoId(animal.animal_info_id);
  const ql   = qualityLabel(qualityScore(animal));
  const life = lifeLeft(animal.dies_at);
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
        background: `linear-gradient(135deg, ${hab.color}18, rgba(16,18,32,0.95))`,
        border:     `1px solid ${hab.color}40`,
        boxShadow:  `0 0 32px ${glow}, 0 8px 24px rgba(0,0,0,0.5)`,
        animation:  'scale-in 0.4s var(--spring-bounce) both',
      }}
    >
      <div className="px-4 pt-4 pb-3 flex items-center gap-3">
        <div
          className="w-14 h-14 rounded-2xl grid place-items-center text-[28px] shrink-0"
          style={{ background: `${hab.color}25`, border: `1px solid ${hab.color}50` }}
        >
          {def?.emoji ?? hab.emoji}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-[6px]">
            <span className="font-extrabold text-[16px]">{def?.name ?? hab.name}</span>
            <span
              className="text-[11px] font-bold px-2 py-[2px] rounded-full"
              style={{ background: `${ql.color}20`, color: ql.color, border: `1px solid ${ql.color}35` }}
            >
              {ql.text}
            </span>
          </div>
          <p className="m-0 mt-[3px] text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            {hab.emoji} {hab.name}
          </p>
        </div>
        <div className="text-right shrink-0">
          <p className="m-0 text-[14px] font-extrabold" style={{ color: 'var(--c-green)' }}>
            ₽{fmt(animal.income)}
          </p>
          <p className="m-0 text-[10px]" style={{ color: 'var(--tg-theme-hint-color)' }}>в мин</p>
        </div>
      </div>

      <div style={{ height: 1, background: `${hab.color}20`, margin: '0 16px' }} />

      <div className="grid grid-cols-2 gap-[6px] px-4 py-3">
        {genes.map(([key, val]) => {
          const meta = GENE_META[key as keyof typeof GENE_META]?.[val as 'low' | 'medium' | 'high'];
          return (
            <div
              key={key}
              className="flex items-center gap-[6px] px-3 py-[6px] rounded-xl"
              style={{
                background: `${meta?.color ?? 'currentColor'}12`,
                border:     `1px solid ${meta?.color ?? 'currentColor'}22`,
              }}
            >
              <div className="w-[6px] h-[6px] rounded-full shrink-0" style={{ background: meta?.color }} />
              <span className="text-[10px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                {key === 'survival' ? 'Выж' : key === 'reproduction' ? 'Разм' : key === 'appearance' ? 'Вид' : 'Раз'}
              </span>
              <span className="ml-auto text-[11px] font-bold" style={{ color: meta?.color }}>
                {meta?.label}
              </span>
            </div>
          );
        })}
      </div>

      {life && (
        <div className="px-4 pb-4">
          <div
            className="flex items-center justify-between px-3 py-[7px] rounded-xl"
            style={{ background: `${life.color}12`, border: `1px solid ${life.color}30` }}
          >
            <span className="text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>⏳ Жизнь</span>
            <span className="text-[12px] font-extrabold" style={{ color: life.color }}>{life.label}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Pack stage (pure UI) ─────────────────────────────────────────────────────

type OpenState = 'idle' | 'opening' | 'revealed';

function PackStage({
  tier, info, gs, openState, newAnimal, error,
  onOpenClick, onAnimEnd, onOpenAnother,
}: {
  tier: (typeof TIERS)[TierKey];
  info: PackInfo;
  gs: GameState;
  openState: OpenState;
  newAnimal: PackAnimal | null;
  error: string | null;
  onOpenClick: () => void;
  onAnimEnd: () => void;
  onOpenAnother: () => void;
}) {
  const isOpening  = openState === 'opening';
  const isRevealed = openState === 'revealed';
  const videoRef   = useRef<HTMLVideoElement>(null);

  // Imperatively attach 'ended' listener when opening starts.
  // React synthetic onEnded is unreliable for short autoplay videos
  // (non-bubbling media events can fire before React attaches its handler).
  useEffect(() => {
    if (openState !== 'opening') return;
    const video = videoRef.current;
    if (!video) return;

    let fired = false;
    const trigger = () => {
      if (fired) return;
      fired = true;
      onAnimEnd();
    };

    // If browser already ended before effect ran
    if (video.ended) { trigger(); return; }

    video.addEventListener('ended', trigger, { once: true });

    // Fallback: derive remaining time once metadata is known
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
  }, [openState]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-col gap-4">

      {/* Video */}
      {!isRevealed && (
        <div
          className="relative mx-auto overflow-hidden rounded-3xl"
          style={{
            width: '100%',
            maxWidth: 340,
            aspectRatio: '3/4',
            background: tier.bg,
            border:     `1.5px solid ${tier.border}`,
            boxShadow:  `0 0 48px ${tier.glow}, 0 12px 40px rgba(0,0,0,0.6)`,
          }}
        >
          <video
            ref={videoRef}
            key={openState}
            src={isOpening ? tier.openVideo : tier.idleVideo}
            autoPlay
            loop={!isOpening}
            muted
            playsInline
            className="w-full h-full object-cover"
            style={{ display: 'block' }}
          />

          {!isOpening && (
            <div className="absolute bottom-4 left-0 right-0 flex justify-center">
              <span
                className="px-4 py-[6px] rounded-full text-[13px] font-extrabold tracking-wide"
                style={{
                  background: `${tier.color}25`,
                  color:      tier.color,
                  border:     `1px solid ${tier.color}50`,
                  backdropFilter: 'blur(8px)',
                  WebkitBackdropFilter: 'blur(8px)',
                }}
              >
                {tier.name}
              </span>
            </div>
          )}
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
                color:      tier.color,
                border:     `1px solid ${tier.color}40`,
              }}
            >
              ✨ {tier.name} пак
            </span>
          </div>
          <AnimalCard animal={newAnimal} glow={tier.glow} />
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

      {/* Open button */}
      {!isRevealed && (
        <div className="flex flex-col gap-2">
          <button
            onClick={onOpenClick}
            disabled={isOpening}
            className="w-full py-[14px] rounded-2xl font-extrabold text-[16px] border-none"
            style={{
              background: isOpening
                ? `${tier.color}30`
                : `linear-gradient(135deg, ${tier.color}, ${tier.color}cc)`,
              color:      isOpening ? tier.color : '#fff',
              boxShadow:  isOpening ? 'none' : `0 6px 20px ${tier.glow}`,
              transition: 'all 0.2s ease',
            }}
          >
            {isOpening
              ? '⏳ Открываем...'
              : info.free_available
              ? '🎁 Открыть бесплатно'
              : `🔓 Открыть · ₽${fmt(info.next_price)}`}
          </button>
          <div className="flex items-center justify-center gap-3">
            <span className="text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
              Баланс: <strong style={{ color: 'var(--c-green)' }}>₽{fmt(gs.rub)}</strong>
            </span>
            {info.packs_today > 0 && (
              <span className="text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                · Сегодня: {info.packs_today} шт.
              </span>
            )}
          </div>
        </div>
      )}

      {/* Open another */}
      {isRevealed && (
        <button
          onClick={onOpenAnother}
          className="w-full py-[13px] rounded-2xl font-bold text-[14px] border-none"
          style={{
            background: `${tier.color}18`,
            color:      tier.color,
            border:     `1px solid ${tier.color}35`,
          }}
        >
          Открыть ещё один
        </button>
      )}
    </div>
  );
}

// ─── Compact animal row ───────────────────────────────────────────────────────

function AnimalRow({ animal }: { animal: PackAnimal }) {
  const hab = HABITAT_INFO[animal.habitat];
  const def = getAnimalByInfoId(animal.animal_info_id);
  const ql  = qualityLabel(qualityScore(animal));

  return (
    <div
      className="flex items-center gap-3 px-3 py-[10px] rounded-xl"
      style={{ background: `${hab.color}0a`, border: `1px solid ${hab.color}20` }}
    >
      <span className="text-[22px] shrink-0">{def?.emoji ?? hab.emoji}</span>
      <div className="flex-1 min-w-0">
        <p className="m-0 text-[13px] font-bold truncate">{def?.name ?? hab.name}</p>
        <p className="m-0 text-[10px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
          {hab.emoji} {hab.name}
        </p>
      </div>
      <div className="text-right shrink-0 flex flex-col items-end gap-[3px]">
        <span
          className="text-[10px] font-bold px-2 py-[2px] rounded-full"
          style={{ background: `${ql.color}18`, color: ql.color, border: `1px solid ${ql.color}28` }}
        >
          {ql.text}
        </span>
        <span className="text-[11px] font-bold" style={{ color: 'var(--c-green)' }}>
          ₽{fmt(animal.income)}/мин
        </span>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function PacksPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [info, setInfo]           = useState<PackInfo | null>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);

  // Opening flow state — lives here so PackStage never remounts mid-flow
  const [openState, setOpenState]       = useState<OpenState>('idle');
  const [newAnimal, setNewAnimal]       = useState<PackAnimal | null>(null);
  const [apiDone, setApiDone]           = useState(false);
  const [animDone, setAnimDone]         = useState(false);
  // Lock tier at the moment of open so src never changes mid-animation
  const [lockedTierKey, setLockedTierKey] = useState<TierKey>('rare');

  useEffect(() => {
    apiGetPacksInfo()
      .then(setInfo)
      .catch(() => setError('Ошибка загрузки'))
      .finally(() => setLoading(false));
  }, []);

  // Reveal as soon as both animation and API are done
  useEffect(() => {
    if (apiDone && animDone && openState === 'opening') {
      setOpenState('revealed');
    }
  }, [apiDone, animDone, openState]);

  const handleOpenClick = async () => {
    if (openState !== 'idle' || !info) return;
    // Capture tier BEFORE any state updates so video src never changes mid-animation
    setLockedTierKey(getTierKey(info.packs_today, info.free_available));
    setOpenState('opening');
    setApiDone(false);
    setAnimDone(false);
    setError(null);

    try {
      const res = await apiOpenPack();
      setNewAnimal(res.animal);
      setInfo(prev => prev ? {
        ...prev,
        packs_today:    res.packs_today,
        free_available: false,
        next_price:     res.next_price,
        animals:        [res.animal, ...prev.animals],
      } : prev);
      onRefresh();
      setApiDone(true);
    } catch (e) {
      setError((e as Error).message);
      setOpenState('idle');
    }
  };

  const handleAnimEnd = () => {
    setAnimDone(true);
  };

  const handleOpenAnother = () => {
    setOpenState('idle');
    setNewAnimal(null);
    setApiDone(false);
    setAnimDone(false);
    setError(null);
  };

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="spinner" />
      </div>
    );
  }

  if (error || !info) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="text-[14px]" style={{ color: 'var(--c-red)' }}>{error ?? 'Ошибка загрузки'}</p>
      </div>
    );
  }

  // During opening/revealed use the locked tier so src never changes mid-animation
  const tierKey = openState !== 'idle' ? lockedTierKey : getTierKey(info.packs_today, info.free_available);
  const tier    = TIERS[tierKey];

  return (
    <div className="px-[14px] pt-4 pb-6 flex flex-col gap-5">

      {/* Header */}
      <div>
        <p className="m-0 font-extrabold text-[17px]">🎁 Паки с животными</p>
        <p className="m-0 mt-[2px] text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
          {info.free_available
            ? 'Ежедневный бесплатный пак доступен'
            : `Следующий пак: ₽${fmt(info.next_price)}`}
        </p>
      </div>

      {/* Pack stage — never remounts, receives all state as props */}
      <PackStage
        tier={tier}
        info={info}
        gs={gs}
        openState={openState}
        newAnimal={newAnimal}
        error={error}
        onOpenClick={handleOpenClick}
        onAnimEnd={handleAnimEnd}
        onOpenAnother={handleOpenAnother}
      />

      {/* Tier progression dots */}
      <div
        className="rounded-2xl px-4 py-3 flex items-center gap-3"
        style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 6%, transparent)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 10%, transparent)' }}
      >
        <div className="flex gap-[6px] items-center">
          {(['rare', 'epic', 'legendary', 'mythic'] as TierKey[]).map((t) => (
            <div
              key={t}
              className="w-3 h-3 rounded-full"
              style={{
                background: TIERS[t].color,
                opacity:    t === tierKey ? 1 : 0.3,
                transform:  t === tierKey ? 'scale(1.4)' : 'scale(1)',
                transition: 'all 0.2s',
              }}
            />
          ))}
        </div>
        <p className="m-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
          Чем больше паков в день — тем выше тир
        </p>
      </div>

      {/* Rules */}
      <div className="card">
        <p className="m-0 mb-2 font-bold text-[13px]">Как работают паки</p>
        <div className="flex flex-col gap-[6px]">
          {[
            ['🎁', '1 бесплатный пак каждый день (Редкий)'],
            ['📈', 'Каждый следующий пак дороже и выше тиром'],
            ['🧬', '4 гена: выживаемость, размножение, внешность, размер'],
            ['🌍', '5 сред обитания: бонус дохода в нужном вольере'],
          ].map(([icon, text]) => (
            <div key={text as string} className="flex items-start gap-2">
              <span className="text-[14px] shrink-0 mt-[1px]">{icon}</span>
              <span className="text-[12px] leading-relaxed" style={{ color: 'var(--tg-theme-hint-color)' }}>{text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Animal history */}
      {info.animals.length > 0 && (
        <div>
          <p className="m-0 mb-3 font-extrabold text-[14px]">
            Мои животные
            <span className="ml-2 text-[12px] font-normal" style={{ color: 'var(--tg-theme-hint-color)' }}>
              {info.animals.length} шт.
            </span>
          </p>
          <div className="flex flex-col gap-2">
            {info.animals.map(a => (
              <AnimalRow key={a.id} animal={a} />
            ))}
          </div>
        </div>
      )}

      {info.animals.length === 0 && (
        <div className="text-center py-6">
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
