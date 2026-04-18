export interface GameDef {
  id: string;
  name: string;
  emoji: string;
  description: string;
  detail: string;
}

export const GAMES: GameDef[] = [
  {
    id: 'darts',
    name: 'Дартс',
    emoji: '🎯',
    description: 'Брось дротик в цель. Чем выше — тем лучше!',
    detail: '· случайно 1-10 ходов',
  },
  {
    id: 'bowling',
    name: 'Боулинг',
    emoji: '🎳',
    description: 'Сбей как можно больше кеглей!',
    detail: '· случайно 1-10 ходов',
  },
  {
    id: 'dice',
    name: 'Кубик',
    emoji: '🎲',
    description: 'Классический кубик — удача решает всё!',
    detail: '· случайно 1-10 ходов',
  },
  {
    id: 'football',
    name: 'Футбол',
    emoji: '⚽',
    description: 'Забивай голы в ворота противника!',
    detail: '· случайно 1-10 ходов',
  },
];
