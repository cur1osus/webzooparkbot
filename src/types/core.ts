import type { GameState } from './gameState';

export type MeResponse = GameState;

export interface RegisterResponse {
  ok: boolean;
  game_state: GameState;
}

export interface AppConfig {
  bot_username: string | null;
}

export interface MaintenanceStatus {
  active: boolean;
  started_at: string | null;
  ends_at: string | null;
  message: string;
}

export interface OnlinePlayer {
  id: number;
  nickname: string;
  nickname_color: string;
  profile_emoji: string | null;
  profile_frame: string | null;
  is_me: boolean;
}

export interface MaintenancePollStatus extends MaintenanceStatus {
  online_count: number;
  online_players: OnlinePlayer[];
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
  upkeep_rub_per_min: number;
  net_income_rub_per_min: number;
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
  maintenance: MaintenanceStatus;
  players_list: AdminPlayer[];
  custom_achievements: AdminCustomAchievement[];
}

export interface AdminCustomAchievement {
  id: string;
  title: string;
  description: string;
  audience: 'all' | 'selected';
  recipient_count: number;
  image_url: string;
  created_at: string;
}

export interface AdminGrantResult {
  ok: true;
  tg_id: number;
  currency: 'rub' | 'usd' | 'paw';
  new_balance: number;
}
