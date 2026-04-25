import type { ForgeCreateResponse, ForgeItem, ForgeMergeResponse, ForgeSellResponse, ForgeSet, ForgeUpgradeResponse } from '@/types';
import { req } from './client';

export const apiGetForgeItems = () => req<{ items: ForgeItem[] }>('/forge/items');
export const apiGetForgeSets = () => req<{ sets: ForgeSet[] }>('/forge/sets');
export const apiForgeCreate = (currency: 'usd' | 'paw') =>
  req<ForgeCreateResponse>('/forge/create', { method: 'POST', body: JSON.stringify({ currency }) });
export const apiForgeCreateSet = (item_ids: string[] = []) =>
  req<{ ok: boolean; set: ForgeSet }>('/forge/sets/create', { method: 'POST', body: JSON.stringify({ item_ids }) });
export const apiForgeUpdateSet = (set_id: string, item_ids: string[]) =>
  req<{ ok: boolean; set: ForgeSet }>('/forge/sets/update', { method: 'POST', body: JSON.stringify({ set_id, item_ids }) });
export const apiForgeDeleteSet = (set_id: string) =>
  req<{ ok: boolean }>('/forge/sets/delete', { method: 'POST', body: JSON.stringify({ set_id }) });
export const apiForgeApplySet = (set_id: string) =>
  req<{ ok: boolean }>('/forge/sets/apply', { method: 'POST', body: JSON.stringify({ set_id }) });
export const apiForgeUpgrade = (item_id: string) =>
  req<ForgeUpgradeResponse>('/forge/upgrade', { method: 'POST', body: JSON.stringify({ item_id }) });
export const apiForgeMerge = (item_id1: string, item_id2: string) =>
  req<ForgeMergeResponse>('/forge/merge', { method: 'POST', body: JSON.stringify({ item_id1, item_id2 }) });
export const apiForgeSell = (item_id: string) =>
  req<ForgeSellResponse>('/forge/sell', { method: 'POST', body: JSON.stringify({ item_id }) });
export const apiForgeActivate = (item_id: string) =>
  req<{ ok: boolean; is_active: boolean }>('/forge/activate', { method: 'POST', body: JSON.stringify({ set_id: item_id }) });
