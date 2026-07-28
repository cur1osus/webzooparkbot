import type {
  Animal,
  AssignMatchingLocalityResult,
  AssignLocalityResult,
  BreedResult,
  BreedingAnimal,
  BuyLocalityResult,
  DevelopmentTrack,
  DonateInfo,
  ExpeditionFinishResponse,
  ExpeditionInfo,
  ExpeditionStartResponse,
  Habitat,
  LocalityAnimal,
  LocalitiesInfo,
  ReleaseAnimalResult,
  ReleaseAnimalsResult,
  UpgradeLocalityResult,
  MerchantBuyResponse,
  MerchantResponse,
  PackInfo,
  PackOpenResult,
} from '@/types';
import { req } from './client';
import type { ForecastAnimal } from '@/lib/incomeForecast';

export const apiGetMerchant = () => req<MerchantResponse>('/merchant/animals');
export const apiBuyFromMerchant = (slot: number) =>
  req<MerchantBuyResponse>(`/merchant/buy/${slot}`, { method: 'POST' });

export const apiGetDonateInfo = () => req<DonateInfo>('/donate/info');
export const apiCreateDonateInvoice = (stars: number) =>
  req<{ invoice_link: string }>('/donate/invoice', { method: 'POST', body: JSON.stringify({ stars }) });

/** Alive animals that are not away on an expedition — the breeding and squad pool. */
export const apiGetAnimals = () => req<{ animals: Animal[] }>('/animals');
export const apiGetZooAnimals = (offset = 0, limit = 120, sort = 'new') =>
  req<{ animals: Animal[]; total: number; next_offset: number | null }>(
    `/zoo/animals?offset=${offset}&limit=${limit}&sort=${encodeURIComponent(sort)}`,
  );
export const apiGetAnimalForecast = () => req<{ animals: ForecastAnimal[]; average_lifespan_ms: number | null }>('/zoo/forecast');
/** Full passport fields are loaded only for the one animal the player opens. */
export const apiGetAnimal = (animalId: number) => req<{ animal: Animal }>(`/animals/${animalId}`);
/** Compact list of ready animals from species that already have a ready partner. */
export const apiGetBreedingAnimals = () => req<{ animals: BreedingAnimal[] }>('/breeding/animals');
export const apiGetBreedingAnimalsPage = (params: {
  offset?: number;
  limit?: number;
  sort?: string;
  query?: string;
  speciesCode?: string | null;
  excludeId?: number | null;
}) => {
  const search = new URLSearchParams({
    offset: String(params.offset ?? 0),
    limit: String(params.limit ?? 120),
    sort: params.sort ?? 'new',
  });
  if (params.query) search.set('query', params.query);
  if (params.speciesCode) search.set('species_code', params.speciesCode);
  if (params.excludeId) search.set('exclude_id', String(params.excludeId));
  return req<{ animals: BreedingAnimal[]; total: number; next_offset: number | null }>(`/breeding/animals/page?${search}`);
};

export const apiGetPacksInfo = () => req<PackInfo>('/packs/info');
/** `tier` omitted opens the free daily gift; a tier name buys that (unlocked) tier. */
export const apiOpenPack = (tier?: string, quantity = 1) =>
  req<PackOpenResult>('/packs/open', { method: 'POST', body: JSON.stringify({ tier: tier ?? null, quantity }) });

/** Constant-size locality totals; animal rows are fetched per bucket only when opened. */
export const apiGetLocalities = () => req<LocalitiesInfo>('/localities/summary');
export const apiGetLocalityAnimalsPage = (params: {
  localityId?: number | null;
  offset?: number;
  limit?: number;
  query?: string;
  preferredHabitat?: Habitat | null;
}) => {
  const search = new URLSearchParams({
    offset: String(params.offset ?? 0),
    limit: String(params.limit ?? 120),
  });
  if (params.localityId) search.set('locality_id', String(params.localityId));
  if (params.query) search.set('query', params.query);
  if (params.preferredHabitat) search.set('preferred_habitat', params.preferredHabitat);
  return req<{ animals: LocalityAnimal[]; total: number; next_offset: number | null }>(
    `/localities/animals/page?${search}`,
  );
};
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
export const apiReleaseAnimals = (animal_ids: number[]) =>
  req<ReleaseAnimalsResult>('/animals/release-batch', {
    method: 'POST',
    body: JSON.stringify({ animal_ids }),
  });

export const apiSetAnimalFavorite = (animal_id: number, is_favorite: boolean) =>
  req<{ ok: boolean; animal_id: number; is_favorite: boolean }>('/animals/favorite', {
    method: 'POST',
    body: JSON.stringify({ animal_id, is_favorite }),
  });

export const apiGetExpeditions = () => req<ExpeditionInfo>('/expeditions');
export const apiGetExpeditionAnimalsPage = (offset = 0, limit = 120, query = '') => {
  const search = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (query) search.set('query', query);
  return req<{ animals: import('@/types').ExpeditionAnimal[]; total: number; next_offset: number | null }>(
    `/expeditions/animals/page?${search}`,
  );
};
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
