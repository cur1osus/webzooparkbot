import type { AdminGrantResult, AdminOverview, AppConfig, GameState, MaintenancePollStatus, MaintenanceStatus, RegisterResponse } from '@/types';
import { req } from './client';

/**
 * There is no `apiSave`. `POST /api/save` carried one field, `data_version`, which the
 * server stored and handed straight back; currencies have been server-authoritative for
 * far longer. A fresh balance is what `/api/me` returns.
 */
export const apiMe = () => req<GameState>('/me');
export const apiMaintenanceStatus = () => req<MaintenancePollStatus>('/maintenance');
export const apiRegister = (nickname: string, ref_code?: string) =>
  req<RegisterResponse>('/register', { method: 'POST', body: JSON.stringify({ nickname, ref_code }) });
export const apiConfig = () => req<AppConfig>('/config');
export const apiSetNicknameColor = (color: string) =>
  req<{ ok: true; nickname_color: string }>('/profile/nickname-color', {
    method: 'POST',
    body: JSON.stringify({ color }),
  });
export const apiSetProfileAvatar = (avatar: string | null) =>
  req<{ ok: true; profile_emoji: string | null }>('/profile/avatar', {
    method: 'POST',
    body: JSON.stringify({ avatar }),
  });
export const apiBuyNicknameColor = (color: string) =>
  req<{ ok: true; nickname_color: string; new_paw_coins: number }>(`/profile/nickname-colors/${color}`, {
    method: 'POST',
  });
export const apiSetProfileFrame = (frame: string) =>
  req<{ ok: true; profile_frame: string }>('/profile/frame', {
    method: 'POST',
    body: JSON.stringify({ frame }),
  });
export const apiBuyProfileFrame = (frame: string) =>
  req<{ ok: true; profile_frame: string; new_paw_coins: number }>(`/profile/frames/${frame}`, {
    method: 'POST',
  });
export const apiSetProfileWallpaper = (wallpaper: string) =>
  req<{ ok: true; profile_wallpaper: string }>('/profile/wallpaper', {
    method: 'POST',
    body: JSON.stringify({ wallpaper }),
  });
export const apiBuyProfileWallpaper = (wallpaper: string) =>
  req<{ ok: true; profile_wallpaper: string; new_paw_coins: number }>(`/profile/wallpapers/${wallpaper}`, {
    method: 'POST',
  });

export const apiAdminOverview = (search = '') =>
  req<AdminOverview>(`/admin/overview${search ? `?search=${encodeURIComponent(search)}` : ''}`);

export const apiAdminGrant = (telegramId: number, currency: AdminCurrency, amount: number) =>
  req<AdminGrantResult>(`/admin/players/${telegramId}/grant`, {
    method: 'POST',
    body: JSON.stringify({ currency, amount }),
  });

export const apiAdminSetStatus = (telegramId: number, status: 'active' | 'banned') =>
  req<{ ok: true; tg_id: number; status: 'active' | 'banned' }>(`/admin/players/${telegramId}/status`, {
    method: 'POST',
    body: JSON.stringify({ status }),
  });

export const apiAdminCreateAchievement = (payload: {
  title: string;
  description: string;
  audience: 'all' | 'selected';
  player_tg_ids: number[];
  image_data: string;
}) => req<{ ok: true; id: string; image_url: string }>('/admin/achievements', {
  method: 'POST',
  body: JSON.stringify(payload),
});

export const apiAdminDeleteAchievement = (achievementId: string) =>
  req<{ ok: true; id: string }>(`/admin/achievements/${achievementId}`, { method: 'DELETE' });

export const apiAdminGetMaintenance = () => req<MaintenanceStatus>('/admin/maintenance');
export const apiAdminStartMaintenance = (durationMinutes: number, message: string) =>
  req<MaintenanceStatus>('/admin/maintenance', {
    method: 'POST',
    body: JSON.stringify({ duration_minutes: durationMinutes, message }),
  });
export const apiAdminEndMaintenance = () =>
  req<MaintenanceStatus>('/admin/maintenance/end', { method: 'POST' });

export type AdminCurrency = 'rub' | 'usd' | 'paw';
