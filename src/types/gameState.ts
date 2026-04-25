export interface AnimalState {
  animal_id: string;
  quantity: number;
}

export interface AviaryState {
  aviary_id: string;
  count: number;
}

export interface SickAnimal {
  animal_id: string;
  penalty_rub_per_min: number;
  since: string;
}

export interface ForgeProperty {
  type: string;
  value: number;
  label: string;
  animal_id?: string;
}

export interface ForgeItem {
  id: string;
  name: string;
  icon: string;
  rarity: string;
  level: number;
  properties: ForgeProperty[];
  is_active: boolean;
}

export interface ForgeSet {
  id: string;
  name: string;
  icon: string;
  item_ids: string[];
  is_active: boolean;
}

export interface ClanInfo {
  id: number;
  name: string;
  level: number;
  member_count: number;
  specialty: string | null;
  role: 'owner' | 'member';
}

export interface GameState {
  tg_id: number;
  nickname: string;
  registered_at: string;
  profile_emoji: string | null;
  rub: number;
  usd: number;
  paw_coins: number;
  income_rub_per_min: number;
  expenses_rub_per_min: number;
  animals: AnimalState[];
  aviaries: AviaryState[];
  total_seats: number;
  free_seats: number;
  species_count: number;
  diversity_bonus_per_species: number;
  sick_animals: SickAnimal[];
  pack_animals: PackAnimal[];
  live_animals_count: number;
  localities_count: number;
  season_id: number;
  season_started_at: string;
  forge_items: ForgeItem[];
  forge_sets: ForgeSet[];
  clan: ClanInfo | null;
  season_end: string;
  bonus: 0 | 1;
  balance_seq: number;
  data_version: number;
}
import type { PackAnimal } from './progression';
