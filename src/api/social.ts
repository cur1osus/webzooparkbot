import type { ClanListResponse, ClanMembersResponse, ReferralResponse, TopResponse, TransferOut } from '@/types';
import { req } from './client';

export const apiGetTop = () => req<TopResponse>('/top');
export const apiGetClanList = () => req<ClanListResponse>('/clan/list');
export const apiCreateClan = (name: string, spec?: string) =>
  req<{ ok: boolean; message: string }>('/clan/create', { method: 'POST', body: JSON.stringify({ name, spec }) });
export const apiJoinClan = (clan_id: number) =>
  req<{ ok: boolean; message: string }>('/clan/request', { method: 'POST', body: JSON.stringify({ clan_id }) });
export const apiLeaveClan = () => req<{ ok: boolean; message: string }>('/clan/leave', { method: 'POST' });
export const apiGetClanMembers = () => req<ClanMembersResponse>('/clan/members');
export const apiGetReferrals = () => req<ReferralResponse>('/referrals');
export const apiCreateTransfer = (total_rub: number, max_claims: number) =>
  req<{ key: string }>('/transfers/create', { method: 'POST', body: JSON.stringify({ total_rub, max_claims }) });
export const apiGetMyTransfers = () => req<{ transfers: TransferOut[] }>('/my-transfers');
