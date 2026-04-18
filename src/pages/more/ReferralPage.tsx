import { useEffect, useState } from 'react';
import type { GameState, ReferralResponse } from '../../types';
import { apiGetReferrals, apiConfig } from '../../api';
import { fmt } from '../../utils/format';

export function ReferralPage({ gs: _gs }: { gs: GameState }) {
  const [data, setData] = useState<ReferralResponse | null>(null);
  const [botUsername, setBotUsername] = useState('ZooParkBot');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    Promise.all([
      apiGetReferrals(),
      apiConfig().catch(() => null),
    ]).then(([ref, cfg]) => {
      setData(ref);
      if (cfg?.bot_username) setBotUsername(cfg.bot_username);
    }).catch(e => setError((e as Error).message ?? 'Ошибка')).finally(() => setLoading(false));
  }, []);

  const refLink = data ? `https://t.me/${botUsername}?start=${data.code}` : '';

  const copyLink = () => {
    if (!refLink) return;
    navigator.clipboard.writeText(refLink).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {});
  };

  const shareLink = () => {
    if (!refLink) return;
    const text = encodeURIComponent('Играй в ZooPark — строй зоопарк, зарабатывай!');
    const url = encodeURIComponent(refLink);
    const tg = (window as { Telegram?: { WebApp?: { openLink?: (url: string) => void } } }).Telegram?.WebApp;
    const shareUrl = `https://t.me/share/url?url=${url}&text=${text}`;
    if (tg?.openLink) {
      tg.openLink(shareUrl);
    } else {
      window.open(shareUrl, '_blank');
    }
  };

  return (
    <div className="p-[14px] flex flex-col gap-3">
      {loading && <p className="text-center text-tg-hint">Загрузка...</p>}
      {error && <p className="text-[#ff6b63]">⚠️ {error}</p>}

      {data && (
        <>
          <div className="card">
            <p className="m-0 mb-[6px] font-bold">🤝 Твоя реферальная ссылка</p>
            <p className="m-0 mb-[10px] text-[13px] text-tg-hint">
              За каждого приглашённого — <strong className="text-[#ffd60a]">$ {fmt(data.reward_usd_per_ref)}</strong>
            </p>
            <div className="px-3 py-[10px] rounded-[10px] mb-[10px] bg-black/20 border border-white/[0.1] text-[13px] text-tg-hint break-all select-all">
              {refLink}
            </div>
            <div className="flex gap-2">
              <button
                onClick={copyLink}
                className="flex-1 py-3 rounded-[10px] border-none cursor-pointer font-bold text-sm text-white transition-all"
                style={{ background: copied ? '#34c759' : '#0a84ff' }}
              >
                {copied ? '✅ Скопировано' : '📋 Копировать'}
              </button>
              <button
                onClick={shareLink}
                className="flex-1 py-3 rounded-[10px] border-none cursor-pointer font-bold text-sm text-white"
                style={{ background: 'rgba(10,132,255,0.25)', color: '#0a84ff' }}
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
              <span className="font-bold text-[#ffd60a]">$ {fmt(data.total * data.reward_usd_per_ref)}</span>
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
