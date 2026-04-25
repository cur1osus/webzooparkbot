import { create } from 'zustand';
import { createCoreSlice } from './slices/coreSlice';
import type { ZooStore } from './types';

export const useZooStore = create<ZooStore>()((...args) => ({
  ...createCoreSlice(...args),
}));

export type { CoreSlice, PersistOptions, ZooStore } from './types';
