import type {
  AppConfig,
  BankInfo,
  BonusResult,
  BreedResult,
  BuyAnimalResponse,
  BuyAviaryResponse,
  BuyLocalityResult,
  ClanListResponse,
  CocktailGuessResult,
  CureResponse,
  DonateInfo,
  ExchangeResult,
  ExpeditionInfo,
  ExpeditionFinishResponse,
  ExpeditionStartResponse,
  ForgeCreateResponse,
  ForgeSet,
  ForgeMergeResponse,
  ForgeUpgradeResponse,
  ForgeSellResponse,
  ForgeItem,
  GameState,
  LocalitiesInfo,
  MerchantBuyResponse,
  MpGame,
  MerchantResponse,
  MpGameResponse,
  PackInfo,
  PackOpenResult,
  ReferralResponse,
  RegisterResponse,
  SaveResponse,
  SoloGameResult,
  SoloStats,
  TopResponse,
  TransferOut,
} from './types';
import { getRawTelegramInitData } from './tmaEnv';

const API = '/api';
const DEV_KEY = 'dev_user_id';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// ─── Dev mode helpers ─────────────────────────────────────────────────────────

export function isDevMode(): boolean {
  return Boolean(localStorage.getItem(DEV_KEY));
}

export function setDevUserId(id: string) {
  localStorage.setItem(DEV_KEY, id);
}

export function clearDevUserId() {
  localStorage.removeItem(DEV_KEY);
}

// ─── Headers ──────────────────────────────────────────────────────────────────

export function getHeaders(): HeadersInit {
  const initData = getRawTelegramInitData() ?? '';

  if (initData) {
    return { 'Content-Type': 'application/json', 'X-Init-Data': initData };
  }

  const devId = localStorage.getItem(DEV_KEY) ?? '';
  if (devId) {
    return { 'Content-Type': 'application/json', 'X-Dev-User-Id': devId };
  }

  return { 'Content-Type': 'application/json', 'X-Init-Data': '' };
}

// ─── Base request ─────────────────────────────────────────────────────────────

async function req<T>(path: string, init?: RequestInit, keepalive = false): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    keepalive,
    headers: { ...getHeaders(), ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, (err as { detail?: string }).detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

// ─── Core ─────────────────────────────────────────────────────────────────────

export const apiMe = () => req<GameState>('/me');
export const apiSave = (payload: object, keepalive = false) =>
  req<SaveResponse>('/save', { method: 'POST', body: JSON.stringify(payload) }, keepalive);
export const apiRegister = (nickname: string) =>
  req<RegisterResponse>('/register', { method: 'POST', body: JSON.stringify({ nickname }) });
export const apiConfig = () => req<AppConfig>('/config');

// ─── Shop ─────────────────────────────────────────────────────────────────────

export const apiBuyAnimal = (animal_id: string, quantity: number) =>
  req<BuyAnimalResponse>('/buy_animal', { method: 'POST', body: JSON.stringify({ animal_id, quantity }) });
export const apiBuyAviary = (aviary_id: string) =>
  req<BuyAviaryResponse>('/buy_aviary', { method: 'POST', body: JSON.stringify({ aviary_id }) });

// ─── Bank ─────────────────────────────────────────────────────────────────────

export const apiGetBank = () => req<BankInfo>('/bank');
export const apiExchange = (from: 'rub' | 'usd', amount: number) =>
  req<ExchangeResult>('/bank/exchange', { method: 'POST', body: JSON.stringify({ from, amount }) });

// ─── Bonus ────────────────────────────────────────────────────────────────────

export const apiClaimBonus = () =>
  req<BonusResult>('/claim_bonus', { method: 'POST' });

// ─── Cure ─────────────────────────────────────────────────────────────────────

export const apiCureAnimal = (animal_id: string) =>
  req<CureResponse>('/cure_animal', { method: 'POST', body: JSON.stringify({ animal_id }) });

// ─── Merchant ─────────────────────────────────────────────────────────────────

export const apiGetMerchant = () => req<MerchantResponse>('/merchant/animals');
export const apiBuyFromMerchant = (slot: 1 | 2 | 3) =>
  req<MerchantBuyResponse>(`/merchant/buy${slot}`, { method: 'POST' });

// ─── Forge ────────────────────────────────────────────────────────────────────

export const apiGetForgeItems = () => req<{ items: ForgeItem[] }>('/forge/items');
export const apiGetForgeSets = () => req<{ sets: ForgeSet[] }>('/forge/sets');
export const apiForgeCreate = (currency: 'usd' | 'paw') =>
  req<ForgeCreateResponse>('/forge/create', { method: 'POST', body: JSON.stringify({ currency }) });
export const apiForgeCreateSet = (item_ids: string[] = []) =>
  req<{ ok: boolean; set: ForgeSet }>('/forge/sets/create', { method: 'POST', body: JSON.stringify({ item_ids }) });
export const apiForgeUpdateSet = (set_id: string, item_ids: string[]) =>
  req<{ ok: boolean; set: ForgeSet }>('/forge/sets/update', { method: 'POST', body: JSON.stringify({ set_id, item_ids }) });
export const apiForgeDeleteSet = (set_id: string) =>
  req<{ ok: boolean }>('/forge/sets/delete', { method: 'POST', body: JSON.stringify({ set_id }) });
export const apiForgeApplySet = (set_id: string) =>
  req<{ ok: boolean }>('/forge/sets/apply', { method: 'POST', body: JSON.stringify({ set_id }) });
export const apiForgeUpgrade = (item_id: string) =>
  req<ForgeUpgradeResponse>('/forge/upgrade', { method: 'POST', body: JSON.stringify({ item_id }) });
export const apiForgeMerge = (item_id1: string, item_id2: string) =>
  req<ForgeMergeResponse>('/forge/merge', { method: 'POST', body: JSON.stringify({ item_id1, item_id2 }) });
export const apiForgeSell = (item_id: string) =>
  req<ForgeSellResponse>('/forge/sell', { method: 'POST', body: JSON.stringify({ item_id }) });
export const apiForgeActivate = (item_id: string) =>
  req<{ ok: boolean; is_active: boolean }>('/forge/activate', { method: 'POST', body: JSON.stringify({ set_id: item_id }) });

// ─── Leaderboard ─────────────────────────────────────────────────────────────

export const apiGetTop = () => req<TopResponse>('/top');

// ─── Clan ─────────────────────────────────────────────────────────────────────

export const apiGetClanList = () => req<ClanListResponse>('/clan/list');
export const apiCreateClan = (name: string, spec?: string) =>
  req<{ ok: boolean; message: string }>('/clan/create', { method: 'POST', body: JSON.stringify({ name, spec }) });
export const apiJoinClan = (clan_id: number) =>
  req<{ ok: boolean; message: string }>(`/clan/request`, { method: 'POST', body: JSON.stringify({ clan_id }) });
export const apiLeaveClan = () =>
  req<{ ok: boolean; message: string }>('/clan/leave', { method: 'POST' });

// ─── Referrals ───────────────────────────────────────────────────────────────

export const apiGetReferrals = () => req<ReferralResponse>('/referrals');

// ─── Transfers ───────────────────────────────────────────────────────────────

export const apiCreateTransfer = (total_rub: number, max_claims: number) =>
  req<{ key: string }>('/transfers/create', { method: 'POST', body: JSON.stringify({ total_rub, max_claims }) });
export const apiGetMyTransfers = () =>
  req<{ transfers: TransferOut[] }>('/my-transfers');

// ─── Multiplayer games ────────────────────────────────────────────────────────

export const apiGetOpenGames = () => req<MpGameResponse>('/mpgame/open');
export const apiCreateMpGame = (game_type: string, bet_rub: number) =>
  req<{ ok: boolean; game: MpGame }>('/mpgame/create', { method: 'POST', body: JSON.stringify({ game_type, bet_rub }) });
export const apiJoinMpGame = (game_id: number) =>
  req<{ ok: boolean; game: MpGame }>(`/mpgame/${game_id}/join`, { method: 'POST' });
export const apiThrowMpGame = (game_id: number) =>
  req<{ ok: boolean; game: MpGame }>(`/mpgame/${game_id}/throw`, { method: 'POST' });

// ─── Solo game ────────────────────────────────────────────────────────────────

export const apiStartSoloGame = (game_type: string, bet_rub: number) =>
  req<SoloGameResult>
  ('/start_solo_game', { method: 'POST', body: JSON.stringify({ game_type, bet_rub }) });
export const apiGetSoloStats = () => req<SoloStats>('/get_solo_stats');

// ─── Donate ───────────────────────────────────────────────────────────────────

export const apiGetDonateInfo = () => req<DonateInfo>('/donate/info');
export const apiCreateDonateInvoice = (stars: number) =>
  req<{ invoice_link: string }>('/donate/invoice', { method: 'POST', body: JSON.stringify({ stars }) });

// ─── Cocktail game ────────────────────────────────────────────────────────────

export const apiCocktailGuess = (fruits: string[]) =>
  req<CocktailGuessResult>('/cocktail/guess', { method: 'POST', body: JSON.stringify({ fruits }) });

// ─── Packs ────────────────────────────────────────────────────────────────────

export const apiGetPacksInfo = () => req<PackInfo>('/packs/info');
export const apiOpenPack     = () => req<PackOpenResult>('/packs/open', { method: 'POST' });

// ─── Localities ───────────────────────────────────────────────────────────────

export const apiGetLocalities  = () => req<LocalitiesInfo>('/localities');
export const apiBuyLocality    = (habitat: string) =>
  req<BuyLocalityResult>('/localities/buy', { method: 'POST', body: JSON.stringify({ habitat }) });
export const apiAssignLocality = (animal_id: number, locality_id: number | null) =>
  req<{ ok: boolean }>('/localities/assign', { method: 'POST', body: JSON.stringify({ animal_id, locality_id }) });

// ─── Expeditions ─────────────────────────────────────────────────────────────

export const apiGetExpeditions = () => req<ExpeditionInfo>('/expeditions');
export const apiStartExpedition = (locality_id: number, animal_ids: number[]) =>
  req<ExpeditionStartResponse>('/expeditions/start', { method: 'POST', body: JSON.stringify({ locality_id, animal_ids }) });
export const apiFinishExpedition = () =>
  req<ExpeditionFinishResponse>('/expeditions/finish', { method: 'POST' });
export const apiDismissExpedition = () =>
  req<{ ok: boolean }>('/expeditions/dismiss', { method: 'POST' });

// ─── Breeding ─────────────────────────────────────────────────────────────────

export const apiBreed = (animal_id_1: number, animal_id_2: number) =>
  req<BreedResult>('/breed', { method: 'POST', body: JSON.stringify({ animal_id_1, animal_id_2 }) });
