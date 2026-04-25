import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { GameState } from '@/types';
import { apiGetReferrals, apiConfig } from '@/api';
import { copyTmaText, shareTmaUrl } from '@/lib/tma';
import { fmt } from '@/utils/format';

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
  const botUsername = queryData?.config?.bot_username ?? 'ZooParkBot';
  const refLink = data ? `https://t.me/${botUsername}?start=${data.code}` : '';
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
          <div className="card">
            <p className="m-0 mb-[6px] font-bold">🤝 Реферальная ссылка {inviterName}</p>
            <p className="m-0 mb-[10px] text-[13px] text-tg-hint">
              За каждого приглашённого — <strong className="text-[var(--c-gold)]">$ {fmt(data.reward_usd_per_ref)}</strong>
            </p>
            <div className="surface-subtle px-3 py-[10px] rounded-[10px] mb-[10px] text-[13px] text-tg-hint break-all select-all">
              {refLink}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => void copyLink()}
                className="flex-1 py-3 rounded-[10px] border-none cursor-pointer font-bold text-sm text-[var(--tg-theme-button-text-color)] transition-all"
                style={{ background: copied ? 'var(--c-green)' : 'var(--c-blue)' }}
              >
                {copied ? '✅ Скопировано' : '📋 Копировать'}
              </button>
              <button
                onClick={shareLink}
                className="flex-1 py-3 rounded-[10px] border-none cursor-pointer font-bold text-sm"
                style={{ background: 'rgba(var(--c-blue-rgb),0.25)', color: 'var(--c-blue)' }}
              >
                🔗 Поделиться
              </button>
            </div>
          </div>

          <div className="card">
            <p className="m-0 mb-[10px] font-bold">Статистика</p>
            <div className="flex justify-between mb-[6px]">
              <span className="text-[13px] text-tg-hint">Приглашено</span>
              <span className="font-bold">{data.total}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[13px] text-tg-hint">Заработано</span>
              <span className="font-bold text-[var(--c-gold)]">$ {fmt(data.total * data.reward_usd_per_ref)}</span>
            </div>
          </div>

          {data.referred.length > 0 && (
            <div className="card">
              <p className="m-0 mb-2 font-bold">Приглашённые ({data.referred.length})</p>
              {data.referred.map((nick, i) => (
                <div key={i} className="flex items-center gap-2 mb-1">
                  <span className="text-tg-hint text-[13px]">·</span>
                  <span className="text-[13px]">{nick}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
