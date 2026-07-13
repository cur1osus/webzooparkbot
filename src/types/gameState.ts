import type { Animal } from './progression';

export interface Achievement {
  id: string;
  title: string;
  description: string;
  value: number;
  target: number;
  completed: boolean;
}

/** Which effect an item property has. Every one of these is read somewhere on the server. */
export type PropertyKind =
  | 'income_total'
  | 'income_species'
  | 'discount_upkeep'
  | 'discount_packs'
  | 'discount_locality'
  | 'discount_bank'
  | 'duel_moves'
  | 'duel_bonus'
  | 'bonus_rerolls';

export interface ItemProperty {
  kind: PropertyKind;
  value: number;
  /** Set only for the per-species kinds. */
  species_code: string | null;
  label: string;
  unit: 'percent_bonus' | 'percent_discount' | 'flat';
}

export type ItemRarity = 'common' | 'rare' | 'epic' | 'mythical' | 'legendary';

export interface ForgeItem {
  id: string;
  name: string;
  icon: string;
  rarity: ItemRarity;
  level: number;
  is_active: boolean;
  /** Dollars this item sells back for at its current rarity and level. */
  sell_price_usd: number;
  properties: ItemProperty[];
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
  role: 'owner' | 'member';
}

export interface GameState {
  tg_id: number;
  nickname: string;
  nickname_color: NicknameColor;
  nickname_colors: NicknameColorOption[];
  profile_frame: ProfileFrame;
  profile_frames: ProfileFrameOption[];
  profile_wallpaper: ProfileWallpaper;
  profile_wallpapers: ProfileWallpaperOption[];
  registered_at: string;
  profile_emoji: string | null;

  rub: number;
  usd: number;
  paw_coins: number;
  vet_level: number;
  genetics_level: number;

  income_rub_per_min: number;
  /** Upkeep grows with the size of the zoo. Net income is income minus this. */
  upkeep_rub_per_min: number;
  income_synced_at: string;

  animals: Animal[];
  sick_animal_ids: number[];
  live_animals_count: number;
  localities_count: number;

  species_count: number;
  /** exp(Shannon entropy) over the zoo. What the diversity bonus is actually computed from. */
  effective_species_count: number;
  /** The bonus the server applied, in percent. Not a number the client invents. */
  diversity_bonus_percent: number;
  diversity_bonus_percent_per_species: number;

  season_id: number;
  season_started_at: string;
  season_ends_at: string;

  items: ForgeItem[];
  item_sets: ForgeSet[];
  clan: ClanInfo | null;
  achievements: Achievement[];
}

export type NicknameColor = 'ivory' | 'gold' | 'jade' | 'lagoon' | 'orchid' | 'coral' | 'aurora' | 'embers' | 'spectrum' | 'neon' | 'wave' | 'wave-azure' | 'wave-violet' | 'glitch' | 'glitch-aqua' | 'glitch-lime' | 'glitch-sunset' | 'google';
export type NicknameColorRarity = 'standard' | 'rare' | 'legendary';

export interface NicknameColorOption {
  id: NicknameColor;
  price_paw: number;
  animated: boolean;
  rarity: NicknameColorRarity;
  owned: boolean;
}

export type ProfileFrame = 'none' | 'brass' | 'jade' | 'coral' | 'azure' | 'aurora' | 'ember' | 'spectrum' | 'royal';

export interface ProfileFrameOption {
  id: ProfileFrame;
  price_paw: number;
  animated: boolean;
  rarity: NicknameColorRarity;
  owned: boolean;
}

export type ProfileWallpaper = 'none' | 'dusk' | 'sunrise' | 'meadow' | 'ocean' | 'bubbles' | 'grid' | 'paws' | 'stars';

export interface ProfileWallpaperOption {
  id: ProfileWallpaper;
  price_paw: number;
  animated: boolean;
  rarity: NicknameColorRarity;
  owned: boolean;
}
