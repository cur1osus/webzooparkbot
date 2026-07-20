export type GameKind = 'basketball' | 'darts' | 'bowling' | 'dice' | 'football';

/** Currency a duel is wagered in. Rubles are the everyday currency; dollars are the premium
 *  one bought at the bank. A lobby fixes its currency at creation and every stake, refund and
 *  payout moves in it. */
export type DuelCurrency = 'rub' | 'usd';

/** Player versus player, zero-sum. `duel_moves` and `duel_bonus` items apply here. */
export interface Duel {
  id: number;
  kind: GameKind | string;
  stake: number;
  currency: DuelCurrency;
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
    reward: number;
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
  refunded: number;
  currency: DuelCurrency;
  new_rub: number;
  new_usd: number;
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
  kind: string;
  won: boolean;
  stake_rub: number;
  rub_delta: number;
  new_rub: number;
  player_score: number;
  ai_score: number;
  history: SoloThrowRound[];
  result: string;
  resumed?: boolean;
}

export interface CocktailGuessResult {
  ok: boolean;
  won: boolean;
  attempts_left: number;
  clues: Array<{ pos: number; status: 'correct' | 'present' | 'absent' }>;
  reward_paw?: number;
  new_paw_coins?: number;
  winner_nickname?: string | null;
}

export interface CocktailHistoryEntry {
  fruits: string[];
  clues: Array<{ pos: number; status: 'correct' | 'present' | 'absent' }>;
}

export interface CocktailState {
  ok: boolean;
  attempts_left: number;
  history: CocktailHistoryEntry[];
  solved: boolean;
  rewarded: boolean;
  reward_claimed: boolean;
  winner_nickname: string | null;
}

/** One published guess. Only appears once its day's window has closed. */
export interface SafeBoardEntry {
  day: string;
  nickname: string;
  code: string;
  /** Right digit, right place. */
  exact: number;
  /** Right digit, wrong place. */
  misplaced: number;
}

export interface SafeState {
  ok: boolean;
  is_open: boolean;
  /** While open this is when the window opened; while closed, the next opening. */
  opens_at: string;
  closes_at: string;
  code_length: number;
  round_day: string;
  prize_usd: number;
  treasury_usd: number;
  attempts_left: number;
  /** The viewer's own sealed guesses for today — deliberately without clues. */
  pending_codes: string[];
  board: SafeBoardEntry[];
}

export interface SafeGuessResult {
  ok: boolean;
  accepted: string;
  attempts_left: number;
  closes_at: string;
}
