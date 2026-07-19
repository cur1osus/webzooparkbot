import type { Animal, GameState } from '@/types';

/**
 * Планирование дохода на клиенте.
 *
 * Сервер — единственный источник правды по текущим `income_rub_per_min` и
 * `upkeep_rub_per_min`: в них уже зашиты местности, предметы, бонусы клана и
 * разнообразие видов, которые клиенту не пересчитать. Поэтому прогноз не считает
 * доход с нуля, а масштабирует серверные числа по мере того, как животные умирают:
 * доход падает пропорционально выбывшему вкладу, а процент содержания пересчитывается
 * по той же формуле, что и на сервере (см. UPKEEP_* в api/app/zoopark/catalog.py),
 * с поправкой на фактические скидки игрока.
 */

const UPKEEP_BASE_PERCENT = 5;
const UPKEEP_PERCENT_PER_LOG10_ANIMALS = 12;
const UPKEEP_MAX_PERCENT = 45;

/** Доля содержания от дохода при таком размере зоопарка, до скидок игрока. */
function upkeepPercent(animalCount: number): number {
  if (animalCount <= 0) return 0;
  return Math.min(UPKEEP_BASE_PERCENT + UPKEEP_PERCENT_PER_LOG10_ANIMALS * Math.log10(animalCount), UPKEEP_MAX_PERCENT);
}

export interface ForecastPoint {
  /** Момент, с которого действует этот темп (мс от начала прогноза). */
  atMs: number;
  animalCount: number;
  incomePerMin: number;
  upkeepPerMin: number;
  netPerMin: number;
}

export interface Forecast {
  /** Отрезки с постоянным темпом; границы — моменты смерти животных. */
  segments: ForecastPoint[];
  /** Ближайшая смерть после начала прогноза, если она есть. */
  nextDeathAtMs: number | null;
}

/**
 * Строит кусочно-постоянный график чистого дохода: он меняется только когда
 * умирает животное. Живые животные без срока смерти держат темп до бесконечности.
 */
export function buildForecast(gs: GameState, now: number = Date.now()): Forecast {
  const alive = gs.animals.filter(a => new Date(a.dies_at).getTime() > now);
  const totalIncome = alive.reduce((acc, a) => acc + a.income, 0);

  // Серверный доход учитывает больше факторов, чем сумма животных (и исключает тех, кто
  // в экспедиции). Держим его как истину на старте, а вклад каждого животного берём как
  // его долю в этой сумме.
  const scale = totalIncome > 0 ? gs.income_rub_per_min / totalIncome : 0;

  // Фактические скидки игрока на содержание — отношение того, что сервер насчитал, к
  // тому, что дала бы голая формула. Дальше это отношение считаем постоянным.
  const baselinePercent = upkeepPercent(alive.length);
  const actualPercent = gs.income_rub_per_min > 0
    ? (gs.upkeep_rub_per_min / gs.income_rub_per_min) * 100
    : 0;
  const discountRatio = baselinePercent > 0 ? actualPercent / baselinePercent : 1;

  const deaths = alive
    .map(a => ({ atMs: new Date(a.dies_at).getTime() - now, income: a.income }))
    .sort((a, b) => a.atMs - b.atMs);

  const segments: ForecastPoint[] = [];
  let remainingIncome = totalIncome;
  let remainingCount = alive.length;
  let cursor = 0;

  const pushSegment = (atMs: number) => {
    const income = Math.round(remainingIncome * scale);
    const upkeep = Math.round(income * Math.min(upkeepPercent(remainingCount) * discountRatio, UPKEEP_MAX_PERCENT) / 100);
    segments.push({
      atMs,
      animalCount: remainingCount,
      incomePerMin: income,
      upkeepPerMin: upkeep,
      netPerMin: income - upkeep,
    });
  };

  pushSegment(cursor);
  for (const death of deaths) {
    remainingIncome -= death.income;
    remainingCount -= 1;
    cursor = death.atMs;
    // Несколько смертей в одну миллисекунду — один отрезок, а не несколько нулевой длины.
    if (segments[segments.length - 1].atMs === cursor) segments.pop();
    pushSegment(cursor);
  }

  return { segments, nextDeathAtMs: deaths.length > 0 ? deaths[0].atMs : null };
}

/** Сколько накопится за `durationMs`, если ничего не делать. */
export function accumulate(forecast: Forecast, durationMs: number): number {
  let total = 0;
  for (let i = 0; i < forecast.segments.length; i += 1) {
    const segment = forecast.segments[i];
    if (segment.atMs >= durationMs) break;
    const next = forecast.segments[i + 1];
    const until = next ? Math.min(next.atMs, durationMs) : durationMs;
    total += segment.netPerMin * ((until - segment.atMs) / 60_000);
  }
  return Math.round(total);
}

/**
 * Через сколько накопится `target` сверх текущего баланса.
 * `null` — цель недостижима: доход иссякает раньше, чем она набирается.
 */
export function timeToTarget(forecast: Forecast, target: number, balance: number): number | null {
  let remaining = target - balance;
  if (remaining <= 0) return 0;

  for (let i = 0; i < forecast.segments.length; i += 1) {
    const segment = forecast.segments[i];
    if (segment.netPerMin <= 0) continue;
    const next = forecast.segments[i + 1];
    const spanMs = next ? next.atMs - segment.atMs : Number.POSITIVE_INFINITY;
    const earned = segment.netPerMin * (spanMs / 60_000);
    if (earned >= remaining) {
      return segment.atMs + (remaining / segment.netPerMin) * 60_000;
    }
    remaining -= earned;
  }
  return null;
}

/** Животные, чья смерть заметнее всего просадит доход в ближайшее время. */
export function biggestUpcomingLosses(gs: GameState, now: number = Date.now(), limit = 3): Animal[] {
  return gs.animals
    .filter(a => new Date(a.dies_at).getTime() > now)
    .sort((a, b) => b.income - a.income || new Date(a.dies_at).getTime() - new Date(b.dies_at).getTime())
    .slice(0, limit);
}
