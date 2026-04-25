import type { AnimalState, AviaryState, GameState } from './gameState';

export type MeResponse = GameState;

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

export interface RegisterResponse {
  ok: boolean;
  game_state: GameState;
}

export interface AppConfig {
  bot_username: string;
}
