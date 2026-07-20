import type {
  Animal,
  AssignMatchingLocalityResult,
  AssignLocalityResult,
  BreedResult,
  BuyLocalityResult,
  DevelopmentTrack,
  DonateInfo,
  ExpeditionFinishResponse,
  ExpeditionInfo,
  ExpeditionStartResponse,
  LocalitiesInfo,
  ReleaseAnimalResult,
  UpgradeLocalityResult,
  MerchantBuyResponse,
  MerchantResponse,
  PackInfo,
  PackOpenResult,
} from '@/types';
import { req } from './client';

export const apiGetMerchant = () => req<MerchantResponse>('/merchant/animals');
export const apiBuyFromMerchant = (slot: number) =>
  req<MerchantBuyResponse>(`/merchant/buy/${slot}`, { method: 'POST' });

export const apiGetDonateInfo = () => req<DonateInfo>('/donate/info');
export const apiCreateDonateInvoice = (stars: number) =>
  req<{ invoice_link: string }>('/donate/invoice', { method: 'POST', body: JSON.stringify({ stars }) });

/** Alive animals that are not away on an expedition — the breeding and squad pool. */
export const apiGetAnimals = () => req<{ animals: Animal[] }>('/animals');

export const apiGetPacksInfo = () => req<PackInfo>('/packs/info');
/** `tier` omitted opens the free daily gift; a tier name buys that (unlocked) tier. */
export const apiOpenPack = (tier?: string, quantity = 1) =>
  req<PackOpenResult>('/packs/open', { method: 'POST', body: JSON.stringify({ tier: tier ?? null, quantity }) });

export const apiGetLocalities = () => req<LocalitiesInfo>('/localities');
export const apiBuyLocality = (habitat: string) =>
  req<BuyLocalityResult>('/localities/buy', { method: 'POST', body: JSON.stringify({ habitat }) });
export const apiUpgradeLocality = (localityId: number) =>
  req<UpgradeLocalityResult>('/localities/upgrade', { method: 'POST', body: JSON.stringify({ locality_id: localityId }) });
export const apiUpgradeDevelopment = (kind: DevelopmentTrack) =>
  req<{ ok: boolean; kind: DevelopmentTrack; level: number; next_cost_rub: number | null; new_rub: number }>(
    '/development/upgrade', { method: 'POST', body: JSON.stringify({ kind }) },
  );
export const apiAssignLocality = (animal_id: number, locality_id: number | null) =>
  req<AssignLocalityResult>('/localities/assign', {
    method: 'POST',
    body: JSON.stringify({ animal_id, locality_id }),
  });
export const apiAssignMatchingLocality = (locality_id: number) =>
  req<AssignMatchingLocalityResult>('/localities/assign-matching', {
    method: 'POST',
    body: JSON.stringify({ locality_id }),
  });
/** Permanently remove an animal from the zoo — used to cull the population. Irreversible. */
export const apiReleaseAnimal = (animal_id: number) =>
  req<ReleaseAnimalResult>('/animals/release', {
    method: 'POST',
    body: JSON.stringify({ animal_id }),
  });

export const apiSetAnimalFavorite = (animal_id: number, is_favorite: boolean) =>
  req<{ ok: boolean; animal_id: number; is_favorite: boolean }>('/animals/favorite', {
    method: 'POST',
    body: JSON.stringify({ animal_id, is_favorite }),
  });

export const apiGetExpeditions = () => req<ExpeditionInfo>('/expeditions');
/** `depth` picks how hard the raid is; the habitat caps it (see `ExpeditionLocality.max_depth`). */
export const apiStartExpedition = (locality_id: number, animal_ids: number[], depth = 1) =>
  req<ExpeditionStartResponse>('/expeditions/start', {
    method: 'POST',
    body: JSON.stringify({ locality_id, animal_ids, depth }),
  });
/** Omitting the id resolves the oldest raid that has landed. */
export const apiFinishExpedition = (expedition_id?: number) =>
  req<ExpeditionFinishResponse>('/expeditions/finish', {
    method: 'POST',
    body: JSON.stringify({ expedition_id: expedition_id ?? null }),
  });
export const apiDismissExpedition = (expedition_id?: number) =>
  req<{ ok: boolean }>('/expeditions/dismiss', {
    method: 'POST',
    body: JSON.stringify({ expedition_id: expedition_id ?? null }),
  });

export const apiBreed = (animal_id_1: number, animal_id_2: number) =>
  req<BreedResult>('/breed', { method: 'POST', body: JSON.stringify({ animal_id_1, animal_id_2 }) });
