import { apiBuyAnimal, apiBuyAviary } from '@/api';
import { getAviaryById } from '@/data/aviaries';
import { getAnimalById } from '@/data/animals';
import type { GameState } from '@/types';
import type { ShopSlice, ZooSliceCreator } from '@/store/types';

function applyAviaryToState(state: GameState, aviaryId: string, count: number, rub: number, totalSeats: number, freeSeats: number): Partial<GameState> {
  const existingIdx = state.aviaries.findIndex(a => a.aviary_id === aviaryId);
  const aviaries = existingIdx >= 0
    ? state.aviaries.map((a, i) => i === existingIdx ? { ...a, count } : a)
    : [...state.aviaries, { aviary_id: aviaryId, count }];
  return { rub, aviaries, total_seats: totalSeats, free_seats: freeSeats };
}

function applyAnimalToState(state: GameState, animalId: string, quantity: number, rub: number, freeSeats: number): Partial<GameState> {
  const existingIdx = state.animals.findIndex(a => a.animal_id === animalId);
  const animals = existingIdx >= 0
    ? state.animals.map((a, i) => i === existingIdx ? { ...a, quantity } : a)
    : [...state.animals, { animal_id: animalId, quantity }];
  return { rub, animals, free_seats: freeSeats };
}

export const createShopSlice: ZooSliceCreator<ShopSlice> = (set, get) => ({
  buyAviary: async (aviaryId: string) => {
    const state = get().state;
    if (!state) return null;

    const def = getAviaryById(aviaryId);
    const snapshot = state;

    // Optimistic update
    if (def) {
      const existingAviary = state.aviaries.find(a => a.aviary_id === aviaryId);
      const optimisticCount = (existingAviary?.count ?? 0) + 1;
      set({ state: { ...state, ...applyAviaryToState(state, aviaryId, optimisticCount, state.rub - def.price_rub, state.total_seats + def.seats, state.free_seats + def.seats) } });
    }

    try {
      const res = await apiBuyAviary(aviaryId);
      if (!res.ok) {
        set({ state: snapshot });
        return res;
      }

      const current = get().state ?? snapshot;
      set({ state: { ...current, ...applyAviaryToState(current, aviaryId, res.new_count, res.new_rub, res.new_total_seats, res.new_free_seats) } });
      return res;
    } catch (err) {
      set({ state: snapshot });
      throw err;
    }
  },

  buyAnimal: async (animalId: string, quantity: number) => {
    const state = get().state;
    if (!state) return null;

    const def = getAnimalById(animalId);
    const snapshot = state;

    // Optimistic update
    if (def) {
      const existingAnimal = state.animals.find(a => a.animal_id === animalId);
      const optimisticQty = (existingAnimal?.quantity ?? 0) + quantity;
      set({ state: { ...state, ...applyAnimalToState(state, animalId, optimisticQty, state.rub - def.price_rub * quantity, state.free_seats - quantity) } });
    }

    try {
      const res = await apiBuyAnimal(animalId, quantity);
      if (!res.ok) {
        set({ state: snapshot });
        return res;
      }

      const current = get().state ?? snapshot;
      set({ state: { ...current, ...applyAnimalToState(current, animalId, res.new_quantity, res.new_rub, res.new_free_seats) } });
      return res;
    } catch (err) {
      set({ state: snapshot });
      throw err;
    }
  },
});
