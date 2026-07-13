import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { GameState } from '@/types';
import { apiGetReferrals, apiConfig } from '@/api';
import { copyTmaText, shareTmaUrl } from '@/lib/tma';
import { fmt } from '@/utils/format';
import { buildBotLink, normalizeBotUsername } from '@/lib/botLinks';

export function ReferralPage({ gs }: { gs: GameState }) {
  const [copied, setCopied] = useState(false);
  const { data: queryData, error, isLoading } = useQuery({
    queryKey: ['referrals'],
    queryFn: async () => {
      const [referrals, config] = await Promise.all([
        apiGetReferrals(),
        apiConfig().catch(() => null),
      ]);
      return { referrals, config };
    },
    staleTime: 30_000,
  });

  const data = queryData?.referrals ?? null;
  const botUsername = normalizeBotUsername(queryData?.config?.bot_username);
  const refLink = data ? buildBotLink(botUsername, { startapp: data.code }) ?? '' : '';
  const inviterName = gs.nickname;

  const copyLink = async () => {
    if (!refLink) return;
    if (await copyTmaText(refLink)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const shareLink = () => {
    if (!refLink) return;
    void shareTmaUrl(refLink, 'Играй в ZooPark — строй зоопарк, зарабатывай!');
  };

  return (
    <div className="p-[14px] flex flex-col gap-3">
      {isLoading && <p className="text-center text-tg-hint">Загрузка...</p>}
      {error && <p className="text-[var(--c-red-soft)]">⚠️ {error instanceof Error ? error.message : 'Ошибка'}</p>}

      {data && (
        <>
          <section className="referral-hero" aria-labelledby="referral-title">
            <div className="referral-hero-orbit referral-hero-orbit-one" />
            <div className="referral-hero-orbit referral-hero-orbit-two" />
            <div className="referral-hero-top">
              <div className="min-w-0">
                <p className="referral-hero-kicker">🤝 Реферальная программа</p>
                <h3 id="referral-title" className="m-0 mt-2 text-[22px] leading-[1.08] font-black tracking-[-0.5px]">
                  Зови друзей.<br />Получай больше.
                </h3>
                <p className="m-0 mt-2 max-w-[210px] text-[12px] leading-[1.4]" style={{ color: 'rgba(255,248,236,0.68)' }}>
                  Друг зарегистрируется — ты получишь награду.
                </p>
              </div>
              <div className="referral-reward" aria-label={`${fmt(data.signup_reward_usd)}$ за каждого друга`}>
                <div className="referral-reward-amount">
                  <strong>{fmt(data.signup_reward_usd)}</strong>
                  <span className="referral-reward-sign">$</span>
                </div>
                <span>за друга</span>
              </div>
            </div>

            <div className="referral-steps" aria-label="Как работает реферальная программа">
              <div className="referral-step">
                <span className="referral-step-mark">1</span>
                <span>Поделись<br />ссылкой</span>
              </div>
              <div className="referral-step-line" />
              <div className="referral-step">
                <span className="referral-step-mark">2</span>
                <span>Друг<br />создаст профиль</span>
              </div>
              <div className="referral-step-line" />
              <div className="referral-step">
                <span className="referral-step-mark referral-step-mark-gold">$</span>
                <span>Награда<br />тебе</span>
              </div>
            </div>
          </section>

          <section className="card referral-link-card">
            <div className="flex items-start justify-between gap-3 mb-[10px]">
              <div>
                <p className="m-0 font-bold">Твоя ссылка</p>
                <p className="m-0 mt-1 text-[12px] text-tg-hint">Приглашает от имени {inviterName}</p>
              </div>
            </div>
            <div className="surface-subtle px-3 py-[10px] rounded-[10px] mb-[10px] text-[12px] text-tg-hint break-all select-all">
              {refLink || 'Ссылка загружается…'}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => void copyLink()}
                disabled={!refLink}
                className="flex-1 py-3 rounded-[10px] border-none cursor-pointer font-bold text-sm text-[var(--tg-theme-button-text-color)] transition-all"
                style={{
                  background: copied ? 'var(--c-green)' : 'var(--c-gold)',
                  color: copied ? 'var(--tg-theme-button-text-color)' : '#241c08',
                }}
              >
                {copied ? '✅ Скопировано' : '📋 Копировать'}
              </button>
              <button
                onClick={shareLink}
                disabled={!refLink}
                className="flex-1 py-3 rounded-[10px] border-none cursor-pointer font-bold text-sm"
                style={{
                  background: 'rgba(var(--c-gold-rgb),0.16)',
                  border: '1px solid rgba(var(--c-gold-rgb),0.32)',
                  color: 'var(--c-gold)',
                }}
              >
                🔗 Поделиться
              </button>
            </div>
          </section>

          <section className="card referral-stats-card">
            <p className="m-0 mb-[10px] text-[11px] font-bold text-tg-hint tracking-[0.8px] uppercase">Твоя статистика</p>
            <div className="referral-stat-grid">
              <div className="referral-stat">
                <span className="referral-stat-icon">👥</span>
                <div>
                  <strong>{data.total}</strong>
                  <span>приглашено</span>
                </div>
              </div>
              <div className="referral-stat referral-stat-highlight">
                <span className="referral-stat-icon">💰</span>
                <div>
                  <strong>{fmt(data.total * data.signup_reward_usd)}$</strong>
                  <span>заработано</span>
                </div>
              </div>
            </div>
          </section>

          {data.referred.length > 0 && (
            <section className="card">
              <div className="flex items-center justify-between mb-2">
                <p className="m-0 font-bold">Приглашённые</p>
                <span className="text-[11px] font-bold text-tg-hint">{data.referred.length} чел.</span>
              </div>
              {data.referred.map((nick, i) => (
                <div key={i} className="flex items-center gap-2 py-[5px] border-b last:border-b-0" style={{ borderColor: 'var(--surface-overlay-border)' }}>
                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-[11px]" style={{ background: 'rgba(var(--c-gold-rgb),0.14)', color: 'var(--c-gold)' }}>✓</span>
                  <span className="text-[13px]">{nick}</span>
                </div>
              ))}
            </section>
          )}
        </>
      )}
    </div>
  );
}
