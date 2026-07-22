export interface DonateInfo {
  stars_to_paw: number;
}

export interface CocktailGuessResult {
  ok: boolean;
  won: boolean;
  attempts_left: number;
  clues: Array<{ pos: number; status: 'correct' | 'present' | 'absent' }>;
  reward_paw?: number;
  /** True only for the first solver of the day, who is paid double. */
  was_first?: boolean;
  new_paw_coins?: number;
  winner_nickname?: string | null;
  solved_today?: number;
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
  /** Every solver is paid, so this now tracks `solved` exactly. */
  rewarded: boolean;
  was_first: boolean;
  winner_nickname: string | null;
  /** How many players have cracked today's recipe. */
  solved_today: number;
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
