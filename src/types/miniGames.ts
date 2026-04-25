export interface MpGame {
  id: number;
  game_type: string;
  bet_rub: number;
  creator_nickname: string;
  created_at: string;
  status: 'open' | 'playing' | 'finished';
  winner_nickname: string | null;
}

export interface MpGameResponse {
  games: MpGame[];
}

export interface DonateInfo {
  stars_to_paw: number;
}

export interface SoloStats {
  games_played: number;
  wins: number;
  losses: number;
  total_won_rub: number;
  total_lost_rub: number;
}

export interface SoloThrowRound {
  round: number;
  player_roll: number;
  ai_roll: number;
}

export type SoloBasketballThrow = SoloThrowRound;

export interface SoloGameResult {
  ok: boolean;
  result: string;
  score: number;
  won: boolean;
  rub_delta: number;
  new_rub: number;
  is_draw?: boolean;
  player_score?: number;
  ai_score?: number;
  history?: SoloThrowRound[];
}

export interface CocktailGuessResult {
  ok: boolean;
  won: boolean;
  attempts_left: number;
  clues: Array<{ pos: number; status: 'correct' | 'present' | 'absent' }>;
  reward_paw?: number;
  new_paw_coins?: number;
}
