import { describe, expect, it } from 'vitest';
import type { GameState } from '@/types';
import { calculateLiveRubBalance, netRubPerMin } from './useLiveGameState';

const baseState: GameState = {
  tg_id: 1,
  is_admin: false,
  maintenance: { active: false, started_at: null, ends_at: null, message: 'Технический перерыв' },
  nickname: 'test',
  nickname_color: 'ivory',
  nickname_colors: [{ id: 'ivory', price_paw: 0, animated: false, rarity: 'standard', owned: true }],
  profile_frame: 'none',
  profile_frames: [{ id: 'none', price_paw: 0, animated: false, rarity: 'standard', owned: true }],
  profile_wallpaper: 'none',
  profile_wallpapers: [{ id: 'none', price_paw: 0, animated: false, rarity: 'standard', owned: true }],
  theme: 'dusk',
  registered_at: '2026-01-01T00:00:00.000Z',
  profile_emoji: null,
  rub: 100,
  usd: 0,
  paw_coins: 0,
  vet_level: 0,
  genetics_level: 0,
  expedition_level: 0,
  income_rub_per_min: 30,
  upkeep_rub_per_min: 10,
  income_synced_at: '2026-01-01T00:00:00.000Z',
  animals: [],
  sick_animal_ids: [],
  live_animals_count: 0,
  localities_count: 0,
  species_count: 0,
  effective_species_count: 0,
  diversity_bonus_percent: 0,
  diversity_bonus_percent_per_species: 1,
  season_id: 1,
  season_started_at: '2026-12-01T00:00:00.000Z',
  season_ends_at: '2026-12-31T00:00:00.000Z',
  items: [],
  active_item_bonuses: [],
  forge_create_cost_usd: 80000,
  item_sets: [],
  clan: null,
  achievements: [],
};

describe('netRubPerMin', () => {
  it('is income minus upkeep', () => {
    expect(netRubPerMin(baseState)).toBe(20);
  });
});

describe('calculateLiveRubBalance', () => {
  it('adds net income for visible elapsed time', () => {
    expect(calculateLiveRubBalance(baseState, 180_000)).toBe(160);
  });

  it('does not allow a negative displayed balance', () => {
    const drowning = { ...baseState, rub: 5, income_rub_per_min: 0, upkeep_rub_per_min: 60 };
    expect(calculateLiveRubBalance(drowning, 60_000)).toBe(0);
  });
});
