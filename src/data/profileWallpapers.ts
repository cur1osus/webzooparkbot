import type { ProfileWallpaper } from '@/types';

// Catalogue mirror of the server's PROFILE_WALLPAPERS. Labels and accents come from real
// Telegram NFT gift backdrops — colours scraped by scripts/extract_gift_backdrops.py and
// baked into `.wallpaper-<id>` (backdrop gradient + tiled symbol in the gift's own pattern
// colour). The ids stay stable so ownership survives a re-theme.
export const PROFILE_WALLPAPERS: { id: ProfileWallpaper; label: string; accent: string }[] = [
  { id: 'none', label: 'Без обоев', accent: 'var(--tg-theme-hint-color)' },
  { id: 'dusk', label: 'Аметист', accent: '#b17da5' },
  { id: 'sunrise', label: 'Персиммон', accent: '#e7a75a' },
  { id: 'meadow', label: 'Мятный', accent: '#7ecb82' },
  { id: 'ocean', label: 'Сапфир', accent: '#80a4b8' },
  { id: 'bubbles', label: 'Циан', accent: '#31b5aa' },
  { id: 'grid', label: 'Фанданго', accent: '#e28ab6' },
  { id: 'paws', label: 'Капучино', accent: '#b1907e' },
  { id: 'stars', label: 'Стальной', accent: '#97a2ac' },
];

export const wallpaperClass = (id: string | null | undefined): string =>
  id && id !== 'none' ? `wallpaper-${id}` : '';
