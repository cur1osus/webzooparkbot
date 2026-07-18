export type RootTab = 'zoo' | 'shop' | 'lab' | 'games' | 'more' | 'bank' | 'bonus' | 'merchant' | 'top';

const PRIMARY_TABS: { id: RootTab; emoji: string; label: string }[] = [
  { id: 'zoo',   emoji: '🏡', label: 'Зоопарк'     },
  { id: 'shop',  emoji: '🛒', label: 'Магазин'      },
  { id: 'lab',   emoji: '🧪', label: 'Лаборатория'  },
  { id: 'games', emoji: '🎮', label: 'Игры'         },
  { id: 'more',  emoji: '☰',  label: 'Ещё'          },
];

const QUICK_TABS: { id: RootTab; emoji: string; label: string }[] = [
  { id: 'bank', emoji: '🏦', label: 'Банк' },
  { id: 'bonus', emoji: '🎁', label: 'Бонус' },
  { id: 'merchant', emoji: '🧙', label: 'Торговец' },
  { id: 'top', emoji: '📊', label: 'Топ' },
];

export function TabBar({
  active,
  onChange,
}: {
  active: RootTab;
  onChange: (tab: RootTab) => void;
}) {
  return (
    <nav
      className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[480px] backdrop-blur-xl z-[100]"
      style={{
        paddingBottom: 'var(--safe-bottom)',
        background: 'color-mix(in srgb, var(--tg-theme-bottom-bar-bg-color) 94%, transparent)',
        // No top border — a hairline here reads as a stray line across the screen. The soft
        // shadow alone lifts the bar off the content.
        boxShadow: '0 -8px 26px rgba(0,0,0,0.38)',
      }}
    >
      <div className="border-t border-[color-mix(in_srgb,var(--tg-theme-hint-color)_10%,transparent)]">
        <div className="flex">
        {PRIMARY_TABS.map(t => {
          const isActive = t.id === active;
          return (
            <button
              key={t.id}
              onClick={() => onChange(t.id)}
              className={[
                'flex-1 flex flex-col items-center gap-[3px] px-1 pt-[13px] pb-[9px]',
                'border-none bg-transparent cursor-pointer relative transition-colors duration-200',
                isActive ? 'text-tg-button' : 'text-tg-hint',
              ].join(' ')}
            >
              {/* Signature: the active tab is lit from below like a low sun */}
              {isActive && (
                <span
                  aria-hidden
                  className="absolute inset-x-0 bottom-0 top-0 pointer-events-none"
                  style={{ background: 'radial-gradient(ellipse at 50% 118%, rgba(var(--c-gold-rgb),0.28) 0%, transparent 62%)' }}
                />
              )}
              <span
                className="text-[22px] leading-none relative transition-transform duration-200"
                style={isActive ? { transform: 'translateY(-1px)', filter: 'drop-shadow(0 3px 8px rgba(var(--c-gold-rgb),0.4))' } : undefined}
              >
                {t.emoji}
              </span>
              <span className={`relative text-[10px] tracking-[0.2px] leading-[1.3] ${isActive ? 'font-extrabold' : 'font-semibold'}`}>
                {t.label}
              </span>
            </button>
          );
        })}
        </div>
        <div className="flex border-t border-[color-mix(in_srgb,var(--tg-theme-hint-color)_8%,transparent)]">
        {QUICK_TABS.map(t => {
          const isActive = t.id === active;
          return (
            <button
              key={t.id}
              onClick={() => onChange(t.id)}
              className={[
                'flex-1 flex flex-col items-center gap-[2px] px-1 pt-[7px] pb-[6px]',
                'border-none bg-transparent cursor-pointer relative transition-colors duration-200',
                isActive ? 'text-tg-button' : 'text-tg-hint',
              ].join(' ')}
            >
              {isActive && <span aria-hidden className="absolute inset-x-0 bottom-0 top-0 pointer-events-none" style={{ background: 'radial-gradient(ellipse at 50% 118%, rgba(var(--c-gold-rgb),0.18) 0%, transparent 65%)' }} />}
              <span className="text-[17px] leading-none relative" style={isActive ? { filter: 'drop-shadow(0 2px 6px rgba(var(--c-gold-rgb),0.35))' } : undefined}>{t.emoji}</span>
              <span className={`relative text-[9px] tracking-[0.1px] leading-[1.3] ${isActive ? 'font-extrabold' : 'font-semibold'}`}>{t.label}</span>
            </button>
          );
        })}
        </div>
      </div>
    </nav>
  );
}
