import type { BuyAnimalResponse, BuyAviaryResponse } from '@/types';
import { req } from './client';

export const apiBuyAnimal = (animal_id: string, quantity: number) =>
  req<BuyAnimalResponse>('/buy_animal', { method: 'POST', body: JSON.stringify({ animal_id, quantity }) });
export const apiBuyAviary = (aviary_id: string) =>
  req<BuyAviaryResponse>('/buy_aviary', { method: 'POST', body: JSON.stringify({ aviary_id }) });
