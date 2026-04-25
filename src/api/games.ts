import type { CocktailGuessResult, MpGame, MpGameResponse, SoloGameResult, SoloStats } from '@/types';
import { req } from './client';

export const apiGetOpenGames = () => req<MpGameResponse>('/mpgame/open');
export const apiCreateMpGame = (game_type: string, bet_rub: number) =>
  req<{ ok: boolean; game: MpGame }>('/mpgame/create', { method: 'POST', body: JSON.stringify({ game_type, bet_rub }) });
export const apiJoinMpGame = (game_id: number) =>
  req<{ ok: boolean; game: MpGame }>(`/mpgame/${game_id}/join`, { method: 'POST' });
export const apiThrowMpGame = (game_id: number) =>
  req<{ ok: boolean; game: MpGame }>(`/mpgame/${game_id}/throw`, { method: 'POST' });
export const apiStartSoloGame = (game_type: string, bet_rub: number) =>
  req<SoloGameResult>('/start_solo_game', { method: 'POST', body: JSON.stringify({ game_type, bet_rub }) });
export const apiGetSoloStats = () => req<SoloStats>('/get_solo_stats');
export const apiCocktailGuess = (fruits: string[]) =>
  req<CocktailGuessResult>('/cocktail/guess', { method: 'POST', body: JSON.stringify({ fruits }) });
