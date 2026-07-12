import type { GameState } from './gameState';

export type MeResponse = GameState;

export interface RegisterResponse {
  ok: boolean;
  game_state: GameState;
}

export interface AppConfig {
  bot_username: string;
}

export interface AdminPlayer {
  id: number;
  tg_id: number;
  nickname: string;
  username: string | null;
  status: 'active' | 'banned';
  registered_at: string;
  last_seen_at: string | null;
  rub: number;
  usd: number;
  paw: number;
  animals_count: number;
  income_rub_per_min: number;
}

export interface AdminOverview {
  generated_at: string;
  stats: {
    players: number;
    active_players: number;
    banned_players: number;
    online_players: number;
    animals: number;
    ledger_entries_today: number;
  };
  balances: { rub: number; usd: number; paw: number };
  treasury: { rub: number; usd: number; paw: number };
  bank_rate: number | null;
  players_list: AdminPlayer[];
}

export interface AdminGrantResult {
  ok: true;
  tg_id: number;
  currency: 'rub' | 'usd' | 'paw';
  new_balance: number;
}
