import { describe, expect, it } from 'vitest';
import type { PackTierInfo } from '@/types';
import { bestValueTier, evaluatePack } from './packValue';

const DAY = 24 * 60 * 60_000;

function tier(overrides: Partial<PackTierInfo> = {}): PackTierInfo {
  return {
    tier: 'rare',
    price: 100,
    unlocked: true,
    reward_range: { animals: [1, 3], rub: [0, 0], usd: [0, 0] },
    batch_prices: {},
    ...overrides,
  };
}

// Каждое животное приносит 10 ₽/мин чистыми, доллар стоит ровно 100 ₽.
const ctx = {
  netGainFor: (animals: number) => animals * 10,
  usdToRub: (usd: number) => usd * 100,
  lifespanMs: 10 * DAY,
};

describe('evaluatePack', () => {
  it('prices the pack by its average haul and pays it back out of net income', () => {
    const value = evaluatePack(tier(), ctx);

    expect(value.animals).toBe(2);
    expect(value.netGainPerMin).toBe(20);
    expect(value.netCostRub).toBe(10_000);
    // 10 000 ₽ по 20 ₽/мин — 500 минут.
    expect(value.paybackMs).toBe(500 * 60_000);
    expect(value.lifetimeRub).toBe(20 * 10 * 24 * 60);
    expect(value.multiple).toBeCloseTo(28.8, 1);
  });

  it('subtracts the money the pack hands back from its price', () => {
    const value = evaluatePack(tier({ reward_range: { animals: [2, 2], rub: [1_000, 3_000], usd: [10, 10] } }), ctx);

    // 100$ = 10 000 ₽ минус 2 000 ₽ наличными и 10$ (ещё 1 000 ₽).
    expect(value.netCostRub).toBe(7_000);
  });

  it('treats a pack that hands back more than it costs as free', () => {
    const value = evaluatePack(tier({ price: 5, reward_range: { animals: [1, 1], rub: [9_000, 9_000], usd: [0, 0] } }), ctx);

    expect(value.netCostRub).toBe(0);
    expect(value.paybackMs).toBe(0);
    expect(value.multiple).toBeNull();
  });

  it('has no payback when the zoo cannot say what an animal earns', () => {
    const value = evaluatePack(tier(), { ...ctx, netGainFor: () => 0 });

    expect(value.paybackMs).toBeNull();
    expect(value.lifetimeRub).toBe(0);
  });
});

describe('bestValueTier', () => {
  it('picks the tier that returns the most per rouble among the ones on sale', () => {
    const values = [
      evaluatePack(tier({ tier: 'rare', price: 100 }), ctx),
      evaluatePack(tier({ tier: 'epic', price: 50, reward_range: { animals: [2, 4], rub: [0, 0], usd: [0, 0] } }), ctx),
      evaluatePack(tier({ tier: 'mythic', price: 1, unlocked: false, reward_range: { animals: [9, 9], rub: [0, 0], usd: [0, 0] } }), ctx),
    ];

    expect(bestValueTier(values)).toBe('epic');
  });

  it('recommends nothing when no unlocked tier ever earns its price back', () => {
    const values = [evaluatePack(tier({ price: 1_000_000 }), ctx)];
    expect(bestValueTier(values)).toBeNull();
  });
});
