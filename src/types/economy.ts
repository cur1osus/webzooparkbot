import type { Animal, GeneTier, Habitat, SpeciesRarity } from './progression';

export interface RatePoint {
  period: number;
  rate: number;
}

/**
 * The bank is one-way: rubles buy dollars, and there is no way back. That is why a rate
 * this volatile is safe to publish — see `api/app/zoopark/economy.py`.
 */
export interface BankInfo {
  /** What this player pays per dollar, after their `discount_bank` items. */
  rate_rub_per_usd: number;
  /** The published rate, before those items. */
  base_rate_rub_per_usd: number;
  fee_percent: number;
  referral_percent: number;
  min_exchange_rub: number;
  next_update_in: number;
  treasury_usd: number;
  history: RatePoint[];
}

export interface ExchangeResult {
  ok: boolean;
  spent_rub: number;
  received_usd: number;
  fee_usd: number;
  referrer_usd: number;
  rate_rub_per_usd: number;
  new_rub: number;
  new_usd: number;
}

export type BonusCurrency = 'rub' | 'usd' | 'paw' | 'animal' | 'locality';

/** Generated and stored server-side, so a reroll cannot be replayed. */
export interface BonusOffer {
  currency: BonusCurrency;
  amount: number;
  reward_code?: string | null;
  reward_name?: string | null;
  reward_emoji?: string | null;
  claimed: boolean;
  rerolls_left: number;
}

export interface BonusClaimResult {
  ok: boolean;
  currency: BonusCurrency;
  amount: number;
  reward_code?: string | null;
  reward_name?: string | null;
  reward_emoji?: string | null;
  new_rub?: number;
  new_usd?: number;
  new_paw_coins?: number;
}

export interface CureResponse {
  ok: boolean;
  cost_usd: number;
  new_usd: number;
  income_rub_per_min: number;
}

export interface CureAllResponse extends CureResponse {
  cured_count: number;
}

export interface MerchantOffer {
  slot: number;
  species_code: string;
  species_name: string;
  species_emoji: string;
  species_rarity: SpeciesRarity;
  survival: GeneTier;
  reproduction: GeneTier;
  appearance: GeneTier;
  size_trait: GeneTier;
  habitat: Habitat;
  list_price: number;
  discount_pct: number;
  final_price: number;
  bought: boolean;
}

export interface MerchantResponse {
  animals: MerchantOffer[];
  refreshes_at: string;
}

export interface MerchantBuyResponse {
  ok: boolean;
  price_paid: number;
  new_rub: number;
  animal: Animal;
}
