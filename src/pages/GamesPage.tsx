import { useState } from 'react';
import { CocktailTab } from '@/features/games/CocktailTab';
import { SafeTab } from '@/features/games/SafeTab';
import { PageHeader } from '@/components/PageHeader';

type GamesTab = 'cocktail' | 'safe';

/* ──────────────────────────── MAIN PAGE ────────────────────────────── */
export function GamesPage({ onRefresh, initialTab = 'cocktail' }: { onRefresh: () => void; initialTab?: GamesTab }) {
  const [tab, setTab] = useState<GamesTab>(initialTab);

  const tabs: { id: GamesTab; emoji: string; label: string }[] = [
    { id: 'cocktail', emoji: '🥤', label: 'Коктейль' },
    { id: 'safe',     emoji: '🔐', label: 'Сейф' },
  ];

  return (
    <div className="page-content-safe">

      <PageHeader
        emoji="🎮"
        title="Игры"
        subtitle="Разгадай коктейль дня и вскрой сейф банка!"
        accent="var(--c-blue-rgb)"
      />

      {/* Tabs */}
      <div
        className="flex mx-[14px] rounded-2xl p-1 mb-1"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 18%, transparent)' }}
      >
        {tabs.map(t => {
          const isActive = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className="flex-1 flex items-center justify-center gap-[6px] py-[9px] rounded-xl border-none transition-all duration-200"
              style={{
                background: isActive ? 'color-mix(in srgb, var(--tg-theme-button-color) 15%, transparent)' : 'transparent',
                color: isActive ? 'var(--tg-theme-text-color)' : 'var(--tg-theme-hint-color)',
                boxShadow: isActive ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
              }}
            >
              <span className="text-[15px]">{t.emoji}</span>
              <span className="text-[12px] font-bold">{t.label}</span>
            </button>
          );
        })}
      </div>

      <div>
        {tab === 'cocktail' && <CocktailTab onRefresh={onRefresh} />}
        {tab === 'safe'     && <SafeTab onRefresh={onRefresh} />}
      </div>
    </div>
  );
}
