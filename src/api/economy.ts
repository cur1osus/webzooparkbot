import type { BankInfo, BonusResult, CureResponse, ExchangeResult } from '@/types';
import { req } from './client';

export const apiGetBank = () => req<BankInfo>('/bank');
export const apiExchange = (from: 'rub' | 'usd', amount: number, exchange_all = false) =>
  req<ExchangeResult>('/bank/exchange', { method: 'POST', body: JSON.stringify({ from, amount, exchange_all }) });
export const apiClaimBonus = () => req<BonusResult>('/claim_bonus', { method: 'POST' });
export const apiCureAnimal = (animal_id: string) =>
  req<CureResponse>('/cure_animal', { method: 'POST', body: JSON.stringify({ animal_id }) });
