export type GeneTier = 'low' | 'medium' | 'high';
export type Habitat = 'desert' | 'mountains' | 'forest' | 'fields' | 'antarctica';

export interface PackAnimal {
  id: number;
  animal_info_id?: number;
  survival: GeneTier;
  reproduction: GeneTier;
  appearance: GeneTier;
  size_trait: GeneTier;
  habitat: Habitat;
  source?: 'pack' | 'breeding' | 'expedition' | 'merchant' | string;
  acquired_at: string;
  dies_at: string | null;
  locality_id: number | null;
  can_breed: boolean;
  income: number;
  habitat_bonus: boolean;
}

export interface PackInfo {
  packs_today: number;
  free_available: boolean;
  next_price: number;
  animals: PackAnimal[];
}

export interface Locality {
  id: number;
  habitat: Habitat;
  animals: PackAnimal[];
}

export interface LocalitiesInfo {
  localities: Locality[];
  unassigned: PackAnimal[];
  next_price: number | null;
  habitats_taken: Habitat[];
}

export interface BuyLocalityResult {
  ok: boolean;
  id: number;
  habitat: Habitat;
  price_paid: number;
  new_rub: number;
}

export interface BreedResult {
  ok: boolean;
  success: boolean;
  rate: number;
  animal: PackAnimal | null;
}

export interface PackOpenResult {
  ok: boolean;
  price_paid: number;
  new_rub: number;
  packs_today: number;
  next_price: number;
  animal: PackAnimal;
}

export interface ExpeditionResult {
  outcome: 'victory' | 'defeat';
  squad_power: number;
  wild_power: number;
  wild: {
    survival: GeneTier;
    reproduction: GeneTier;
    appearance: GeneTier;
    size_trait: GeneTier;
    habitat: Habitat;
  };
  reward_animal_id?: number;
  captured_animal?: PackAnimal;
  killed_id?: number;
}

export interface ActiveExpedition {
  id: number;
  habitat: Habitat;
  started_at: string;
  ends_at: string;
  status: 'active' | 'finished';
  animals: PackAnimal[];
  result: ExpeditionResult | null;
}

export interface ExpeditionInfo {
  active: ActiveExpedition | null;
  localities: Array<{ id: number; habitat: Habitat }>;
  available_animals: PackAnimal[];
  expedition_minutes: Record<Habitat, number>;
}

export interface ExpeditionStartResponse {
  ok: boolean;
  expedition: ActiveExpedition;
}

export interface ExpeditionFinishResponse {
  ok: boolean;
  result: ExpeditionResult;
}
