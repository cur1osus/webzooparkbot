// ─── Core GameState ───────────────────────────────────────────────────────────

export interface AnimalState {
  animal_id: string;
  quantity: number;
}

export interface AviaryState {
  aviary_id: string;
  count: number; // how many of this aviary type owned
}

export interface SickAnimal {
  animal_id: string;
  penalty_rub_per_min: number;
  since: string; // ISO timestamp
}

export interface ForgeProperty {
  type: string;       // 'animal_income' | 'income_boost' | 'bank_rate' | 'aviary_discount' | 'animal_discount' | 'extra_turns' | 'last_chance' | 'bonus_rerolls'
  value: number;      // integer (e.g. 12 for 12%)
  label: string;      // e.g. "Курс банка -12%"
  animal_id?: string; // set only for animal_income
}

export interface ForgeItem {
  id: string;
  name: string;
  icon: string;         // emoji
  rarity: string;       // 'common' | 'rare' | 'epic' | 'mythical' | 'legendary'
  level: number;
  properties: ForgeProperty[];
  is_active: boolean;
}

export interface ForgeSet {
  id: string;
  name: string;
  icon: string;
  item_ids: string[];
  is_active: boolean;
}

export interface ClanInfo {
  id: number;
  name: string;
  level: number;
  member_count: number;
  specialty: string | null;
  role: 'owner' | 'member';
}

export interface GameState {
  // User
  tg_id: number;
  nickname: string;
  registered_at: string;   // ISO
  profile_emoji: string | null;

  // Balances
  rub: number;
  usd: number;
  paw_coins: number;

  // Income/expenses (per minute)
  income_rub_per_min: number;
  expenses_rub_per_min: number;

  // Zoo state
  animals: AnimalState[];
  aviaries: AviaryState[];
  total_seats: number;
  free_seats: number;
  species_count: number;
  diversity_bonus_per_species: number; // e.g. 0.01 = 1% per species

  // Sick animals
  sick_animals: SickAnimal[];

  // Forge
  forge_items: ForgeItem[];
  forge_sets: ForgeSet[];

  // Clan
  clan: ClanInfo | null;

  // Season
  season_end: string; // ISO datetime

  // Bonus available
  bonus: 0 | 1;

  // Server-side version tracking
  balance_seq: number;
  data_version: number;
}

// ─── API response wrappers ────────────────────────────────────────────────────

export interface MeResponse extends GameState {}

export interface SavePayload {
  rub: number;
  usd: number;
  paw_coins: number;
  animals: AnimalState[];
  aviaries: AviaryState[];
  balance_seq: number;
  data_version: number;
}

export type SaveResponse =
  | { ok: false }
  | {
      ok: true;
      rub: number;
      usd: number;
      paw_coins: number;
      balance_seq: number;
      data_version: number;
    };

// ─── Shop ─────────────────────────────────────────────────────────────────────

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

// ─── Bank ─────────────────────────────────────────────────────────────────────

export interface BankInfo {
  rub_rate: number;      // 1 USD = X RUB
  usd_rate: number;      // 1 RUB = X USD
  rub_discount: number;  // % discount from forge items
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

// ─── Daily bonus ──────────────────────────────────────────────────────────────

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

// ─── Merchant ─────────────────────────────────────────────────────────────────

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

// ─── Cure ─────────────────────────────────────────────────────────────────────

export interface CureResponse {
  ok: boolean;
  cost_paw_coins: number;
  new_paw_coins: number;
  message?: string;
}

// ─── Forge ────────────────────────────────────────────────────────────────────

export interface ForgeCreateResponse {
  ok: boolean;
  item: ForgeItem;
  cost_usd?: number;
  new_usd: number;
  cost_paw_coins?: number;
  new_paw_coins: number;
}

export interface ForgeUpgradeResponse {
  ok: boolean;
  success: boolean;
  success_pct: number;
  item: ForgeItem;
  cost_usd: number;
  new_usd: number;
}

export interface ForgeMergeResponse {
  ok: boolean;
  new_item: ForgeItem;
  cost_usd: number;
  new_usd: number;
}

export interface ForgeSellResponse {
  ok: boolean;
  earned_usd: number;
  new_usd: number;
}

// ─── Leaderboard ─────────────────────────────────────────────────────────────

export interface TopEntry {
  rank: number;
  tg_id: number;
  nickname: string;
  income_rub_per_min: number;
  name_color: string | null;
  is_me: boolean;
}

export interface TopResponse {
  entries: TopEntry[];
  my_rank: number | null;
}

// ─── Clan ─────────────────────────────────────────────────────────────────────

export interface ClanOut {
  idpk: number;
  name: string;
  level: number;
  member_count: number;
  specialty: string | null;
  owner_nickname: string;
}

export interface ClanListResponse {
  clans: ClanOut[];
  my_clan: ClanOut | null;
  my_role: 'owner' | 'member' | null;
}

// ─── Referrals ───────────────────────────────────────────────────────────────

export interface ReferralResponse {
  code: string;
  total: number;
  reward_usd_per_ref: number;
  referred: string[];
}

// ─── Transfers ───────────────────────────────────────────────────────────────

export interface TransferOut {
  key: string;
  total_rub: number;
  rub_per_claim: number;
  max_claims: number;
  claims: number;
  active: boolean;
  created_at: string;
}

// ─── Multiplayer game ─────────────────────────────────────────────────────────

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

// ─── Donate ───────────────────────────────────────────────────────────────────

export interface DonateInfo {
  stars_to_paw: number; // 1 star = X paw_coins
}

// ─── Solo stats ───────────────────────────────────────────────────────────────

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

// ─── Register ─────────────────────────────────────────────────────────────────

export interface RegisterResponse {
  ok: boolean;
  game_state: GameState;
}

// ─── Config ───────────────────────────────────────────────────────────────────

export interface AppConfig {
  bot_username: string;
}

// ─── Packs ────────────────────────────────────────────────────────────────────

export type GeneTier = 'low' | 'medium' | 'high';
export type Habitat  = 'desert' | 'mountains' | 'forest' | 'fields' | 'antarctica';

export interface PackAnimal {
  id: number;
  survival:     GeneTier;
  reproduction: GeneTier;
  appearance:   GeneTier;
  size_trait:   GeneTier;
  habitat:      Habitat;
  acquired_at:   string; // ISO
  dies_at:       string | null;
  locality_id:   number | null;
  can_breed:     boolean; // false if already bred today
  income:        number; // ₽/min computed by server
  habitat_bonus: boolean; // true if placed in matching locality
}

export interface PackInfo {
  packs_today:    number;
  free_available: boolean;
  next_price:     number;
  animals:        PackAnimal[];
}

// ─── Localities (GDD §5) ─────────────────────────────────────────────────────

export interface Locality {
  id:      number;
  habitat: Habitat;
  animals: PackAnimal[];
}

export interface LocalitiesInfo {
  localities:     Locality[];
  unassigned:     PackAnimal[];
  next_price:     number | null; // null = max 5 reached
  habitats_taken: Habitat[];
}

export interface BuyLocalityResult {
  ok:         boolean;
  id:         number;
  habitat:    Habitat;
  price_paid: number;
  new_rub:    number;
}

// ─── Breeding (GDD §6) ───────────────────────────────────────────────────────

export interface BreedResult {
  ok:      boolean;
  success: boolean;
  rate:    number;       // 0.0–1.0
  animal:  PackAnimal | null;
}

export interface PackOpenResult {
  ok:          boolean;
  price_paid:  number;
  new_rub:     number;
  packs_today: number;
  next_price:  number;
  animal:      PackAnimal;
}

// ─── Expeditions (GDD §7) ────────────────────────────────────────────────────

export interface ExpeditionResult {
  outcome: 'victory' | 'defeat';
  squad_power: number;
  wild_power: number;
  wild: {
    survival: GeneTier;
    reproduction: GeneTier;
    appearance: GeneTier;
    size_trait: GeneTier;
    habitat: Habitat;
  };
  reward_animal_id?: number;
  captured_animal?: PackAnimal;
  killed_id?: number;
}

export interface ActiveExpedition {
  id: number;
  habitat: Habitat;
  started_at: string;
  ends_at: string;
  status: 'active' | 'finished';
  animals: PackAnimal[];
  result: ExpeditionResult | null;
}

export interface ExpeditionInfo {
  active: ActiveExpedition | null;
  localities: Array<{ id: number; habitat: Habitat }>;
  available_animals: PackAnimal[];
  expedition_minutes: Record<Habitat, number>;
}

export interface ExpeditionStartResponse {
  ok: boolean;
  expedition: ActiveExpedition;
}

export interface ExpeditionFinishResponse {
  ok: boolean;
  result: ExpeditionResult;
}

// ─── Cocktail game ────────────────────────────────────────────────────────────

export interface CocktailGuessResult {
  ok: boolean;
  won: boolean;
  attempts_left: number;
  clues: Array<{ pos: number; status: 'correct' | 'present' | 'absent' }>;
  reward_paw?: number;
  new_paw_coins?: number;
}
