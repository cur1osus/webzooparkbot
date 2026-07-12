import { describe, expect, it } from 'vitest';
import { fmt, fmtMin, formatCountdown } from './format';

describe('format utilities', () => {
  it('keeps exact grouped values below the compact threshold', () => {
    expect(fmt(999)).toBe('999');
    expect(fmt(1_250)).toBe('1\u00A0250');
    expect(fmt(2_900_000)).toBe('2\u00A0900\u00A0000');
    expect(fmt(100_000_000)).toBe('100M');
  });

  it('keeps signs for per-minute values', () => {
    expect(fmtMin(1500)).toBe('+1\u00A0500');
    expect(fmtMin(-1500)).toBe('-1\u00A0500');
  });

  it('formats countdowns with day prefix when needed', () => {
    expect(formatCountdown(65)).toBe('00:01:05');
    expect(formatCountdown(90_061)).toBe('1д 01:01:01');
  });
});
