import type { BankInfo, BonusClaimResult, BonusOffer, CureResponse, ExchangeResult } from '@/types';
import { req } from './client';

export const apiGetBank = () => req<BankInfo>('/bank');

/** Rubles to dollars. The bank has no reverse direction. */
export const apiExchange = (amount_rub: number, exchange_all = false) =>
  req<ExchangeResult>('/bank/exchange', {
    method: 'POST',
    body: JSON.stringify({ amount_rub: Math.max(0, Math.floor(amount_rub)), exchange_all }),
  });

export const apiGetBonus = () => req<BonusOffer>('/bonus');
export const apiRerollBonus = () => req<BonusOffer>('/bonus/reroll', { method: 'POST' });
export const apiClaimBonus = () => req<BonusClaimResult>('/bonus/claim', { method: 'POST' });

export const apiCureAnimal = (animal_id: number) =>
  req<CureResponse>('/animals/cure', { method: 'POST', body: JSON.stringify({ animal_id }) });
