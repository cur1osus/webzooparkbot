import type { NicknameColor } from '@/types';

export const NICKNAME_COLORS: { id: NicknameColor; label: string; value: string; glow: string; animated?: boolean }[] = [
  { id: 'ivory', label: 'Слоновая кость', value: '#f1f0ed', glow: 'rgba(241, 240, 237, 0.18)' },
  { id: 'gold', label: 'Латунь', value: '#f3b53f', glow: 'rgba(243, 181, 63, 0.28)' },
  { id: 'jade', label: 'Нефрит', value: '#63c268', glow: 'rgba(99, 194, 104, 0.28)' },
  { id: 'lagoon', label: 'Лагуна', value: '#56bfdc', glow: 'rgba(86, 191, 220, 0.28)' },
  { id: 'orchid', label: 'Орхидея', value: '#c072d8', glow: 'rgba(192, 114, 216, 0.28)' },
  { id: 'coral', label: 'Коралл', value: '#f0837b', glow: 'rgba(240, 131, 123, 0.28)' },
  { id: 'aurora', label: 'Аврора', value: '#3fe0b8', glow: 'rgba(63, 224, 184, 0.42)', animated: true },
  { id: 'embers', label: 'Угли', value: '#ff9569', glow: 'rgba(255, 112, 73, 0.42)', animated: true },
  { id: 'spectrum', label: 'Спектр', value: '#b06bff', glow: 'rgba(176, 107, 255, 0.42)', animated: true },
  { id: 'neon', label: 'Неон', value: '#ff43c4', glow: 'rgba(255, 67, 196, 0.52)', animated: true },
  { id: 'wave', label: 'Волна', value: '#ff8a00', glow: 'rgba(255, 138, 0, 0.42)', animated: true },
  { id: 'wave-azure', label: 'Волна лазурь', value: '#35b8ff', glow: 'rgba(53, 184, 255, 0.42)', animated: true },
  { id: 'wave-violet', label: 'Волна аметист', value: '#b57bff', glow: 'rgba(181, 123, 255, 0.42)', animated: true },
  { id: 'glitch', label: 'Глитч', value: '#ff5c5c', glow: 'rgba(120, 130, 255, 0.5)', animated: true },
  { id: 'glitch-aqua', label: 'Глитч аква', value: '#2fe0ff', glow: 'rgba(47, 224, 255, 0.5)', animated: true },
  { id: 'glitch-lime', label: 'Глитч токсик', value: '#a6ff4d', glow: 'rgba(140, 230, 90, 0.5)', animated: true },
  { id: 'glitch-sunset', label: 'Глитч закат', value: '#ff4d6d', glow: 'rgba(255, 90, 110, 0.5)', animated: true },
  { id: 'google', label: 'Google', value: '#4285f4', glow: 'rgba(66, 133, 244, 0.58)', animated: true },
];

export const nicknameColorValue = (color: string | null | undefined): string =>
  NICKNAME_COLORS.find(option => option.id === color)?.value ?? NICKNAME_COLORS[0].value;

export const nicknameColorClass = (color: string | null | undefined): string =>
  NICKNAME_COLORS.find(option => option.id === color)?.animated ? `nickname-color-${color}` : '';
