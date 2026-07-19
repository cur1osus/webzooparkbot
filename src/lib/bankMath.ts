/**
 * Пересчёт рублей в доллары по правилам банка.
 *
 * Повторяет `_bank_fee` и `exchange` на сервере: доллары покупаются целыми, комиссия —
 * процент от купленного, но не меньше одного доллара, как только куплено больше одного.
 * Живёт отдельно, потому что этим считают и банк, и калькулятор дохода.
 */

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
