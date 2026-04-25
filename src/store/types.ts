import type { StateCreator } from 'zustand';
import type { BuyAnimalResponse, BuyAviaryResponse, GameState } from '@/types';

export interface PersistOptions {
  keepalive?: boolean;
  snapshot?: GameState;
}

export interface CoreSlice {
  state: GameState | null;
  loading: boolean;
  error: string | null;
  errorStatus: number | null;
  lastSaved: number;

  loadFromServer: () => Promise<void>;
  persistStateSilently: (options?: PersistOptions) => Promise<void>;
  setGameState: (gs: GameState) => void;
  patchState: (patch: Partial<GameState>) => void;
}

export interface ShopSlice {
  buyAviary: (aviaryId: string) => Promise<BuyAviaryResponse | null>;
  buyAnimal: (animalId: string, quantity: number) => Promise<BuyAnimalResponse | null>;
}

export type ZooStore = CoreSlice & ShopSlice;
export type ZooSliceCreator<T> = StateCreator<ZooStore, [], [], T>;
