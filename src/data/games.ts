export interface GameDef {
  id: string;
  name: string;
  emoji: string;
  description: string;
  detail: string;
}

export const GAMES: GameDef[] = [
  {
    id: 'basketball',
    name: 'Баскетбол',
    emoji: '🏀',
    description: 'Серия бросков против соперника с анимацией Telegram.',
    detail: '· случайно 2-7 бросков',
  },
  {
    id: 'darts',
    name: 'Дартс',
    emoji: '🎯',
    description: 'Брось дротик в цель. Чем выше — тем лучше!',
    detail: '· случайно 2-7 бросков',
  },
  {
    id: 'bowling',
    name: 'Боулинг',
    emoji: '🎳',
    description: 'Сбей как можно больше кеглей!',
    detail: '· случайно 2-7 бросков',
  },
  {
    id: 'dice',
    name: 'Кубик',
    emoji: '🎲',
    description: 'Классический кубик — удача решает всё!',
    detail: '· случайно 2-7 бросков',
  },
  {
    id: 'football',
    name: 'Футбол',
    emoji: '⚽',
    description: 'Забивай голы в ворота противника!',
    detail: '· случайно 2-7 бросков',
  },
];
