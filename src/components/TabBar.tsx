export type RootTab = 'zoo' | 'shop' | 'lab' | 'games' | 'more';

const TABS: { id: RootTab; emoji: string; label: string }[] = [
  { id: 'zoo',   emoji: '🏡', label: 'Зоопарк'     },
  { id: 'shop',  emoji: '🛒', label: 'Магазин'      },
  { id: 'lab',   emoji: '🧪', label: 'Лаборатория'  },
  { id: 'games', emoji: '🎮', label: 'Игры'         },
  { id: 'more',  emoji: '☰',  label: 'Ещё'          },
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
      className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[480px] bg-tg-secondary/95 backdrop-blur-xl border-t border-white/[0.07] z-[100] shadow-[0_-4px_24px_rgba(0,0,0,0.4)]"
      style={{ paddingBottom: 'var(--safe-bottom)' }}
    >
      <div className="flex">
        {TABS.map(t => {
          const isActive = t.id === active;
          return (
            <button
              key={t.id}
              onClick={() => onChange(t.id)}
              className={[
                'flex-1 flex flex-col items-center gap-[2px] px-1 pt-3 pb-[8px]',
                'border-none bg-transparent cursor-pointer relative',
                isActive ? 'text-tg-button' : 'text-tg-hint',
              ].join(' ')}
            >
              <span className="text-[22px] leading-none">{t.emoji}</span>
              <span className={`text-[10px] tracking-[0.1px] leading-[1.3] ${isActive ? 'font-bold' : 'font-normal'}`}>
                {t.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
