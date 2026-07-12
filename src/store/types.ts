import type { StateCreator } from 'zustand';
import type { GameState } from '@/types';

export interface CoreSlice {
  state: GameState | null;
  loading: boolean;
  error: string | null;
  errorStatus: number | null;

  loadFromServer: () => Promise<void>;
  setGameState: (gs: GameState) => void;
  patchState: (patch: Partial<GameState>) => void;
}

export type ZooStore = CoreSlice;
export type ZooSliceCreator<T> = StateCreator<ZooStore, [], [], T>;
