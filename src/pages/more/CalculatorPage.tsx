import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { GameState } from '@/types';
import { fmt } from '@/utils/format';
import { SPECIES_RARITY_META } from '@/data/packs';
import { AnimalArt } from '@/components/AnimalArt';
import { apiGetBank } from '@/api';
import { applyBankDiscount, bankDiscountPercent, rublesToUsd, usdToRubles } from '@/lib/bankMath';
import { accumulate, biggestUpcomingLosses, buildForecast, timeToTarget } from '@/lib/incomeForecast';

type RateMode = 'current' | 'best' | 'average';

const RATE_MODES: { id: RateMode; label: string }[] = [
  { id: 'current', label: 'Сейчас' },
  { id: 'best',    label: 'Лучший' },
  { id: 'average', label: 'Средний' },
];

const HORIZONS: { label: string; ms: number }[] = [
  { label: 'Час',     ms: 60 * 60_000 },
  { label: 'Сутки',   ms: 24 * 60 * 60_000 },
  { label: 'Неделя',  ms: 7 * 24 * 60 * 60_000 },
];

function fmtDuration(ms: number): string {
  const minutes = Math.ceil(ms / 60_000);
  if (minutes < 60) return `${minutes} мин`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    const rest = minutes % 60;
    return rest > 0 ? `${hours} ч ${rest} мин` : `${hours} ч`;
  }
  const days = Math.floor(hours / 24);
  const restHours = hours % 24;
  return restHours > 0 ? `${days} д ${restHours} ч` : `${days} д`;
}

export function CalculatorPage({ gs }: { gs: GameState }) {
  const [goal, setGoal] = useState('');
  const [goalCurrency, setGoalCurrency] = useState<'rub' | 'usd'>('rub');
  const [rateMode, setRateMode] = useState<RateMode>('current');

  // Тот же ключ, что и на странице банка — курс переиспользуется из кэша, лишнего запроса нет.
  const { data: bank = null } = useQuery({
    queryKey: ['bank'],
    queryFn: apiGetBank,
    staleTime: 55_000,
  });

  // Точку отсчёта держим в состоянии, а не читаем часы на каждый рендер: иначе прогноз
  // «плыл» бы при каждом введённом символе. Раз в минуту подтягиваем — сроки жизни тикают.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 60_000);
    return () => window.clearInterval(timer);
  }, []);

  const forecast = useMemo(() => buildForecast(gs, now), [gs, now]);
  const losses = useMemo(() => biggestUpcomingLosses(gs, now), [gs, now]);

  const net = forecast.segments[0]?.netPerMin ?? 0;

  // Курс скачет между 60 и 130 ₽, поэтому «сколько это в долларах» зависит от того, в
  // какую минуту менять. Лучший и средний считаем по той же истории, что рисует банк.
  //
  // История — это опубликованные курсы, без предметов `discount_bank`, тогда как
  // `rate_rub_per_usd` уже со скидкой. Сравнивать их напрямую нельзя, поэтому к истории
  // применяется та же скидка и та же формула, что на сервере (`effective_rate`).
  const { rates, discountPercent } = useMemo(() => {
    const current = bank?.rate_rub_per_usd ?? 0;
    const published = bank?.base_rate_rub_per_usd ?? 0;
    const percent = bankDiscountPercent(current, published);
    const discounted = (rate: number) => applyBankDiscount(rate, percent);

    const history = bank?.history ?? [];
    if (history.length === 0) {
      return { rates: { current, best: current, average: current }, discountPercent: percent };
    }
    const values = history.map(p => discounted(p.rate));
    return {
      rates: {
        current,
        // Дешевле рубль за доллар — выгоднее покупка, поэтому лучший курс это минимум.
        best: Math.min(...values),
        average: Math.round(values.reduce((acc, r) => acc + r, 0) / values.length),
      },
      discountPercent: percent,
    };
  }, [bank]);

  const rate = rates[rateMode];
  const feePercent = bank?.fee_percent ?? 0;
  const toUsd = (rub: number) => rublesToUsd(rub, rate, feePercent);
  const goalValue = Number(goal.replace(/\s/g, ''));
  const goalReady = goal.trim() !== '' && Number.isFinite(goalValue) && goalValue > 0;

  // Долларовая цель считается через банк: копим рубли, потом меняем. Доллары, которые уже
  // на руках, доменивать не нужно — в рубли переводится только нехватка.
  const usdShortfall = Math.max(goalValue - gs.usd, 0);
  // Сколько рублей нужно иметь всего; накопленный рублёвый баланс тоже идёт в дело.
  const goalRub = goalCurrency === 'usd' ? usdToRubles(usdShortfall, rate, feePercent) : goalValue;
  const etaMs = !goalReady || (goalCurrency === 'usd' && rate <= 0)
    ? null
    : goalCurrency === 'usd' && usdShortfall === 0
      ? 0
      : timeToTarget(forecast, goalRub, gs.rub);

  return (
    <div className="p-[14px] flex flex-col gap-3">
      <div className="card">
        <p className="m-0 text-[11px] font-extrabold text-tg-hint tracking-[1px] uppercase">Сейчас</p>
        <p className="m-0 mt-1 text-[26px] font-black leading-none tabular-nums"
           style={{ color: net >= 0 ? 'var(--c-green)' : 'var(--c-red-soft)' }}>
          {net >= 0 ? '+' : '−'}₽{fmt(Math.abs(net))}<span className="text-[14px] font-bold">/мин</span>
        </p>
        <p className="m-0 mt-2 text-[12px] text-tg-hint">
          Доход ₽{fmt(gs.income_rub_per_min)} − содержание ₽{fmt(gs.upkeep_rub_per_min)} · {gs.live_animals_count} животных
        </p>
      </div>

      <div className="card">
        <p className="m-0 text-[13px] font-extrabold">Сколько накопится</p>
        <p className="m-0 mt-1 text-[11px] text-tg-hint leading-[1.4]">
          С учётом того, что животные умирают и доход по пути падает.
        </p>
        {rate > 0 && (
          <div className="mt-3 grid grid-cols-3 gap-1" role="tablist" aria-label="Курс для пересчёта в доллары">
            {RATE_MODES.map(m => {
              const active = m.id === rateMode;
              return (
                <button
                  key={m.id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => setRateMode(m.id)}
                  className="min-w-0 min-h-10 rounded-xl px-1 leading-tight cursor-pointer transition-colors"
                  style={{
                    background: active ? 'color-mix(in srgb, var(--c-gold) 18%, transparent)' : 'color-mix(in srgb, var(--tg-theme-hint-color) 9%, transparent)',
                    color: active ? 'var(--c-gold)' : 'var(--tg-theme-hint-color)',
                    border: `1px solid ${active ? 'color-mix(in srgb, var(--c-gold) 40%, transparent)' : 'transparent'}`,
                  }}
                >
                  <span className="block text-[10px] font-semibold">{m.label}</span>
                  <span className="block text-[12px] font-extrabold tabular-nums">₽{fmt(rates[m.id])}</span>
                </button>
              );
            })}
          </div>
        )}
        <div className="mt-2 flex flex-col gap-2">
          {HORIZONS.map(h => {
            const earned = accumulate(forecast, h.ms);
            return (
              <div key={h.label} className="flex items-center justify-between gap-2 rounded-xl px-3 py-[10px]"
                   style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)' }}>
                <span className="text-[12px] font-bold text-tg-hint">{h.label}</span>
                <span className="text-right">
                  <span className="block text-[14px] font-extrabold tabular-nums" style={{ color: 'var(--c-green)' }}>
                    +₽{fmt(earned)}
                  </span>
                  {rate > 0 && (
                    <span className="block text-[11px] font-bold tabular-nums" style={{ color: 'var(--c-gold)' }}>
                      ≈ ${fmt(toUsd(earned))}
                    </span>
                  )}
                </span>
              </div>
            );
          })}
        </div>
        <p className="m-0 mt-2 text-[10.5px] text-tg-hint leading-[1.4]">
          Баланс через неделю: ₽{fmt(gs.rub + accumulate(forecast, HORIZONS[2].ms))}
          {rate > 0 && ` · ≈ $${fmt(toUsd(gs.rub + accumulate(forecast, HORIZONS[2].ms)))}`}
        </p>
        {rate > 0 && (
          <p className="m-0 mt-1 text-[10.5px] text-tg-hint leading-[1.4]">
            Доллары посчитаны с комиссией банка {feePercent}%. Лучший и средний — по недавней истории курса.
            {discountPercent > 0 && ` Твоя скидка на курс ${discountPercent}% уже учтена.`}
          </p>
        )}
      </div>

      <div className="card">
        <div className="flex items-center justify-between gap-2">
          <p className="m-0 text-[13px] font-extrabold">Когда накоплю на цель</p>
          {rate > 0 && (
            <div className="flex gap-1 shrink-0" role="tablist" aria-label="Валюта цели">
              {(['rub', 'usd'] as const).map(c => {
                const active = c === goalCurrency;
                return (
                  <button
                    key={c}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    onClick={() => setGoalCurrency(c)}
                    className="min-h-8 min-w-9 rounded-lg text-[13px] font-extrabold cursor-pointer transition-colors"
                    style={{
                      background: active ? 'color-mix(in srgb, var(--c-gold) 18%, transparent)' : 'color-mix(in srgb, var(--tg-theme-hint-color) 9%, transparent)',
                      color: active ? 'var(--c-gold)' : 'var(--tg-theme-hint-color)',
                      border: `1px solid ${active ? 'color-mix(in srgb, var(--c-gold) 40%, transparent)' : 'transparent'}`,
                    }}
                  >
                    {c === 'rub' ? '₽' : '$'}
                  </button>
                );
              })}
            </div>
          )}
        </div>
        <label className="mt-2 flex items-center gap-2 min-h-11 rounded-xl px-3"
               style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 14%, transparent)' }}>
          <span className="text-[14px] font-bold text-tg-hint">{goalCurrency === 'rub' ? '₽' : '$'}</span>
          <input
            value={goal}
            onChange={e => setGoal(e.target.value.replace(/[^\d\s]/g, ''))}
            inputMode="numeric"
            placeholder={goalCurrency === 'rub' ? 'Сумма, например 500000' : 'Сумма, например 5000'}
            aria-label="Целевая сумма"
            className="min-w-0 flex-1 bg-transparent border-none outline-none text-[14px] tabular-nums"
          />
          {goal && (
            <button type="button" onClick={() => setGoal('')} aria-label="Очистить"
                    className="border-none bg-transparent text-[16px] cursor-pointer" style={{ color: 'var(--tg-theme-hint-color)' }}>×</button>
          )}
        </label>
        {goalReady && (
          <div className="mt-3">
            {etaMs === null ? (
              <p className="m-0 text-[13px] font-bold" style={{ color: 'var(--c-amber)' }}>
                Так долго зоопарк не проживёт — животные умрут раньше. Нужны новые.
              </p>
            ) : etaMs === 0 ? (
              <p className="m-0 text-[13px] font-bold" style={{ color: 'var(--c-green)' }}>
                {goalCurrency === 'rub'
                  ? `Уже накоплено — на балансе ₽${fmt(gs.rub)}.`
                  : usdShortfall === 0
                    ? `Уже накоплено — на балансе $${fmt(gs.usd)}.`
                    : `Хватает рублей — можно менять прямо сейчас, ₽${fmt(goalRub)} по курсу ₽${fmt(rate)}.`}
              </p>
            ) : (
              <>
                <p className="m-0 text-[20px] font-black leading-none" style={{ color: 'var(--c-gold)' }}>
                  {fmtDuration(etaMs)}
                </p>
                <p className="m-0 mt-1 text-[11px] text-tg-hint">
                  Не хватает ₽{fmt(goalRub - gs.rub)} · при текущем темпе ₽{fmt(net)}/мин
                </p>
                {goalCurrency === 'usd' && (
                  <p className="m-0 mt-1 text-[11px] text-tg-hint">
                    ${fmt(usdShortfall)} по курсу ₽{fmt(rate)} — это ₽{fmt(goalRub)} с комиссией {feePercent}%
                    {gs.usd > 0 && ` · $${fmt(gs.usd)} уже есть`}
                  </p>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {losses.length > 0 && (
        <div className="card">
          <p className="m-0 text-[13px] font-extrabold">Что просядет первым</p>
          <p className="m-0 mt-1 text-[11px] text-tg-hint leading-[1.4]">
            Самые доходные животные и сколько им осталось.
          </p>
          <div className="mt-3 flex flex-col gap-2">
            {losses.map(a => {
              const leftMs = new Date(a.dies_at).getTime() - now;
              const rarityColor = SPECIES_RARITY_META[a.species_rarity].color;
              return (
                <div key={a.id} className="flex items-center gap-[10px] rounded-xl px-3 py-2"
                     style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)' }}>
                  <span className="w-9 h-9 rounded-xl grid place-items-center shrink-0 overflow-hidden"
                        style={{ background: `${rarityColor}18`, border: `1px solid ${rarityColor}35` }}>
                    <AnimalArt animal={a} size={32} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="m-0 text-[12.5px] font-bold truncate">{a.name}</p>
                    <p className="m-0 text-[11px] text-tg-hint truncate">−₽{fmt(a.income)}/мин через {fmtDuration(leftMs)}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <p className="m-0 px-1 text-[10.5px] text-tg-hint leading-[1.45]">
        Прогноз считается от текущего дохода и сроков жизни животных. Новые звери, лечение,
        улучшения местностей и бонусы его меняют — это оценка, а не обещание.
      </p>
    </div>
  );
}
