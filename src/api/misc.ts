import type {
  BreedResult,
  BuyLocalityResult,
  DonateInfo,
  ExpeditionFinishResponse,
  ExpeditionInfo,
  ExpeditionStartResponse,
  LocalitiesInfo,
  MerchantBuyResponse,
  MerchantResponse,
  PackInfo,
  PackOpenResult,
} from '@/types';
import { req } from './client';

export const apiGetMerchant = () => req<MerchantResponse>('/merchant/animals');
export const apiBuyFromMerchant = (slot: 1 | 2 | 3) =>
  req<MerchantBuyResponse>(`/merchant/buy${slot}`, { method: 'POST' });
export const apiGetDonateInfo = () => req<DonateInfo>('/donate/info');
export const apiCreateDonateInvoice = (stars: number) =>
  req<{ invoice_link: string }>('/donate/invoice', { method: 'POST', body: JSON.stringify({ stars }) });
export const apiGetPacksInfo = () => req<PackInfo>('/packs/info');
export const apiOpenPack = () => req<PackOpenResult>('/packs/open', { method: 'POST' });
export const apiGetLocalities = () => req<LocalitiesInfo>('/localities');
export const apiBuyLocality = (habitat: string) =>
  req<BuyLocalityResult>('/localities/buy', { method: 'POST', body: JSON.stringify({ habitat }) });
export const apiAssignLocality = (animal_id: number, locality_id: number | null) =>
  req<{ ok: boolean }>('/localities/assign', { method: 'POST', body: JSON.stringify({ animal_id, locality_id }) });
export const apiGetExpeditions = () => req<ExpeditionInfo>('/expeditions');
export const apiStartExpedition = (locality_id: number, animal_ids: number[]) =>
  req<ExpeditionStartResponse>('/expeditions/start', { method: 'POST', body: JSON.stringify({ locality_id, animal_ids }) });
export const apiFinishExpedition = () => req<ExpeditionFinishResponse>('/expeditions/finish', { method: 'POST' });
export const apiDismissExpedition = () => req<{ ok: boolean }>('/expeditions/dismiss', { method: 'POST' });
export const apiBreed = (animal_id_1: number, animal_id_2: number) =>
  req<BreedResult>('/breed', { method: 'POST', body: JSON.stringify({ animal_id_1, animal_id_2 }) });
