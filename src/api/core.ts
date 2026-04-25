import type { AppConfig, GameState, RegisterResponse, SaveResponse } from '@/types';
import { req } from './client';

export const apiMe = () => req<GameState>('/me');
export const apiSave = (payload: object, keepalive = false) =>
  req<SaveResponse>('/save', { method: 'POST', body: JSON.stringify(payload) }, keepalive);
export const apiRegister = (nickname: string) =>
  req<RegisterResponse>('/register', { method: 'POST', body: JSON.stringify({ nickname }) });
export const apiConfig = () => req<AppConfig>('/config');
