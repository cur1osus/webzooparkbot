import type { PackTier, PackTierInfo } from '@/types';

/**
 * Окупаемость пака: во что он обходится и что приносит.
 *
 * Считать доход будущего животного из его вида и генов клиент не может — они выпадают
 * случайно, а серверные множители сюда не приходят. Зато у игрока уже есть зоопарк:
 * среднее животное в нём заработано по тем же правилам, с теми же местностями, предметами
 * и бонусом разнообразия. Поэтому пак оценивается как «столько-то средних животных», а
 * цена — по тому же банковскому курсу, что и остальной калькулятор.
 */

export interface PackValue {
  tier: PackTier;
  unlocked: boolean;
  priceUsd: number;
  /** Среднее число животных в паке. */
  animals: number;
  /** Прирост чистого дохода, ₽/мин, с учётом подорожавшего содержания. */
  netGainPerMin: number;
  /** Цена в рублях за вычетом рублей и долларов, которые пак возвращает. */
  netCostRub: number;
  /** Через сколько окупится, мс. `null` — не окупится никогда: прироста нет. */
  paybackMs: number | null;
  /** Сколько эти животные принесут за свою жизнь, ₽. */
  lifetimeRub: number;
  /** Во сколько раз заработок за жизнь больше чистой цены. `null` — цена нулевая. */
  multiple: number | null;
}

export interface PackValueContext {
  /** Прирост чистого дохода от такого числа средних животных, ₽/мин. */
  netGainFor: (animals: number) => number;
  /** Во сколько рублей обходится покупка долларов в банке. */
  usdToRub: (usd: number) => number;
  /** Сколько живёт среднее животное этого игрока. */
  lifespanMs: number;
}

const mid = ([low, high]: [number, number]) => (low + high) / 2;

export function evaluatePack(tier: PackTierInfo, ctx: PackValueContext): PackValue {
  const animals = mid(tier.reward_range.animals);
  const netGainPerMin = ctx.netGainFor(animals);

  // Пак возвращает часть цены деньгами. Доллары из награды считаем по цене их покупки в
  // банке — столько рублей игроку не придётся менять.
  const cashBack = mid(tier.reward_range.rub) + ctx.usdToRub(Math.round(mid(tier.reward_range.usd)));
  const netCostRub = Math.max(Math.round(ctx.usdToRub(tier.price) - cashBack), 0);

  const lifetimeRub = Math.round(netGainPerMin * (ctx.lifespanMs / 60_000));
  return {
    tier: tier.tier,
    unlocked: tier.unlocked,
    priceUsd: tier.price,
    animals,
    netGainPerMin,
    netCostRub,
    paybackMs: netGainPerMin > 0 ? (netCostRub / netGainPerMin) * 60_000 : null,
    lifetimeRub,
    multiple: netCostRub > 0 ? lifetimeRub / netCostRub : null,
  };
}

/** Тир, который сейчас отбивает вложенное лучше всех — среди доступных к покупке. */
export function bestValueTier(values: PackValue[]): PackTier | null {
  const affordable = values.filter(v => v.unlocked && v.multiple !== null && v.multiple > 1);
  if (affordable.length === 0) return null;
  return affordable.reduce((best, v) => (v.multiple! > best.multiple! ? v : best)).tier;
}
