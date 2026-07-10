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

/**
 * Turn a failed request into a plain-language message the player can act on
 * (Nielsen heuristic #9). Meaningful domain messages from the server
 * (e.g. "Недостаточно средств") are kept as-is; only technical/server/network
 * failures get a friendly generic replacement.
 */
function friendlyError(status: number, serverDetail?: string): string {
  if (status >= 500) return 'Сервер сейчас недоступен. Попробуйте через пару секунд.';
  if (status === 429) return 'Слишком много запросов подряд. Немного подождите и повторите.';
  const detail = serverDetail?.trim();
  // Keep human server messages; drop raw HTTP reason phrases like "Bad Gateway".
  if (detail && !/^[A-Z][a-z]+(\s[A-Za-z]+)*$/.test(detail)) return detail;
  return 'Что-то пошло не так. Попробуйте ещё раз.';
}

export async function req<T>(path: string, init?: RequestInit, keepalive = false): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${env.apiUrl}${path}`, {
      ...init,
      keepalive,
      headers: { ...getHeaders(), ...(init?.headers ?? {}) },
    });
  } catch {
    // Network / offline / DNS — fetch rejects before any HTTP status exists.
    throw new ApiError(0, 'Нет соединения с сервером. Проверьте интернет и попробуйте ещё раз.');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const serverDetail = (body as { detail?: string } | null)?.detail;
    throw new ApiError(res.status, friendlyError(res.status, serverDetail));
  }
  return res.json() as Promise<T>;
}
