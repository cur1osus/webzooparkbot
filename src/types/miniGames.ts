export type GameKind = 'basketball' | 'darts' | 'bowling' | 'dice' | 'football';

/** Player versus player, zero-sum. `duel_moves` and `duel_bonus` items apply here. */
export interface Duel {
  id: number;
  kind: GameKind | string;
  stake_rub: number;
  creator_nickname: string;
  created_at: string;
  expires_at: string | null;
  status: 'open' | 'finished' | 'cancelled';
  participant_count: number;
  max_players: number;
  creator_joined: boolean;
  viewer_joined: boolean;
  participants: Array<{
    player_id: number;
    nickname: string;
    score: number | null;
    place: number | null;
    reward_rub: number;
  }>;
  creator_score: number | null;
  opponent_score: number | null;
  third_score: number | null;
  winner_nickname: string | null;
  outcome_message: string | null;
}

export interface DuelsResponse {
  games: Duel[];
}

export interface DuelActionResponse {
  ok: boolean;
  game: Duel;
  new_rub: number;
}

export interface DuelResponse {
  ok: boolean;
  game: Duel;
}

export interface DuelCancelResponse {
  ok: boolean;
  refunded_rub: number;
  new_rub: number;
}

export interface DuelResolveResponse {
  ok: boolean;
  game: Duel;
}

export interface DonateInfo {
  stars_to_paw: number;
}

export interface SoloStats {
  games_played: number;
  wins: number;
  losses: number;
  won_rub: number;
  lost_rub: number;
}

export type SoloBetPercent = 5 | 10 | 15;

export interface SoloThrowRound {
  round: number;
  player_roll: number;
  ai_roll: number;
}

/** Against the house, which keeps a 4% edge. No item touches it. */
export interface SoloGameResult {
  ok: boolean;
  won: boolean;
  stake_rub: number;
  rub_delta: number;
  new_rub: number;
  player_score: number;
  ai_score: number;
  history: SoloThrowRound[];
  result: string;
}

export interface CocktailGuessResult {
  ok: boolean;
  won: boolean;
  attempts_left: number;
  clues: Array<{ pos: number; status: 'correct' | 'present' | 'absent' }>;
  reward_paw?: number;
  new_paw_coins?: number;
}
