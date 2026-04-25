export interface BuyAnimalResponse {
  ok: boolean;
  new_rub: number;
  new_quantity: number;
  new_total_animals: number;
  new_free_seats: number;
  message?: string;
}

export interface BuyAviaryResponse {
  ok: boolean;
  new_rub: number;
  new_count: number;
  new_total_seats: number;
  new_free_seats: number;
}

export interface BankInfo {
  rub_rate: number;
  usd_rate: number;
  rub_discount: number;
  usd_discount: number;
  min_exchange_rub: number;
  min_exchange_usd: number;
}

export interface ExchangeResult {
  ok: boolean;
  new_rub: number;
  new_usd: number;
  message?: string;
}

export interface BonusResult {
  ok: boolean;
  type: 'rub' | 'usd' | 'paw_coins' | 'aviary' | 'animal';
  amount?: number;
  animal_id?: string;
  aviary_id?: string;
  message: string;
  new_rub?: number;
  new_usd?: number;
  new_paw_coins?: number;
}

export interface CureResponse {
  ok: boolean;
  cost_paw_coins: number;
  new_paw_coins: number;
  message?: string;
}

export interface MerchantAnimal {
  slot: 1 | 2 | 3;
  animal_id: string;
  quantity: number;
  original_price: number;
  discount_pct: number;
  final_price: number;
}

export interface MerchantResponse {
  animals: MerchantAnimal[];
  refreshes_at: string;
}

export interface MerchantBuyResponse {
  ok: boolean;
  new_rub: number;
  new_quantity: number;
  message?: string;
}
