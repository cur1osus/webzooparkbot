import { del as idbDel, get as idbGet, set as idbSet } from 'idb-keyval';
import { apiMe, ApiError } from '@/api';
import type { GameState } from '@/types';
import type { CoreSlice, ZooSliceCreator } from '@/store/types';

const IDB_KEY = 'zooparkbot-v9';

/**
 * There is no `persistStateSilently` any more. It POSTed `data_version` to `/api/save`,
 * a field nothing read, and then spent thirty lines reconciling the balances the server
 * echoed back with the ones already on screen. Currencies only ever change as the result
 * of an endpoint the player invoked; that endpoint's response is the update.
 */
export const createCoreSlice: ZooSliceCreator<CoreSlice> = (set, get) => ({
  state: null,
  loading: false,
  error: null,
  errorStatus: null,

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
      if (status === 404) {
        // Not registered yet. `/api/me` has always answered 404 here, and the app has
        // always rendered "Ошибка загрузки" over the registration screen.
        await idbDel(IDB_KEY).catch(() => {});
        set({ loading: false, state: null, error: null, errorStatus: null });
      } else if (status === 403) {
        await idbDel(IDB_KEY).catch(() => {});
        set({ loading: false, state: null, error: err instanceof Error ? err.message : 'Нет доступа', errorStatus: status });
      } else {
        set({ loading: false, error: err instanceof Error ? err.message : 'Ошибка загрузки', errorStatus: status });
      }
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
