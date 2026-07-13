export type GeneTier = 'low' | 'medium' | 'high';
export type Habitat = 'desert' | 'mountains' | 'forest' | 'fields' | 'antarctica';
export type SpeciesRarity = 'rare' | 'epic' | 'mythic' | 'legendary';
export type PackTier = 'rare' | 'epic' | 'legendary' | 'mythic';
export type AnimalOrigin = 'pack' | 'merchant' | 'breeding' | 'expedition';

export interface AnimalIncomeFactor {
  key: string;
  label: string;
  value?: string;
  multiplier: number;
}

export interface AnimalIncomeBreakdown {
  base: number;
  factors: AnimalIncomeFactor[];
  total: number;
}

/**
 * The species is a skin: GDD §3 derives income from genes and habitat only. It carries a
 * name, an emoji and a collection rarity, and nothing else.
 */
export interface Animal {
  id: number;
  /** Individual pet name (Renaissance figure); falls back to species name on old data. */
  name: string;
  species_code: string;
  species_name: string;
  species_emoji: string;
  species_rarity: SpeciesRarity;
  survival: GeneTier;
  reproduction: GeneTier;
  appearance: GeneTier;
  size_trait: GeneTier;
  habitat: Habitat;
  origin: AnimalOrigin;
  acquired_at: string;
  dies_at: string;
  locality_id: number | null;
  is_sick: boolean;
  can_breed: boolean;
  income: number;
  income_breakdown?: AnimalIncomeBreakdown;
  /** Price to cure this animal, in dollars (10 hours of its healthy income). */
  cure_cost_usd: number;
  habitat_bonus: boolean;
  parent_a_id: number | null;
  parent_b_id: number | null;
}

export interface PackTierInfo {
  tier: PackTier;
  price: number;
  /** Unlocked tiers can be bought (and reopened freely); locked ones need the tier below. */
  unlocked: boolean;
  reward_range: PackRewardRange;
}

export interface PackInfo {
  /** The free daily gift (random tier) is still available today. */
  gift_available: boolean;
  /** Drop chance per tier of the free daily gift (whole percents). */
  gift_odds?: { tier: PackTier; percent: number }[];
  tiers: PackTierInfo[];
}

export interface PackRewardRange {
  animals: [number, number];
  rub: [number, number];
  usd: [number, number];
}

export interface PackRewards {
  rub: number;
  usd: number;
}

export interface PackOpenResult {
  ok: boolean;
  tier: PackTier;
  is_gift: boolean;
  price_paid: number;
  new_rub: number;
  new_usd: number;
  gift_available: boolean;
  unlocked_tiers: PackTier[];
  rewards: PackRewards;
  animals: Animal[];
  /** First bundle item, retained for clients released before pack bundles. */
  animal: Animal;
}

export interface Locality {
  id: number;
  habitat: Habitat;
  level: number;
  upkeep_discount_percent: number;
  next_upkeep_discount_percent: number | null;
  upgrade_cost_rub: number | null;
  animals: Animal[];
}

export interface LocalitiesInfo {
  localities: Locality[];
  unassigned: Animal[];
  next_price: number | null;
  habitats_taken: Habitat[];
  max_localities: number;
}

export interface BuyLocalityResult {
  ok: boolean;
  id: number;
  habitat: Habitat;
  price_paid: number;
  new_rub: number;
}

export interface UpgradeLocalityResult {
  ok: boolean;
  id: number;
  level: number;
  upkeep_discount_percent: number;
  next_upkeep_discount_percent: number | null;
  upgrade_cost_rub: number | null;
  new_rub: number;
}

export interface AssignLocalityResult {
  ok: boolean;
  income_rub_per_min: number;
}

export interface BreedResult {
  ok: boolean;
  success: boolean;
  rate: number;
  animal: Animal | null;
  inherited_genes?: InheritedGene[];
}

export type InheritedGeneKey = 'survival' | 'reproduction' | 'appearance' | 'size_trait';
export type InheritanceSource = 'parent_a' | 'parent_b' | 'both';

export interface InheritedGene {
  gene: InheritedGeneKey;
  value: GeneTier;
  source: InheritanceSource;
  source_name: string;
  parent_a_name: string;
  parent_b_name: string;
  parent_a_value: GeneTier;
  parent_b_value: GeneTier;
}

export interface ExpeditionResult {
  outcome: 'victory' | 'defeat';
  squad_power: number;
  /** Already scaled by the wild multiplier — compare it directly against `squad_power`. */
  wild_power: number;
  habitat: Habitat;
  wild: {
    species_code: string;
    species_name: string;
    species_emoji: string;
    species_rarity: SpeciesRarity;
    survival: GeneTier;
    reproduction: GeneTier;
    appearance: GeneTier;
    size_trait: GeneTier;
  };
  captured_animal_id?: number;
  captured_animal?: Animal;
  killed_animal_id?: number | null;
  sick_animal_ids?: number[];
}

export interface ActiveExpedition {
  id: number;
  habitat: Habitat;
  started_at: string;
  ends_at: string;
  status: 'active' | 'finished';
  animals: Animal[];
  result: ExpeditionResult | null;
}

export interface ExpeditionInfo {
  active: ActiveExpedition | null;
  localities: Array<{ id: number; habitat: Habitat }>;
  available_animals: Animal[];
  expedition_minutes: Record<Habitat, number>;
  squad_min: number;
  squad_max: number;
}

export interface ExpeditionStartResponse {
  ok: boolean;
  expedition: ActiveExpedition;
}

export interface ExpeditionFinishResponse {
  ok: boolean;
  result: ExpeditionResult;
}
