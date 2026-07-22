import { describe, expect, it } from 'vitest';
import type { Animal, GameState } from '@/types';
import { averageLifespanMs, buildForecast, declineOver, netGainFromAnimals } from './incomeForecast';

const NOW = Date.parse('2026-07-22T12:00:00Z');
const DAY = 24 * 60 * 60_000;

function animal(id: number, income: number, livesDays: number, ageDays = 0): Animal {
  return {
    id,
    income,
    acquired_at: new Date(NOW - ageDays * DAY).toISOString(),
    dies_at: new Date(NOW + livesDays * DAY).toISOString(),
  } as Animal;
}

/** Зоопарк, где содержание ровно совпадает с формулой: скидок нет, ratio = 1. */
function zoo(animals: Animal[], upkeepPercentOfIncome = 0): GameState {
  const income = animals.reduce((acc, a) => acc + a.income, 0);
  return {
    animals,
    live_animals_count: animals.length,
    income_rub_per_min: income,
    upkeep_rub_per_min: Math.round((income * upkeepPercentOfIncome) / 100),
  } as GameState;
}

describe('declineOver', () => {
  it('counts the deaths inside the horizon and what they take with them', () => {
    const gs = zoo([animal(1, 600, 2), animal(2, 400, 10)]);
    const decline = declineOver(buildForecast(gs, NOW), 7 * DAY);

    expect(decline.deaths).toBe(1);
    expect(decline.netNow).toBe(1000);
    expect(decline.netThen).toBe(400);
    expect(decline.lostNet).toBe(600);
    expect(decline.percent).toBe(60);
  });

  it('replaces the lost income with animals of average value, not with corpses counted', () => {
    // Умирает одно животное на 900 ₽/мин при среднем по зоопарку 350 — заменить его
    // одним средним не выйдет, нужно три.
    const gs = zoo([animal(1, 900, 2), animal(2, 100, 30), animal(3, 50, 30)]);
    const decline = declineOver(buildForecast(gs, NOW), 7 * DAY);

    expect(decline.deaths).toBe(1);
    expect(decline.replacements).toBe(3);
  });

  it('reports no loss when everyone outlives the horizon', () => {
    const decline = declineOver(buildForecast(zoo([animal(1, 500, 40)]), NOW), 7 * DAY);
    expect(decline).toMatchObject({ deaths: 0, lostNet: 0, percent: 0, replacements: 0 });
  });
});

describe('netGainFromAnimals', () => {
  it('adds the average animal and charges the upkeep that comes with it', () => {
    // Четыре животных по 250 ₽/мин, содержание — 12% дохода (голая формула для четырёх).
    const gs = zoo([animal(1, 250, 30), animal(2, 250, 30), animal(3, 250, 30), animal(4, 250, 30)], 12);
    const forecast = buildForecast(gs, NOW);
    const gain = netGainFromAnimals(forecast, 2);

    // Грязными два средних животных дают +500, но содержание растёт и с них, и со старых.
    expect(gain).toBeGreaterThan(0);
    expect(gain).toBeLessThan(500);
  });

  it('gives nothing for an empty zoo — there is no average to lean on', () => {
    expect(netGainFromAnimals(buildForecast(zoo([]), NOW), 3)).toBe(0);
  });
});

describe('averageLifespanMs', () => {
  it('measures the full span from birth to death, not the time left', () => {
    const gs = zoo([animal(1, 100, 2, 6), animal(2, 100, 4, 4)]);
    expect(averageLifespanMs(gs)).toBe(8 * DAY);
  });

  it('falls back to the medium survival gene when the zoo is empty', () => {
    expect(averageLifespanMs(zoo([]))).toBe(8 * DAY);
  });
});
