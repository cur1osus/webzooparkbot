import { create } from 'zustand';
import { get as idbGet, set as idbSet, del as idbDel } from 'idb-keyval';
import { apiMe, apiSave, ApiError } from './api';
import type { GameState } from './types';

const IDB_KEY = 'zooparkbot-v8';

interface ZooStore {
  state: GameState | null;
  loading: boolean;
  error: string | null;
  errorStatus: number | null;
  lastSaved: number;

  loadFromServer: () => Promise<void>;
  persistStateSilently: (keepalive?: boolean) => Promise<void>;
  setGameState: (gs: GameState) => void;
  patchState: (patch: Partial<GameState>) => void;
}

export const useZooStore = create<ZooStore>((set, get) => ({
  state: null,
  loading: false,
  error: null,
  errorStatus: null,
  lastSaved: 0,

  loadFromServer: async () => {
    set({ loading: true, error: null, errorStatus: null });
    try {
      // First try IndexedDB cache (only use if it matches ZooPark GameState shape)
      const cached = await idbGet<GameState>(IDB_KEY).catch(() => null);
      if (cached && typeof cached.tg_id === 'number' && Array.isArray(cached.animals)) {
        set({ state: cached });
      }

      // Then fetch from server
      const gs = await apiMe();
      await idbSet(IDB_KEY, gs).catch(() => {});
      set({ state: gs, loading: false });
    } catch (err) {
      const status = err instanceof ApiError ? err.status : null;
      // On 403 (access denied), clear cached state so the stub screen shows
      if (status === 403) {
        await idbDel(IDB_KEY).catch(() => {});
        set({ loading: false, state: null, error: err instanceof Error ? err.message : 'Нет доступа', errorStatus: status });
      } else {
        set({ loading: false, error: err instanceof Error ? err.message : 'Ошибка загрузки', errorStatus: status });
      }
    }
  },

  persistStateSilently: async (keepalive = false) => {
    const { state } = get();
    if (!state) return;
    try {
      const payload = {
        rub: state.rub,
        usd: state.usd,
        paw_coins: state.paw_coins,
        animals: state.animals,
        aviaries: state.aviaries,
        balance_seq: state.balance_seq,
        data_version: state.data_version,
      };
      await apiSave(payload, keepalive);
      await idbSet(IDB_KEY, state).catch(() => {});
      set({ lastSaved: Date.now() });
    } catch {
      // silent
    }
  },

  setGameState: (gs: GameState) => {
    set({ state: gs });
    idbSet(IDB_KEY, gs).catch(() => {});
  },

  patchState: (patch: Partial<GameState>) => {
    const { state } = get();
    if (!state) return;
    const next = { ...state, ...patch };
    set({ state: next });
    idbSet(IDB_KEY, next).catch(() => {});
  },
}));
