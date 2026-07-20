import type { ForgeItem } from './gameState';

export type GeneTier = 'low' | 'medium' | 'high';
export type Habitat = 'desert' | 'mountains' | 'forest' | 'fields' | 'antarctica';
export type SpeciesRarity = 'rare' | 'epic' | 'mythic' | 'legendary';
export type PackTier = 'rare' | 'epic' | 'legendary' | 'mythic';
export type AnimalOrigin = 'pack' | 'merchant' | 'breeding' | 'expedition' | 'daily_bonus';

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
 * Species rarity sets the animal's income baseline; genes and current state then refine it.
 */
export interface Animal {
  id: number;
  is_favorite: boolean;
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
  /** Intrinsic income/min (genes + rarity only) — the value breeding is priced from. */
  base_income: number;
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
  /** Total price for one request containing the supported batch sizes. */
  batch_prices: Record<string, number>;
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
  pack_count: number;
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

export interface AssignMatchingLocalityResult {
  ok: boolean;
  assigned_count: number;
  income_rub_per_min: number;
}

export interface ReleaseAnimalResult {
  ok: boolean;
  animal_id: number;
  income_rub_per_min: number;
}

export interface BreedResult {
  ok: boolean;
  success: boolean;
  rate: number;
  animal: Animal | null;
  animals?: Animal[];
  inherited_genes?: InheritedGene[];
  cost_rub?: number;
  new_rub?: number;
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

/**
 * How decisively the fight went. `squad_power / wild_power` picks the grade, so overshoot
 * keeps paying instead of falling off the old binary win/lose cliff.
 */
export type ExpeditionGrade = 'rout' | 'defeat' | 'pyrrhic' | 'victory' | 'confident' | 'dominant';

export type ExpeditionGeneKey = 'survival' | 'reproduction' | 'appearance' | 'size_trait';

/** A gene the squad's surplus power improved on the catch, relative to the beast met. */
export interface ExpeditionGeneUpgrade {
  gene: ExpeditionGeneKey;
  from: GeneTier;
  to: GeneTier;
}

export interface ExpeditionResult {
  outcome: 'victory' | 'defeat';
  grade: ExpeditionGrade;
  grade_label: string;
  /** `squad_power / wild_power`, rounded — what picked the grade. */
  ratio: number;
  squad_power: number;
  /** Already scaled by the wild multiplier and the depth — compare directly against `squad_power`. */
  wild_power: number;
  habitat: Habitat;
  depth: number;
  depth_name: string;
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
  /** Present on a capture; empty when overkill improved nothing. */
  gene_upgrades?: ExpeditionGeneUpgrade[];
  loot?: { rub: number; usd: number };
  /** An artefact the raid turned up. Only on a capture, and rarer the shallower the raid. */
  item?: ForgeItem;
  captured_animal_ids?: number[];
  captured_animals?: Animal[];
  /** First catch, retained for clients released before a dominant win could yield two. */
  captured_animal_id?: number;
  captured_animal?: Animal;
  killed_animal_id?: number | null;
  sick_animal_ids?: number[];
}

export interface ActiveExpedition {
  id: number;
  locality_id: number;
  habitat: Habitat;
  depth: number;
  depth_name: string;
  started_at: string;
  ends_at: string;
  status: 'active' | 'finished';
  animals: Animal[];
  result: ExpeditionResult | null;
}

/** One raid a habitat offers. Deeper means a stronger beast and a better catch. */
export interface ExpeditionDepthOption {
  depth: number;
  name: string;
  minutes: number;
  /** The beast's power band — forecast the grade against this before committing a squad. */
  wild_power_min: number;
  wild_power_max: number;
  wild_power_avg: number;
  rarity_percent: Record<SpeciesRarity, number>;
}

export interface ExpeditionLocality {
  id: number;
  habitat: Habitat;
  /** A raid is already out here, or its result has not been read yet. */
  busy: boolean;
  max_depth: number;
  depths: ExpeditionDepthOption[];
}

export interface ExpeditionInfo {
  /** One raid per locality may be in flight, so this is a list. */
  expeditions: ActiveExpedition[];
  /** First expedition, retained for clients released before parallel raids. */
  active: ActiveExpedition | null;
  localities: ExpeditionLocality[];
  available_animals: Animal[];
  expedition_minutes: Record<Habitat, number>;
  squad_min: number;
  squad_max: number;
  depth_min: number;
  depth_max: number;
  /** Squad power multiplier from forge items and the corps track — the server applies this. */
  power_multiplier: number;
  expedition_level: number;
}

export interface ExpeditionStartResponse {
  ok: boolean;
  expedition: ActiveExpedition;
  squad_power: number;
}

export interface ExpeditionFinishResponse {
  ok: boolean;
  result: ExpeditionResult;
}
