import { useEffect, useState } from 'react';
import type { GameState, ReferralResponse } from '../../types';
import { apiGetReferrals, apiConfig } from '../../api';
import { copyTmaText, shareTmaUrl } from '../../tma';
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
      {loading && <p className="text-center text-tg-hint">Загрузка...</p>}
      {error && <p className="text-[var(--c-red-soft)]">⚠️ {error}</p>}

      {data && (
        <>
          <div className="card">
            <p className="m-0 mb-[6px] font-bold">🤝 Твоя реферальная ссылка</p>
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
