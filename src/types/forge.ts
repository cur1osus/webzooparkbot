import type { ForgeItem } from './gameState';

export interface ForgeCreateResponse {
  ok: boolean;
  item: ForgeItem;
  cost_usd: number | null;
  cost_paw: number | null;
  new_usd: number;
  new_paw_coins: number;
}

export interface ForgeUpgradeResponse {
  ok: boolean;
  success: boolean;
  success_pct: number;
  item: ForgeItem;
  cost_usd: number;
  new_usd: number;
}

export interface ForgeMergeResponse {
  ok: boolean;
  new_item: ForgeItem;
  cost_usd: number;
  new_usd: number;
}

export interface ForgeSellResponse {
  ok: boolean;
  earned_usd: number;
  new_usd: number;
}
