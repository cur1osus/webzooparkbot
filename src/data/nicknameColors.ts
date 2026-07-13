import type { NicknameColor } from '@/types';

export const NICKNAME_COLORS: { id: NicknameColor; label: string; value: string; glow: string; animated?: boolean }[] = [
  { id: 'ivory', label: 'Слоновая кость', value: '#f1f0ed', glow: 'rgba(241, 240, 237, 0.18)' },
  { id: 'gold', label: 'Латунь', value: '#f3b53f', glow: 'rgba(243, 181, 63, 0.28)' },
  { id: 'jade', label: 'Нефрит', value: '#63c268', glow: 'rgba(99, 194, 104, 0.28)' },
  { id: 'lagoon', label: 'Лагуна', value: '#56bfdc', glow: 'rgba(86, 191, 220, 0.28)' },
  { id: 'orchid', label: 'Орхидея', value: '#c072d8', glow: 'rgba(192, 114, 216, 0.28)' },
  { id: 'coral', label: 'Коралл', value: '#f0837b', glow: 'rgba(240, 131, 123, 0.28)' },
  { id: 'aurora', label: 'Аврора', value: '#82efd1', glow: 'rgba(130, 239, 209, 0.42)', animated: true },
  { id: 'embers', label: 'Угли', value: '#ff9569', glow: 'rgba(255, 112, 73, 0.42)', animated: true },
  { id: 'spectrum', label: 'Спектр', value: '#d896ff', glow: 'rgba(216, 150, 255, 0.42)', animated: true },
  { id: 'neon', label: 'Неон', value: '#72ffbc', glow: 'rgba(81, 255, 182, 0.52)', animated: true },
  { id: 'wave', label: 'Волна', value: '#ff8a00', glow: 'rgba(255, 138, 0, 0.42)', animated: true },
  { id: 'google', label: 'Google', value: '#4285f4', glow: 'rgba(66, 133, 244, 0.58)', animated: true },
];

export const nicknameColorValue = (color: string | null | undefined): string =>
  NICKNAME_COLORS.find(option => option.id === color)?.value ?? NICKNAME_COLORS[0].value;

export const nicknameColorClass = (color: string | null | undefined): string =>
  NICKNAME_COLORS.find(option => option.id === color)?.animated ? `nickname-color-${color}` : '';
