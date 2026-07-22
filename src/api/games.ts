import type {
  CocktailGuessResult,
  CocktailState,
  SafeGuessResult,
  SafeState,
} from '@/types';
import { req } from './client';

export const apiCocktailGuess = (fruits: string[]) =>
  req<CocktailGuessResult>('/cocktail/guess', { method: 'POST', body: JSON.stringify({ fruits }) });
export const apiGetCocktailState = () => req<CocktailState>('/cocktail');

export const apiGetSafeState = () => req<SafeState>('/safe');
export const apiSafeGuess = (code: string) =>
  req<SafeGuessResult>('/safe/guess', { method: 'POST', body: JSON.stringify({ code }) });
