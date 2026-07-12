import type { AdminGrantResult, AdminOverview, AppConfig, GameState, RegisterResponse } from '@/types';
import { req } from './client';

/**
 * There is no `apiSave`. `POST /api/save` carried one field, `data_version`, which the
 * server stored and handed straight back; currencies have been server-authoritative for
 * far longer. A fresh balance is what `/api/me` returns.
 */
export const apiMe = () => req<GameState>('/me');
export const apiRegister = (nickname: string, ref_code?: string) =>
  req<RegisterResponse>('/register', { method: 'POST', body: JSON.stringify({ nickname, ref_code }) });
export const apiConfig = () => req<AppConfig>('/config');
export const apiSetNicknameColor = (color: string) =>
  req<{ ok: true; nickname_color: string }>('/profile/nickname-color', {
    method: 'POST',
    body: JSON.stringify({ color }),
  });
export const apiBuyNicknameColor = (color: string) =>
  req<{ ok: true; nickname_color: string; new_paw_coins: number }>(`/profile/nickname-colors/${color}`, {
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

export type AdminCurrency = 'rub' | 'usd' | 'paw';
