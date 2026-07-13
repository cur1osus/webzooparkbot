import type {
  ClanListResponse,
  ClanMembersResponse,
  PublicProfile,
  ReferralResponse,
  TopResponse,
  TransferClaimResponse,
  TransferCreateResponse,
  TransferOut,
} from '@/types';
import { req } from './client';

export const apiGetTop = () => req<TopResponse>('/top');
export const apiGetPublicProfile = (tgId: number) => req<PublicProfile>(`/players/${tgId}/profile`);

export const apiGetClanList = () => req<ClanListResponse>('/clans');
export const apiCreateClan = (name: string) =>
  req<{ ok: boolean; id: number; message: string; new_usd: number }>('/clans', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
export const apiJoinClan = (clan_id: number) =>
  req<{ ok: boolean; message: string }>('/clans/join', { method: 'POST', body: JSON.stringify({ clan_id }) });
export const apiLeaveClan = () => req<{ ok: boolean; message: string }>('/clans/leave', { method: 'POST' });
export const apiGetClanMembers = () => req<ClanMembersResponse>('/clans/members');

export const apiGetReferrals = () => req<ReferralResponse>('/referrals');

export const apiCreateTransfer = (total_rub: number, max_claims: number) =>
  req<TransferCreateResponse>('/transfers', {
    method: 'POST',
    body: JSON.stringify({ total_rub: Math.floor(total_rub), max_claims }),
  });
export const apiClaimTransfer = (code: string) =>
  req<TransferClaimResponse>(`/transfers/${encodeURIComponent(code)}/claim`, { method: 'POST' });
export const apiGetMyTransfers = () => req<{ transfers: TransferOut[] }>('/transfers');
