import type { PropertyKind } from '@/types';

/**
 * Icons only. The human-readable label comes from the server, which is also the only
 * place that knows what each property does — see `ITEM_PROPERTIES` in `catalog.py`.
 */
export const PROPERTY_ICON: Record<PropertyKind, string> = {
  income_total: '📈',
  income_species: '🐾',
  discount_upkeep: '🧾',
  discount_packs: '📉',
  discount_locality: '🌍',
  discount_bank: '🔄',
  bonus_rerolls: '🎁',
  expedition_power: '🧭',
};

export const PROPERTY_SHORT: Record<PropertyKind, string> = {
  income_total: 'Общий доход',
  income_species: 'Доход вида',
  discount_upkeep: 'Содержание',
  discount_packs: 'Скидка на паки',
  discount_locality: 'Местности',
  discount_bank: 'Курс банка',
  bonus_rerolls: 'Перебросы',
  expedition_power: 'Сила в экспедиции',
};

/** Paw-coin price of forging an item (the USD price is server-authoritative — it escalates
 *  with lifetime creations and arrives on game state as `forge_create_cost_usd`). */
export const FORGE_CREATE_PAW = 350;

/** `FORGE_UPGRADE_BASE_USD`, mirrored for the upgrade-price preview. */
export const FORGE_UPGRADE_BASE_USD = 5000;
export function forgeUpgradeCostUsd(level: number): number {
  return FORGE_UPGRADE_BASE_USD * (level + 1);
}

/** `FORGE_MERGE_COST_USD`, mirrored: merging two items is a flat fee. */
export const FORGE_MERGE_COST_USD = 100_000;
