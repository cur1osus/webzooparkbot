import { describe, expect, it } from 'vitest';
import { fmt, fmtMin, formatCountdown } from './format';

describe('format utilities', () => {
  it('formats compact integer suffixes', () => {
    expect(fmt(999)).toBe('999');
    expect(fmt(1_250)).toBe('1K');
    expect(fmt(2_900_000)).toBe('2M');
  });

  it('keeps signs for per-minute values', () => {
    expect(fmtMin(1500)).toBe('+1K');
    expect(fmtMin(-1500)).toBe('-1K');
  });

  it('formats countdowns with day prefix when needed', () => {
    expect(formatCountdown(65)).toBe('00:01:05');
    expect(formatCountdown(90_061)).toBe('1д 01:01:01');
  });
});
