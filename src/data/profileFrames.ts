import type { ProfileFrame } from '@/types';

// Catalogue mirror of the server's PROFILE_FRAMES. `value`/`glow` drive the shop button
// accent; the actual ring is painted by the `.profile-frame-<id>` CSS.
export const PROFILE_FRAMES: { id: ProfileFrame; label: string; value: string; glow: string; animated?: boolean }[] = [
  { id: 'none', label: 'Без рамки', value: 'var(--tg-theme-hint-color)', glow: 'transparent' },
  { id: 'brass', label: 'Латунь', value: '#f3b53f', glow: 'rgba(243, 181, 63, 0.5)' },
  { id: 'jade', label: 'Нефрит', value: '#63c268', glow: 'rgba(99, 194, 104, 0.5)' },
  { id: 'coral', label: 'Коралл', value: '#f0837b', glow: 'rgba(240, 131, 123, 0.5)' },
  { id: 'azure', label: 'Лазурь', value: '#56bfdc', glow: 'rgba(86, 191, 220, 0.5)' },
  { id: 'aurora', label: 'Аврора', value: '#2fe0c0', glow: 'rgba(47, 224, 192, 0.55)', animated: true },
  { id: 'ember', label: 'Пламя', value: '#ff7a3d', glow: 'rgba(255, 122, 61, 0.55)', animated: true },
  { id: 'spectrum', label: 'Спектр', value: '#b06bff', glow: 'rgba(176, 107, 255, 0.55)', animated: true },
  { id: 'royal', label: 'Корона', value: '#c9a24b', glow: 'rgba(201, 162, 75, 0.55)', animated: true },
];

export const profileFrameClass = (id: string | null | undefined): string =>
  id && id !== 'none' ? `profile-frame-${id}` : '';
