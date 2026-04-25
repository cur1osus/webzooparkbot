import { describe, expect, it } from 'vitest';
import type { GameState } from '@/types';
import { calculateLiveRubBalance } from './useLiveGameState';

const baseState: GameState = {
  tg_id: 1,
  nickname: 'test',
  registered_at: '2026-01-01T00:00:00.000Z',
  profile_emoji: null,
  rub: 100,
  usd: 0,
  paw_coins: 0,
  income_rub_per_min: 30,
  expenses_rub_per_min: 10,
  animals: [],
  aviaries: [],
  total_seats: 0,
  free_seats: 0,
  species_count: 0,
  diversity_bonus_per_species: 0,
  sick_animals: [],
  pack_animals: [],
  live_animals_count: 0,
  localities_count: 0,
  season_id: 1,
  season_started_at: '2026-12-01T00:00:00.000Z',
  forge_items: [],
  forge_sets: [],
  clan: null,
  season_end: '2026-12-31T00:00:00.000Z',
  bonus: 0,
  balance_seq: 1,
  data_version: 1,
};

describe('calculateLiveRubBalance', () => {
  it('adds net income for visible elapsed time', () => {
    expect(calculateLiveRubBalance(baseState, 180_000)).toBe(160);
  });

  it('does not allow negative displayed balance', () => {
    expect(calculateLiveRubBalance({ ...baseState, rub: 5, income_rub_per_min: 0, expenses_rub_per_min: 60 }, 60_000)).toBe(0);
  });
});
