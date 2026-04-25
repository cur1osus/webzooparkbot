import { env } from '@/lib/env';
import { getRawTelegramInitData } from '@/lib/tmaEnv';

const DEV_KEY = 'dev_user_id';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function isDevMode(): boolean {
  return Boolean(localStorage.getItem(DEV_KEY));
}

export function setDevUserId(id: string) {
  localStorage.setItem(DEV_KEY, id);
}

export function clearDevUserId() {
  localStorage.removeItem(DEV_KEY);
}

export function getHeaders(): HeadersInit {
  const initData = getRawTelegramInitData() ?? '';

  if (initData) {
    return { 'Content-Type': 'application/json', 'X-Init-Data': initData };
  }

  const devId = localStorage.getItem(DEV_KEY) ?? '';
  if (devId) {
    return { 'Content-Type': 'application/json', 'X-Dev-User-Id': devId };
  }

  return { 'Content-Type': 'application/json', 'X-Init-Data': '' };
}

export async function req<T>(path: string, init?: RequestInit, keepalive = false): Promise<T> {
  const res = await fetch(`${env.apiUrl}${path}`, {
    ...init,
    keepalive,
    headers: { ...getHeaders(), ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, (err as { detail?: string }).detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}
