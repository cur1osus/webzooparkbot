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
  duel_moves: '🎲',
  duel_bonus: '⚡️',
  bonus_rerolls: '🎁',
};

export const PROPERTY_SHORT: Record<PropertyKind, string> = {
  income_total: 'Общий доход',
  income_species: 'Доход вида',
  discount_upkeep: 'Содержание',
  discount_packs: 'Скидка на паки',
  discount_locality: 'Местности',
  discount_bank: 'Курс банка',
  duel_moves: 'Броски в дуэли',
  duel_bonus: 'Счёт в дуэли',
  bonus_rerolls: 'Перебросы',
};

/** Paw-coin price of forging an item (the USD price is server-authoritative — it escalates
 *  with lifetime creations and arrives on game state as `forge_create_cost_usd`). */
export const FORGE_CREATE_PAW = 350;
