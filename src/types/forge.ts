import type { ForgeItem, GameState } from './gameState';

export interface ForgeCreateResponse {
  ok: boolean;
  item: ForgeItem;
  cost_usd: number | null;
  cost_paw: number | null;
  new_usd: number;
  new_paw_coins: number;
  next_cost_usd: number;
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
  earned_paw: number;
  new_usd: number;
  new_paw_coins: number;
  removed_item_id: string;
  was_active: boolean;
  income_rub_per_min?: number;
  upkeep_rub_per_min?: number;
  income_synced_at?: string;
  active_item_bonuses?: GameState['active_item_bonuses'];
}
