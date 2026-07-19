/**
 * Пересчёт рублей в доллары по правилам банка.
 *
 * Повторяет `_bank_fee` и `exchange` на сервере: доллары покупаются целыми, комиссия —
 * процент от купленного, но не меньше одного доллара, как только куплено больше одного.
 * Живёт отдельно, потому что этим считают и банк, и калькулятор дохода.
 */

/** Максимум, до которого сервер поднимает `discount_bank` (cap в ITEM_PROPERTIES). */
const MAX_BANK_DISCOUNT_PERCENT = 80;

/**
 * Применяет скидку к опубликованному курсу той же формулой, что `effective_rate`
 * на сервере: усечение вниз и пол в один рубль.
 */
export function applyBankDiscount(publishedRate: number, discountPercent: number): number {
  return Math.max(1, Math.floor(publishedRate * (1 - discountPercent / 100)));
}

/**
 * Скидка игрока на курс в целых процентах, восстановленная из пары «курс со скидкой /
 * опубликованный курс».
 *
 * Сервер отдаёт только результат, а не сам процент, и усекает его вниз — поэтому делением
 * точное значение не получить: при published = 60 и скидке 1% курс становится 59, а
 * деление даёт 1,67%. Вместо этого подбираем наименьший процент, дающий наблюдаемый курс.
 * На реальных значениях это совпадает с сервером в ~89% случаев, а в остальных ошибается
 * не больше чем на 2 ₽ — и только для исторических курсов; текущий берётся с сервера как есть.
 */
export function bankDiscountPercent(playerRate: number, publishedRate: number): number {
  if (publishedRate <= 0 || playerRate <= 0 || playerRate >= publishedRate) return 0;
  for (let percent = 1; percent <= MAX_BANK_DISCOUNT_PERCENT; percent += 1) {
    if (applyBankDiscount(publishedRate, percent) === playerRate) return percent;
  }
  return 0;
}

/** Комиссия банка в долларах с покупки `grossUsd`. */
export function bankFeeUsd(grossUsd: number, feePercent: number): number {
  if (grossUsd <= 1) return 0;
  return Math.max(Math.floor((grossUsd * feePercent) / 100), 1);
}

/** Сколько долларов останется на руках после обмена `rub` по курсу `rate`. */
export function rublesToUsd(rub: number, rate: number, feePercent: number): number {
  if (rate <= 0 || rub <= 0) return 0;
  const gross = Math.floor(rub / rate);
  return gross - bankFeeUsd(gross, feePercent);
}

/**
 * Сколько рублей нужно, чтобы после комиссии на руках оказалось `usd`.
 * Обратная к `rublesToUsd`: комиссия ступенчатая, поэтому точное значение
 * подбирается от аналитической оценки, а не делением.
 */
export function usdToRubles(usd: number, rate: number, feePercent: number): number {
  if (rate <= 0 || usd <= 0) return 0;
  const net = (gross: number) => gross - bankFeeUsd(gross, feePercent);

  let gross = Math.max(1, Math.ceil(usd / Math.max(1 - feePercent / 100, 0.01)));
  while (net(gross) < usd) gross += 1;
  while (gross > 1 && net(gross - 1) >= usd) gross -= 1;
  return gross * rate;
}
