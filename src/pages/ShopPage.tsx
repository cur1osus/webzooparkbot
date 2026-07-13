import { useState } from 'react';
import { fmt } from '@/utils/format';
import type { GameState, NicknameColor } from '@/types';
import { apiBuyNicknameColor, apiSetNicknameColor } from '@/api';
import { NICKNAME_COLORS } from '@/data/nicknameColors';
import { PacksPage } from './PacksPage';
import { LocalitiesPage } from './LocalitiesPage';
import { ForgeShopTab } from '@/features/forge/ForgeShopTab';
import { PageHeader } from '@/components/PageHeader';
import { TextWave } from '@/components/NicknameEffects';

const RARITY_LABEL = { standard: null, rare: 'Редкий', legendary: 'Легендарный' } as const;

type ShopTab = 'packs' | 'localities' | 'forge' | 'cosmetics';

const SHOP_TABS: { id: ShopTab; emoji: string; label: string }[] = [
  { id: 'packs',      emoji: '📦', label: 'Паки' },
  { id: 'localities', emoji: '🌍', label: 'Местности' },
  { id: 'forge',      emoji: '🔨', label: 'Кузница' },
  { id: 'cosmetics',  emoji: '🎨', label: 'Стиль' },
];

function ShimmerText({ children }: { children: string }) {
  return <span className="shimmer-text">{children}</span>;
}

function GlitchText({ children }: { children: string }) {
  return (
    <span className="glitch" data-text={children}>
      <ShimmerText>{children}</ShimmerText>
    </span>
  );
}

function StyleTab({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [selectedColor, setSelectedColor] = useState<NicknameColor>(gs.nickname_color);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Cached state from the previous app build may briefly lack this new field on startup.
  const colorStates = gs.nickname_colors ?? [];

  const setColor = async (color: NicknameColor) => {
    if (saving || color === gs.nickname_color) return;
    setSelectedColor(color);
    setSaving(true);
    setError(null);
    try {
      await apiSetNicknameColor(color);
      onRefresh();
    } catch (cause) {
      setSelectedColor(gs.nickname_color);
      setError(cause instanceof Error ? cause.message : 'Не удалось сохранить цвет');
    } finally {
      setSaving(false);
    }
  };

  const buyColor = async (color: NicknameColor) => {
    if (saving) return;
    setSelectedColor(color);
    setSaving(true);
    setError(null);
    try {
      await apiBuyNicknameColor(color);
      onRefresh();
    } catch (cause) {
      setSelectedColor(gs.nickname_color);
      setError(cause instanceof Error ? cause.message : 'Не удалось купить цвет');
    } finally {
      setSaving(false);
    }
  };

  const active = NICKNAME_COLORS.find(option => option.id === selectedColor) ?? NICKNAME_COLORS[0];
  const activeState = colorStates.find(color => color.id === selectedColor);
  const activeOwned = activeState?.owned ?? selectedColor === 'ivory';
  const activePrice = activeState?.price_paw ?? 0;
  const isCurrentColor = selectedColor === gs.nickname_color;

  return (
    <div className="px-[14px] pt-3 flex flex-col gap-3">
      <div
        className={`relative rounded-2xl px-4 py-5 ${active.animated ? `nickname-preview-${active.id}` : ''}`}
        style={{ background: active.animated ? undefined : `linear-gradient(135deg, ${active.glow}, transparent 68%), var(--tg-theme-secondary-bg-color)`, border: `1px solid ${active.value}52` }}
      >
        <div className="absolute -right-3 -top-8 text-[100px] opacity-[0.07] leading-none pointer-events-none">✦</div>
        <div className="relative">
          <p className="m-0 text-[11px] font-extrabold tracking-[0.7px] uppercase text-tg-hint">Подпись владельца</p>
          <p className={`m-0 mt-2 text-[25px] leading-none font-extrabold ${active.animated ? `nickname-color-${active.id}` : ''}`} style={{ color: active.value, textShadow: `0 0 18px ${active.glow}` }}>
            {active.id === 'neon' ? <GlitchText>{gs.nickname}</GlitchText> : active.id === 'wave' ? <TextWave text={gs.nickname} /> : gs.nickname}
          </p>
          <p className="m-0 mt-3 max-w-[270px] text-[13px] leading-[1.35] text-tg-hint">
            Цвет имени будет виден в таблице лидеров. Открытые оттенки остаются навсегда.
          </p>
        </div>
      </div>

      <div className="card">
        <div className="flex items-baseline justify-between gap-3 mb-3">
          <p className="m-0 font-extrabold text-[15px]">Палитра имени</p>
          {saving && <span className="text-[11px] font-bold text-tg-hint">Сохраняем...</span>}
        </div>
        <div className="grid grid-cols-2 gap-2">
          {NICKNAME_COLORS.map(option => {
            const isSelected = option.id === selectedColor;
            const state = colorStates.find(color => color.id === option.id);
            const owned = state?.owned ?? option.id === 'ivory';
            const price = state?.price_paw ?? 0;
            const rarity = state?.rarity ?? 'standard';
            return (
              <button
                key={option.id}
                type="button"
                onClick={() => setSelectedColor(option.id)}
                aria-pressed={isSelected}
                className="min-h-[58px] rounded-xl px-3 text-left"
                style={{
                  background: isSelected ? option.glow : 'var(--surface-subtle)',
                  border: `1px solid ${isSelected ? option.value : 'var(--surface-overlay-border)'}`,
                  borderRadius: '12px',
                  boxShadow: isSelected ? `inset 0 0 0 1px ${option.value}30` : 'none',
                }}
              >
                <span className="flex items-center gap-2">
                  <span
                    className={`w-4 h-4 rounded-full shrink-0 ${option.animated ? `nickname-swatch-${option.id}` : ''}`}
                    style={option.animated ? { boxShadow: `0 0 12px ${option.glow}` } : { background: option.value, boxShadow: `0 0 10px ${option.glow}` }}
                  />
                  <span className="min-w-0">
                    <span className={`block text-[13px] font-extrabold truncate ${option.animated ? `nickname-color-${option.id}` : ''}`} style={{ color: option.value }}>{option.label}</span>
                    <span className="block mt-[1px] text-[10px] text-tg-hint">
                      {isSelected ? 'Выбрано' : owned ? 'Надеть' : `${price} 🐾`}{RARITY_LABEL[rarity] ? ` · ${RARITY_LABEL[rarity]}` : ''}
                    </span>
                  </span>
                </span>
              </button>
            );
          })}
        </div>
        <button
          type="button"
          onClick={() => void (activeOwned ? setColor(selectedColor) : buyColor(selectedColor))}
          disabled={saving || isCurrentColor}
          className="w-full mt-3 min-h-[46px] rounded-xl border-none font-extrabold text-[14px] disabled:opacity-55"
          style={{
            background: activeOwned ? 'var(--c-blue)' : 'var(--c-purple)',
            color: 'var(--tg-theme-button-text-color)',
            boxShadow: activeOwned ? 'none' : `0 0 20px ${active.glow}`,
          }}
        >
          {saving ? 'Сохраняем...' : isCurrentColor ? 'Сейчас используется' : activeOwned ? `Надеть «${active.label}»` : `Купить за ${activePrice} 🐾`}
        </button>
        {error && <p className="m-0 mt-3 text-[12px] text-[var(--c-red-soft)]">{error}</p>}
      </div>
    </div>
  );
}

// ─── ShopPage ─────────────────────────────────────────────────────────────────

export function ShopPage({
  gs,
  onRefresh,
}: {
  gs: GameState;
  onRefresh: () => void;
}) {
  const [tab, setTab] = useState<ShopTab>('packs');

  return (
    <div className="page-content-safe">
      <PageHeader emoji="🛒" title="Зоомаркет" accent="var(--c-green-rgb)" />

      {/* Balance + seats */}
      <div className="px-[14px] pb-[10px]">
        <div className="flex gap-[6px] overflow-x-auto">
          {[
            { label: `₽ ${fmt(gs.rub)}`,    color: 'var(--c-green)' },
            { label: `$ ${fmt(gs.usd)}`,    color: 'var(--c-gold)' },
            { label: `🐾 ${gs.paw_coins}`,  color: 'var(--c-purple)' },
          ].map(({ label, color }) => (
            <span key={label} className="px-[10px] py-1 rounded-[20px] text-[13px] font-bold whitespace-nowrap shrink-0"
              style={{ background: `color-mix(in srgb, ${color} 10%, transparent)`, color, border: `1px solid color-mix(in srgb, ${color} 19%, transparent)` }}>
              {label}
            </span>
          ))}
          <span className="px-[10px] py-1 rounded-[20px] text-[13px] font-bold whitespace-nowrap shrink-0"
            style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 13%, transparent)', color: 'var(--tg-theme-hint-color)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 20%, transparent)' }}>
            🌍 {fmt(gs.localities_count)} местн.
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div
        className="flex mx-[14px] mb-1 rounded-2xl p-1"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 18%, transparent)' }}
      >
        {SHOP_TABS.map(t => {
          const isActive = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className="flex-1 flex flex-col items-center justify-center gap-[3px] py-[8px] rounded-xl border-none transition-all duration-200"
              style={{
                background: isActive ? 'color-mix(in srgb, var(--tg-theme-button-color) 15%, transparent)' : 'transparent',
                color: isActive ? 'var(--tg-theme-text-color)' : 'var(--tg-theme-hint-color)',
                boxShadow: isActive ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
              }}
            >
              <span className="text-[17px] leading-none">{t.emoji}</span>
              <span className={`text-[10px] leading-none ${isActive ? 'font-bold' : 'font-semibold'}`}>{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* PACKS */}
      {tab === 'packs' && <PacksPage gs={gs} onRefresh={onRefresh} />}

      {/* LOCALITIES */}
      {tab === 'localities' && <LocalitiesPage gs={gs} onRefresh={onRefresh} />}

      {/* FORGE */}
      {tab === 'forge' && <ForgeShopTab gs={gs} onRefresh={onRefresh} />}

      {/* COSMETICS */}
      {tab === 'cosmetics' && <StyleTab gs={gs} onRefresh={onRefresh} />}
    </div>
  );
}
