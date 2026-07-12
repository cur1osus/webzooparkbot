import type {
  CocktailGuessResult,
  DuelActionResponse,
  DuelCancelResponse,
  DuelsResponse,
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
export const apiJoinDuel = (duel_id: number) =>
  req<DuelActionResponse>(`/duels/${duel_id}/join`, { method: 'POST' });
export const apiCancelDuel = (duel_id: number) =>
  req<DuelCancelResponse>(`/duels/${duel_id}/cancel`, { method: 'POST' });

export const apiStartSoloGame = (kind: string, stake_rub: number) =>
  req<SoloGameResult>('/solo', {
    method: 'POST',
    body: JSON.stringify({ kind, stake_rub: Math.floor(stake_rub) }),
  });
export const apiGetSoloStats = () => req<SoloStats>('/solo/stats');

export const apiCocktailGuess = (fruits: string[]) =>
  req<CocktailGuessResult>('/cocktail/guess', { method: 'POST', body: JSON.stringify({ fruits }) });
