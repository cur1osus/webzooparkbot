import type { GameState } from '@/types';

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
  /**
   * Во сколько раз фактическое содержание отличается от того, что даёт голая формула, —
   * скидки игрока. Прогноз считает его постоянным, поэтому его же применяет и оценка
   * покупок: новые животные попадают под те же скидки.
   */
  upkeepDiscountRatio: number;
}

/** Темп при таком составе зоопарка — общая формула прогноза и оценки покупок. */
function rateFor(income: number, animalCount: number, discountRatio: number) {
  const upkeep = Math.round(income * Math.min(upkeepPercent(animalCount) * discountRatio, UPKEEP_MAX_PERCENT) / 100);
  return { incomePerMin: income, upkeepPerMin: upkeep, netPerMin: income - upkeep };
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
    segments.push({
      atMs,
      animalCount: remainingCount,
      ...rateFor(Math.round(remainingIncome * scale), remainingCount, discountRatio),
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

  return {
    segments,
    nextDeathAtMs: deaths.length > 0 ? deaths[0].atMs : null,
    upkeepDiscountRatio: discountRatio,
  };
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

/** Отрезок, действующий в момент `atMs` от начала прогноза. */
function segmentAt(forecast: Forecast, atMs: number): ForecastPoint | null {
  let current: ForecastPoint | null = null;
  for (const segment of forecast.segments) {
    if (segment.atMs > atMs) break;
    current = segment;
  }
  return current;
}

export interface Decline {
  /** Сколько животных умрёт за горизонт. */
  deaths: number;
  netNow: number;
  netThen: number;
  /** Насколько упадёт чистый доход, ₽/мин. */
  lostNet: number;
  /** Та же просадка в процентах от нынешнего темпа. */
  percent: number;
  /**
   * Сколько животных средней для этого зоопарка доходности нужно завести за горизонт,
   * чтобы удержать темп. Считается по грязному доходу: содержание от размера зоопарка
   * не зависит линейно, а замещать надо именно выбывший заработок.
   */
  replacements: number;
}

/** Насколько просядет доход за `horizonMs`, если ничего не покупать. */
export function declineOver(forecast: Forecast, horizonMs: number): Decline {
  const start = forecast.segments[0];
  const end = segmentAt(forecast, horizonMs) ?? start;
  if (!start) {
    return { deaths: 0, netNow: 0, netThen: 0, lostNet: 0, percent: 0, replacements: 0 };
  }

  const lostIncome = start.incomePerMin - end.incomePerMin;
  const perAnimal = start.animalCount > 0 ? start.incomePerMin / start.animalCount : 0;
  const lostNet = Math.max(start.netPerMin - end.netPerMin, 0);
  return {
    deaths: start.animalCount - end.animalCount,
    netNow: start.netPerMin,
    netThen: end.netPerMin,
    lostNet,
    percent: start.netPerMin > 0 ? Math.round((lostNet / start.netPerMin) * 100) : 0,
    replacements: perAnimal > 0 ? Math.ceil(lostIncome / perAnimal) : 0,
  };
}

/**
 * Прирост чистого дохода от `count` новых животных со средней для этого зоопарка
 * доходностью. Не просто сумма их дохода: с ростом поголовья дорожает содержание, и
 * последние животные приносят меньше первых.
 */
export function netGainFromAnimals(forecast: Forecast, count: number): number {
  const start = forecast.segments[0];
  if (!start || start.animalCount <= 0 || count <= 0) return 0;
  const perAnimal = start.incomePerMin / start.animalCount;
  const grown = rateFor(
    start.incomePerMin + perAnimal * count,
    start.animalCount + count,
    forecast.upkeepDiscountRatio,
  );
  return Math.max(grown.netPerMin - start.netPerMin, 0);
}

/** Продолжительность жизни животного при среднем гене выживаемости (LIFESPAN_DAYS). */
const FALLBACK_LIFESPAN_MS = 8 * 24 * 60 * 60_000;

/**
 * Сколько живёт животное этого игрока — среднее по всему зоопарку, от появления до
 * смерти. Срок задаётся геном выживаемости при рождении и никогда не меняется, поэтому
 * прошлые животные — честная оценка для будущих.
 */
export function averageLifespanMs(gs: GameState): number {
  const spans = gs.animals
    .map(a => new Date(a.dies_at).getTime() - new Date(a.acquired_at).getTime())
    .filter(ms => ms > 0);
  if (spans.length === 0) return FALLBACK_LIFESPAN_MS;
  return spans.reduce((acc, ms) => acc + ms, 0) / spans.length;
}
