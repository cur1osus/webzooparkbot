import { create } from 'zustand';
import { createCoreSlice } from './slices/coreSlice';
import { createShopSlice } from './slices/shopSlice';
import type { ZooStore } from './types';

export const useZooStore = create<ZooStore>()((...args) => ({
  ...createCoreSlice(...args),
  ...createShopSlice(...args),
}));

export type { CoreSlice, PersistOptions, ShopSlice, ZooStore } from './types';
