import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { GameState } from '@/types';
import { apiGetDonateInfo, apiCreateDonateInvoice, apiSyncSocialRewards } from '@/api';
import { openTmaLink } from '@/lib/tma';

const STAR_OPTIONS = [1, 5, 10, 25, 50, 100, 250, 500];

export function DonatePage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [stars, setStars] = useState<number | null>(null);
  const [buying, setBuying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { data: donateInfo } = useQuery({
    queryKey: ['donate-info'],
    queryFn: apiGetDonateInfo,
    staleTime: 60_000,
  });
  const {
    data: socialRewards,
    isLoading: socialRewardsLoading,
    error: socialRewardsError,
    refetch: refetchSocialRewards,
  } = useQuery({
    queryKey: ['social-rewards'],
    queryFn: async () => {
      const result = await apiSyncSocialRewards();
      onRefresh();
      return result;
    },
    staleTime: 30_000,
    retry: false,
  });
  const starsToPaw = donateInfo?.stars_to_paw ?? 10;
  const socialTargets = socialRewards?.targets ?? [];
  const socialTotal = socialTargets.reduce((sum, target) => sum + target.reward, 0);
  const socialJoined = socialTargets.filter(target => target.joined).length;
  const socialComplete = socialTargets.length > 0 && socialJoined === socialTargets.length;

  const handleDonate = async () => {
    if (!stars) return;
    setBuying(true);
    setError(null);
    try {
      const res = await apiCreateDonateInvoice(stars);
      if (res.invoice_link) {
        openTmaLink(res.invoice_link);
      }
    } catch (e) {
      setError((e as Error).message ?? 'Ошибка');
    } finally {
      setBuying(false);
    }
  };

  return (
    <div className="p-[14px] flex flex-col gap-3">
      <div className="card text-center">
        <span className="text-[48px]">⭐️</span>
        <p className="mt-[10px] mb-1 text-lg font-extrabold">Донат Telegram Stars</p>
        <p className="m-0 text-[13px] text-tg-hint">
          1 ⭐️ = {starsToPaw} 🐾 PawCoins · Поддержи игру!
        </p>
        <p className="mt-2 mb-0 text-xs text-tg-hint">На балансе: {gs.paw_coins} 🐾</p>
      </div>

      {socialRewards?.enabled !== false && (
        <section className="social-reward-card">
          <div className="social-reward-heading">
            <span className="social-reward-mark" aria-hidden="true">📣</span>
            <div className="min-w-0 flex-1">
              <h2 className="m-0 text-[16px] font-black">Поддержка ZooPark</h2>
              <p className="m-0 mt-1 text-[11px] text-tg-hint">Подпишись — получи PawCoins</p>
            </div>
            <strong className="social-reward-total">+{socialTotal || 100} 🐾</strong>
          </div>

          {socialRewardsLoading && <p className="m-0 mt-3 text-[12px] text-tg-hint">Проверяем подписки…</p>}
          {socialRewardsError && (
            <p className="m-0 mt-3 text-[12px] text-[var(--c-red-soft)]">Не удалось проверить подписки. Попробуй ещё раз.</p>
          )}
          {!socialRewardsLoading && !socialRewardsError && socialTargets.length > 0 && (
            <div className="social-reward-list">
              {socialTargets.map(target => (
                <button
                  key={target.key}
                  type="button"
                  className={`social-reward-row${target.joined ? ' is-joined' : ''}`}
                  disabled={target.joined}
                  onClick={() => openTmaLink(target.url)}
                >
                  <span className="social-reward-check" aria-hidden="true">{target.joined ? '✓' : '↗'}</span>
                  <span className="social-reward-name">{target.title}</span>
                  <span className="social-reward-amount">{target.joined ? 'Подписан' : `+${target.reward} 🐾`}</span>
                </button>
              ))}
            </div>
          )}
          {!socialRewardsLoading && !socialRewardsError && (
            <div className={`social-reward-footer${socialComplete ? ' is-complete' : ''}`}>
              <span>{socialComplete ? 'Награда начислена' : `${socialJoined} из ${socialTargets.length} подписок`}</span>
              <button type="button" onClick={() => void refetchSocialRewards()} className="social-reward-refresh">
                Проверить
              </button>
            </div>
          )}
        </section>
      )}

      <div className="card">
        <p className="m-0 mb-[10px] font-bold">Выбери количество звёзд:</p>

        <div className="grid grid-cols-4 gap-2">
          {STAR_OPTIONS.map(s => (
            <button
              key={s}
              onClick={() => setStars(s)}
              className="py-[10px] px-1 rounded-[10px] cursor-pointer text-[13px] transition-all"
              style={{
                background: stars === s ? 'rgba(var(--c-gold-rgb),0.2)' : 'var(--surface-subtle)',
                color: stars === s ? 'var(--c-gold)' : 'var(--tg-theme-hint-color)',
                fontWeight: stars === s ? 700 : 400,
                border: `1px solid ${stars === s ? 'rgba(var(--c-gold-rgb),0.4)' : 'transparent'}`,
              }}
            >
              ⭐️ {s}
            </button>
          ))}
        </div>

        {stars && (
          <div className="surface-subtle mt-3 px-3 py-[10px] rounded-[10px]">
            <p className="m-0 text-[13px] text-tg-hint">За {stars} ⭐️ получишь:</p>
            <p className="mt-1 mb-0 text-lg font-extrabold text-[var(--c-purple)]">
              {stars * starsToPaw} 🐾 PawCoins
            </p>
          </div>
        )}

        {error && <p className="mt-2 mb-0 text-[var(--c-red-soft)] text-[13px]">⚠️ {error}</p>}

        <button
          onClick={() => void handleDonate()}
          disabled={!stars || buying}
          className="w-full py-[13px] rounded-[10px] border-none cursor-pointer font-extrabold text-[15px] mt-3 disabled:opacity-60 transition-all"
          style={{
            background: stars ? 'var(--c-gold)' : 'var(--surface-subtle)',
            color: stars ? '#1c1c1e' : 'var(--tg-theme-hint-color)',
          }}
        >
          {buying ? 'Открываем...' : stars ? `⭐️ Задонатить ${stars} звёзд` : 'Выбери количество'}
        </button>
      </div>

      <div className="card">
        <p className="m-0 mb-[6px] font-bold text-[13px]">Что дают PawCoins?</p>
        {[
          '⚒️ Создание предметов в кузнице',
          '💊 Лечение больных животных',
          '🎮 Особые игровые бонусы',
        ].map(item => (
          <p key={item} className="mt-1 mb-0 text-[13px] text-tg-hint">{item}</p>
        ))}
      </div>
    </div>
  );
}
