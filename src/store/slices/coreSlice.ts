import { del as idbDel, get as idbGet, set as idbSet } from 'idb-keyval';
import { apiMe, apiSave, ApiError } from '@/api';
import type { GameState } from '@/types';
import type { CoreSlice, ZooSliceCreator } from '@/store/types';

const IDB_KEY = 'zooparkbot-v8';

let persistRequestSeq = 0;

export const createCoreSlice: ZooSliceCreator<CoreSlice> = (set, get) => ({
  state: null,
  loading: false,
  error: null,
  errorStatus: null,
  lastSaved: 0,

  loadFromServer: async () => {
    set({ loading: true, error: null, errorStatus: null });
    try {
      const cached = await idbGet<GameState>(IDB_KEY).catch(() => null);
      if (cached && typeof cached.tg_id === 'number' && Array.isArray(cached.animals)) {
        set({ state: cached });
      }

      const gs = await apiMe();
      await idbSet(IDB_KEY, gs).catch(() => {});
      set({ state: gs, loading: false });
    } catch (err) {
      const status = err instanceof ApiError ? err.status : null;
      if (status === 403) {
        await idbDel(IDB_KEY).catch(() => {});
        set({ loading: false, state: null, error: err instanceof Error ? err.message : 'Нет доступа', errorStatus: status });
      } else {
        set({ loading: false, error: err instanceof Error ? err.message : 'Ошибка загрузки', errorStatus: status });
      }
    }
  },

  persistStateSilently: async (options) => {
    const { state } = get();
    const baseState = state;
    const snapshot = options?.snapshot ?? baseState;
    if (!baseState || !snapshot) return;

    const requestSeq = ++persistRequestSeq;
    try {
      const payload = {
        rub: snapshot.rub,
        usd: snapshot.usd,
        paw_coins: snapshot.paw_coins,
        animals: snapshot.animals,
        aviaries: snapshot.aviaries,
        balance_seq: snapshot.balance_seq,
        data_version: snapshot.data_version,
      };
      const result = await apiSave(payload, options?.keepalive ?? false);
      if (!result.ok) return;

      const latestState = get().state ?? baseState;
      if (requestSeq !== persistRequestSeq || latestState.balance_seq > result.balance_seq) {
        return;
      }

      const rubChangedSinceRequest = latestState.rub !== baseState.rub;
      const usdChangedSinceRequest = latestState.usd !== baseState.usd;
      const pawCoinsChangedSinceRequest = latestState.paw_coins !== baseState.paw_coins;
      const nextState: GameState = {
        ...latestState,
        rub: rubChangedSinceRequest ? latestState.rub : result.rub,
        usd: usdChangedSinceRequest ? latestState.usd : result.usd,
        paw_coins: pawCoinsChangedSinceRequest ? latestState.paw_coins : result.paw_coins,
        balance_seq: Math.max(latestState.balance_seq, result.balance_seq),
        data_version: Math.max(latestState.data_version, result.data_version),
      };
      await idbSet(IDB_KEY, nextState).catch(() => {});
      set({ state: nextState, lastSaved: Date.now() });
    } catch {
      // Silent persistence must not block gameplay.
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
});
