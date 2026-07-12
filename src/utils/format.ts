const SUFFIXES = [
  { v: 1e63, s: 'Vi' },
  { v: 1e60, s: 'No' },
  { v: 1e57, s: 'Oc' },
  { v: 1e54, s: 'Sp' },
  { v: 1e51, s: 'Sx' },
  { v: 1e48, s: 'Qn' },
  { v: 1e45, s: 'Qd' },
  { v: 1e42, s: 'Td' },
  { v: 1e39, s: 'Dd' },
  { v: 1e36, s: 'Ud' },
  { v: 1e33, s: 'Dc' },
  { v: 1e30, s: 'No' },
  { v: 1e27, s: 'Oc' },
  { v: 1e24, s: 'Sp' },
  { v: 1e21, s: 'Sx' },
  { v: 1e18, s: 'Qn' },
  { v: 1e15, s: 'Qd' },
  { v: 1e12, s: 'T' },
  { v: 1e9, s: 'B' },
  { v: 1e6, s: 'M' },
  { v: 1e3, s: 'K' },
];

// Full grouped digits stay readable and fit on screen well past a million, so only
// numbers from 100M up get the compact suffix; everything below shows exact digits.
const COMPACT_THRESHOLD = 1e8;

export function fmt(value: number | string): string {
  const n = typeof value === 'string' ? parseFloat(value) : value;
  if (!Number.isFinite(n)) return String(value);
  const abs = Math.abs(n);
  const sign = n < 0 ? '-' : '';
  if (abs >= COMPACT_THRESHOLD) {
    for (const { v, s } of SUFFIXES) {
      if (abs >= v) return `${sign}${Math.floor(abs / v)}${s}`;
    }
  }
  return `${sign}${Math.round(abs).toLocaleString('ru-RU')}`;
}

/**
 * Balance format for the counting header: full grouped digits so per-second
 * accrual is visible, switching to the compact suffix form only once the number
 * gets too long to read digit-by-digit.
 */
export function fmtBalance(value: number | string): string {
  const n = typeof value === 'string' ? parseFloat(value) : value;
  if (!Number.isFinite(n)) return String(value);
  if (Math.abs(n) >= 1e8) return fmt(n);
  return Math.round(n).toLocaleString('ru-RU');
}

export function fmtRub(value: number | string): string {
  return `₽ ${fmt(value)}`;
}

export function fmtUsd(value: number | string): string {
  return `$ ${fmt(value)}`;
}

export function fmtPaw(value: number | string): string {
  return `${fmt(value)}`;
}

export function fmtMin(value: number | string): string {
  const n = typeof value === 'string' ? parseFloat(value) : value;
  if (n >= 0) return `+${fmt(n)}`;
  return fmt(n);
}

export function formatDate(isoStr: string): string {
  const d = new Date(isoStr);
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
}

export function formatDateShort(isoStr: string): string {
  const d = new Date(isoStr);
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' }).replace(' г.', '');
}

export function formatCountdown(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const d = Math.floor(s / 86400);
  const h = String(Math.floor((s % 86400) / 3600)).padStart(2, '0');
  const m = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
  const sec = String(s % 60).padStart(2, '0');
  if (d > 0) return `${d}д ${h}:${m}:${sec}`;
  return `${h}:${m}:${sec}`;
}
