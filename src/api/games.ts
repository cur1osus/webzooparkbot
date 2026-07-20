import type {
  CocktailGuessResult,
  CocktailState,
  DuelActionResponse,
  DuelCancelResponse,
  DuelResponse,
  DuelsResponse,
  DuelResolveResponse,
  SafeGuessResult,
  SafeState,
  SoloBetPercent,
  SoloGameResult,
  SoloStats,
} from '@/types';
import { req } from './client';

export const apiGetOpenDuels = () => req<DuelsResponse>('/duels');
export const apiCreateDuel = (kind: string, stake_rub: number) =>
  req<DuelActionResponse>('/duels', {
    method: 'POST',
    body: JSON.stringify({ kind, stake_rub: Math.floor(stake_rub) }),
  });
export const apiGetDuel = (duel_id: number) =>
  req<DuelResponse>(`/duels/${duel_id}`);
export const apiJoinDuel = (duel_id: number) =>
  req<DuelActionResponse>(`/duels/${duel_id}/join`, { method: 'POST' });
export const apiResolveDuel = (duel_id: number) =>
  req<DuelResolveResponse>(`/duels/${duel_id}/resolve`, { method: 'POST' });
export const apiCancelDuel = (duel_id: number) =>
  req<DuelCancelResponse>(`/duels/${duel_id}/cancel`, { method: 'POST' });

export const apiStartSoloGame = (kind: string, stake_pct: SoloBetPercent) =>
  req<SoloGameResult>('/solo', {
    method: 'POST',
    body: JSON.stringify({ kind, stake_pct }),
  });
export const apiGetCurrentSoloGame = () => req<{ game: SoloGameResult | null }>('/solo/current');
export const apiFinishSoloGame = () => req<{ ok: boolean }>('/solo/finish', { method: 'POST' });
export const apiGetSoloStats = () => req<SoloStats>('/solo/stats');

export const apiCocktailGuess = (fruits: string[]) =>
  req<CocktailGuessResult>('/cocktail/guess', { method: 'POST', body: JSON.stringify({ fruits }) });
export const apiGetCocktailState = () => req<CocktailState>('/cocktail');

export const apiGetSafeState = () => req<SafeState>('/safe');
export const apiSafeGuess = (code: string) =>
  req<SafeGuessResult>('/safe/guess', { method: 'POST', body: JSON.stringify({ code }) });
