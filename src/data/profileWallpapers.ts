import type { ProfileWallpaper } from '@/types';

// Catalogue mirror of the server's PROFILE_WALLPAPERS. The actual fills/patterns are
// original CSS/SVG in `.wallpaper-<id>` (no third-party assets). `accent` tints the shop
// button; `label` is the display name.
export const PROFILE_WALLPAPERS: { id: ProfileWallpaper; label: string; accent: string }[] = [
  { id: 'none', label: 'Без обоев', accent: 'var(--tg-theme-hint-color)' },
  { id: 'dusk', label: 'Сумерки', accent: '#7b4fd0' },
  { id: 'sunrise', label: 'Рассвет', accent: '#ff5c8a' },
  { id: 'meadow', label: 'Луг', accent: '#2fb98a' },
  { id: 'ocean', label: 'Океан', accent: '#2f9fd0' },
  { id: 'bubbles', label: 'Пузыри', accent: '#22b0a2' },
  { id: 'grid', label: 'Сетка', accent: '#52658f' },
  { id: 'paws', label: 'Лапки', accent: '#c47c46' },
  { id: 'stars', label: 'Звёзды', accent: '#6a57c8' },
];

export const wallpaperClass = (id: string | null | undefined): string =>
  id && id !== 'none' ? `wallpaper-${id}` : '';
