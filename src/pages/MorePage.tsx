import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { createPortal } from 'react-dom';
import type { GameState, TransferOut } from '@/types';
import { BankPage } from './BankPage';
import { BonusPage } from './more/BonusPage';
import { MerchantPage } from './more/MerchantPage';
import { ClanPage } from './more/ClanPage';
import { TopPage } from './more/TopPage';
import { ReferralPage } from './more/ReferralPage';
import { DonatePage } from './more/DonatePage';
import { apiConfig, apiCreateTransfer, apiGetBonus, apiGetMyTransfers } from '@/api';
import { fmt, formatDateShort } from '@/utils/format';
import { copyTmaText, inTma } from '@/lib/tma';
import { PageHeader } from '@/components/PageHeader';
import { AdminPage } from '@/pages/AdminPage';

type Section =
  | 'bank' | 'bonus' | 'merchant' | 'clan' | 'top'
  | 'referral' | 'donate' | 'giveaway' | 'wiki' | 'admin' | null;

type SectionId = Exclude<Section, null>;

const MENU_GROUPS = [
  {
    label: 'Экономика',
    items: [
      { id: 'bank',     emoji: '🏦',  title: 'Банк',               desc: 'Обмен рублей и долларов' },
      { id: 'bonus',    emoji: '🎁',  title: 'Ежедневный бонус',   desc: 'Рубли, доллары, лапки' },
      { id: 'merchant', emoji: '🧙',  title: 'Случайный торговец', desc: 'Животные со скидкой' },
      { id: 'giveaway', emoji: '💸',  title: 'Раздача денег',      desc: 'Создай ссылку и раздели' },
    ],
  },
  {
    label: 'Сообщество',
    items: [
      { id: 'clan',     emoji: '🏰',  title: 'Клан',               desc: 'Создай клан или вступи в чужой' },
      { id: 'top',      emoji: '📊',  title: 'Таблица лидеров',    desc: 'Топ-20 по доходу' },
      { id: 'referral', emoji: '🤝',  title: 'Рефералы',           desc: 'Приглашай и зарабатывай' },
    ],
  },
  {
    label: 'Прочее',
    items: [
      { id: 'donate',   emoji: '⭐️', title: 'Донат',              desc: '1 ⭐️ = PawCoins' },
      { id: 'wiki',     emoji: '📖',  title: 'База знаний',        desc: 'Механики и гайды' },
    ],
  },
] as const;

function MoreSectionLayer({ title, onBack, children }: { title: string; onBack: () => void; children: React.ReactNode }) {
  const topOffset = inTma ? '0px' : '48px';

  return createPortal(
    <div
      className="fixed left-1/2 -translate-x-1/2 w-full max-w-[480px] bg-tg-bg z-[90]"
      style={{ top: topOffset, bottom: 'var(--app-bottom-offset)' }}
    >
      <div className="h-full flex flex-col" style={{ paddingTop: 'var(--safe-top)' }}>
        <div className="px-[14px] pt-[14px] pb-[10px] flex items-center gap-3 border-b bg-tg-bg/95 backdrop-blur-xl shrink-0" style={{ borderColor: 'var(--surface-overlay-border)' }}>
          <button
            onClick={onBack}
            className="flex items-center gap-1 px-3 py-[6px] rounded-lg border bg-transparent text-tg-text cursor-pointer text-[13px] shrink-0"
            style={{ borderColor: 'var(--surface-overlay-border)' }}
          >
            ‹ Назад
          </button>
          <h2 className="m-0 text-base font-bold flex-1 min-w-0">{title}</h2>
        </div>

        <div className="flex-1 overflow-y-auto overscroll-contain">
          <div className="min-h-full pb-4">
            {children}
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}

export function MorePage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [section, setSection] = useState<Section>(null);
  const [botUsername, setBotUsername] = useState('ZooParkBot');
  // Whether today's bonus is still unclaimed is server state, not something the game
  // state carries around: `gs.bonus` was a column that stopped being the source of truth.
  const { data: bonusOffer = null } = useQuery({ queryKey: ['bonus'], queryFn: apiGetBonus });

  useEffect(() => {
    apiConfig()
      .then((config) => {
        if (config.bot_username) setBotUsername(config.bot_username);
      })
      .catch(() => {});
  }, []);

  const back = () => setSection(null);
  const openSection = (nextSection: SectionId) => setSection(nextSection);

  if (section === 'bank') return (
    <MoreSectionLayer title="🏦 Банк" onBack={back}>
      <BankPage gs={gs} onRefresh={onRefresh} />
    </MoreSectionLayer>
  );

  if (section === 'bonus') return (
    <MoreSectionLayer title="🎁 Ежедневный бонус" onBack={back}>
      <BonusPage onClaim={onRefresh} />
    </MoreSectionLayer>
  );

  if (section === 'merchant') return (
    <MoreSectionLayer title="🧙 Случайный торговец" onBack={back}>
      <MerchantPage gs={gs} onBuy={onRefresh} />
    </MoreSectionLayer>
  );

  if (section === 'clan') return (
    <MoreSectionLayer title="🏰 Клан" onBack={back}>
      <ClanPage gs={gs} onRefresh={onRefresh} />
    </MoreSectionLayer>
  );

  if (section === 'top') return (
    <MoreSectionLayer title="Таблица лидеров" onBack={back}>
      <TopPage />
    </MoreSectionLayer>
  );

  if (section === 'referral') return (
    <MoreSectionLayer title="🤝 Реферальная программа" onBack={back}>
      <ReferralPage gs={gs} />
    </MoreSectionLayer>
  );

  if (section === 'donate') return (
    <MoreSectionLayer title="⭐️ Донат" onBack={back}>
      <DonatePage gs={gs} />
    </MoreSectionLayer>
  );

  if (section === 'giveaway') return (
    <MoreSectionLayer title="💸 Раздача денег" onBack={back}>
      <GiveawayPage gs={gs} onRefresh={onRefresh} botUsername={botUsername} />
    </MoreSectionLayer>
  );

  if (section === 'wiki') return (
    <MoreSectionLayer title="📖 База знаний" onBack={back}>
      <WikiPage />
    </MoreSectionLayer>
  );

  if (section === 'admin') return (
    <MoreSectionLayer title="⚙️ Админ-панель" onBack={back}>
      <AdminPage />
    </MoreSectionLayer>
  );

  return (
    <div className="page-content-safe">
      <PageHeader emoji="☰" title="Ещё" accent="var(--c-gold-rgb)" />

      <div className="px-[14px] pb-[14px] flex flex-col gap-[14px]">
      {MENU_GROUPS.map(group => (
        <div key={group.label}>
          <p className="m-0 mb-[8px] text-[11px] font-bold text-tg-hint tracking-[0.6px] uppercase">{group.label}</p>
          <div className="flex flex-col gap-[8px]">
            {group.items.map(item => (
              <div
                key={item.id}
                className="card flex items-center gap-[14px] cursor-pointer active:opacity-70 transition-opacity"
                onClick={() => openSection(item.id as SectionId)}
              >
                <span className="text-[30px] shrink-0 leading-none">{item.emoji}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="m-0 text-[15px] font-semibold">{item.title}</p>
                    {item.id === 'bonus' && bonusOffer && !bonusOffer.claimed && (
                      <span className="text-[10px] font-bold bg-[var(--c-green)] text-[var(--tg-theme-button-text-color)] px-[6px] py-[2px] rounded-full">Доступен</span>
                    )}
                    {item.id === 'clan' && gs.clan && (
                      <span className="text-[10px] font-bold bg-[rgba(var(--c-purple-rgb),0.2)] text-[var(--c-purple)] px-[6px] py-[2px] rounded-full">«{gs.clan.name}»</span>
                    )}
                  </div>
                  <p className="mt-[2px] mb-0 text-xs text-tg-hint truncate">{item.desc}</p>
                </div>
                <span className="text-[18px] text-tg-hint shrink-0">›</span>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Admin panel (только для владельца) */}
      {gs.tg_id === 474701274 && (
        <div
          className="card flex items-center gap-[14px] cursor-pointer"
          style={{ border: '1px solid rgba(var(--c-red-rgb),0.3)' }}
          onClick={() => openSection('admin')}
        >
          <span className="text-[30px]">⚙️</span>
          <div className="flex-1">
            <p className="m-0 text-[15px] font-semibold">Админ-панель</p>
            <p className="mt-[2px] mb-0 text-xs text-[var(--c-red-soft)]">Только для администратора</p>
          </div>
          <span className="text-[18px] text-tg-hint">›</span>
        </div>
      )}
      </div>
    </div>
  );
}

// ─── Inline sub-pages ─────────────────────────────────────────────────────────

function GiveawayPage({ gs, onRefresh, botUsername }: { gs: GameState; onRefresh: () => void; botUsername: string }) {
  const [amount, setAmount] = useState('');
  const [parts, setParts] = useState('5');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transfers, setTransfers] = useState<TransferOut[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const loadTransfers = () => {
    setLoadingList(true);
    apiGetMyTransfers()
      .then(r => setTransfers(r.transfers))
      .catch(() => {})
      .finally(() => setLoadingList(false));
  };

  useEffect(loadTransfers, []);

  const handleCreate = async () => {
    const total = parseFloat(amount);
    const max = parseInt(parts);
    if (!total || total <= 0 || !max || max <= 0) return;
    if (total > gs.rub) { setError('Недостаточно рублей'); return; }
    setCreating(true);
    setError(null);
    try {
      await apiCreateTransfer(total, max);
      setAmount('');
      setParts('5');
      onRefresh();
      loadTransfers();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка создания');
    } finally {
      setCreating(false);
    }
  };

  const copyLink = (key: string) => {
    const link = `https://t.me/${botUsername}?startapp=transfer_${key}`;
    void copyTmaText(link).then((copied) => {
      if (!copied) return;
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    });
  };

  const total = parseFloat(amount) || 0;
  const max = parseInt(parts) || 0;
  const perPart = total && max ? Math.floor(total / max) : 0;
  const allIn = Math.floor(gs.rub);

  const amountPresets = [1, 5, 10, 50].filter(v => v <= gs.rub);
  const partsPresets = [1, 2, 5, 10, 25, 50];

  const pillActive: React.CSSProperties = {
    background: 'var(--c-blue)',
    color: 'var(--tg-theme-button-text-color)',
    border: '1.5px solid var(--c-blue)',
  };
  const pillIdle: React.CSSProperties = {
    background: 'transparent',
    color: 'var(--tg-theme-hint-color)',
    border: '1.5px solid var(--surface-overlay-border)',
  };

  return (
    <div className="p-[14px] flex flex-col gap-4">

      {/* ── Форма ── */}
      <div className="card flex flex-col gap-0">
        <p className="m-0 mb-[14px] text-[11px] font-semibold text-tg-hint tracking-[0.8px] uppercase">Новая раздача</p>

        {/* Сумма */}
        <div className="mb-3">
          <div className="flex items-center justify-between mb-[6px]">
            <span className="text-[13px] font-medium text-tg-text">Сумма</span>
            <span className="text-[12px] text-tg-hint">
              баланс{' '}
              <span className="font-semibold" style={{ color: 'var(--tg-theme-text-color)' }}>
                ₽ {fmt(allIn)}
              </span>
            </span>
          </div>
          <div className="relative">
            <span
              className="absolute left-[14px] top-1/2 -translate-y-1/2 text-[14px] font-semibold pointer-events-none"
              style={{ color: 'var(--tg-theme-hint-color)' }}
            >
              ₽
            </span>
            <input
              type="number"
              value={amount}
              onChange={e => setAmount(e.target.value)}
              placeholder="0"
              className="text-input text-[15px] font-semibold"
              style={{
                paddingLeft: '32px',
                border: total > gs.rub ? '1.5px solid var(--c-red-soft)' : undefined,
              }}
            />
          </div>
          {(amountPresets.length > 0 || gs.rub > 0) && (
            <div className="flex gap-[6px] mt-[8px] flex-wrap">
              {amountPresets.map(v => (
                <button
                  key={v}
                  onClick={() => setAmount(String(v))}
                  className="px-[12px] py-[5px] rounded-full cursor-pointer text-[12px] font-semibold transition-all"
                  style={total === v ? pillActive : pillIdle}
                >
                  {v >= 1000 ? `${v / 1000}к` : v}
                </button>
              ))}
              {gs.rub > 0 && (
                <button
                  onClick={() => setAmount(String(allIn))}
                  className="px-[12px] py-[5px] rounded-full cursor-pointer text-[12px] font-semibold transition-all"
                  style={
                    total === allIn
                      ? { background: 'rgba(var(--c-gold-rgb),0.25)', color: 'var(--c-gold)', border: '1.5px solid rgba(var(--c-gold-rgb),0.5)' }
                      : { background: 'transparent', color: 'var(--c-gold)', border: '1.5px solid rgba(var(--c-gold-rgb),0.35)' }
                  }
                >
                  Всё
                </button>
              )}
            </div>
          )}
        </div>

        <div style={{ height: 1, background: 'var(--surface-overlay-border)', margin: '2px 0 14px' }} />

        {/* Получателей */}
        <div className="mb-3">
          <span className="block text-[13px] font-medium text-tg-text mb-[6px]">Получателей</span>
          <input
            type="number"
            value={parts}
            onChange={e => setParts(e.target.value)}
            placeholder="5"
            className="text-input text-[15px] font-semibold"
          />
          <div className="flex gap-[6px] mt-[8px] flex-wrap">
            {partsPresets.map(v => (
              <button
                key={v}
                onClick={() => setParts(String(v))}
                className="px-[12px] py-[5px] rounded-full cursor-pointer text-[12px] font-semibold transition-all"
                style={max === v ? pillActive : pillIdle}
              >
                {v}
              </button>
            ))}
          </div>
        </div>

        {/* Превью / ошибка */}
        {(perPart > 0 || error) && (
          <div style={{ height: 1, background: 'var(--surface-overlay-border)', margin: '2px 0 12px' }} />
        )}
        {perPart > 0 && (
          <div className="flex items-center justify-between mb-3">
            <span className="text-[13px] text-tg-hint">Каждый получит</span>
            <span className="text-[15px] font-bold" style={{ color: 'var(--tg-theme-text-color)' }}>
              ₽ {fmt(perPart)}
            </span>
          </div>
        )}
        {error && (
          <div
            className="mb-3 px-3 py-[9px] rounded-[10px] text-[13px]"
            style={{ background: 'rgba(var(--c-red-rgb),0.1)', color: 'var(--c-red-soft)' }}
          >
            ⚠️ {error}
          </div>
        )}

        <button
          onClick={() => void handleCreate()}
          disabled={creating || !total || !max || total > gs.rub}
          className="w-full py-[13px] rounded-[12px] border-none cursor-pointer font-bold text-[15px] disabled:opacity-40 transition-opacity"
          style={{ background: 'var(--c-blue)', color: 'var(--tg-theme-button-text-color)' }}
        >
          {creating ? 'Создаём...' : 'Создать ссылку'}
        </button>
      </div>

      {/* ── Список раздач ── */}
      {loadingList ? (
        <div className="flex justify-center py-3">
          <span className="text-[13px] text-tg-hint">Загрузка...</span>
        </div>
      ) : transfers.length > 0 ? (
        <div className="flex flex-col gap-[10px]">
          <p className="m-0 text-[11px] font-semibold text-tg-hint tracking-[0.8px] uppercase">Мои раздачи</p>
          {transfers.map(t => {
            const pct = t.max_claims > 0 ? (t.claims / t.max_claims) * 100 : 0;
            const isCopied = copiedKey === t.code;
            return (
              <div key={t.code} className="card" style={{ opacity: t.active ? 1 : 0.6 }}>
                {/* Заголовок */}
                <div className="flex items-center justify-between mb-[10px]">
                  <span className="text-[17px] font-bold">₽ {fmt(t.total_rub)}</span>
                  <span
                    className="text-[11px] font-semibold px-[8px] py-[3px] rounded-full"
                    style={{
                      background: t.active ? 'rgba(var(--c-green-rgb),0.12)' : 'var(--surface-subtle)',
                      color: t.active ? 'var(--c-green)' : 'var(--tg-theme-hint-color)',
                    }}
                  >
                    {t.active ? '● Активна' : '○ Завершена'}
                  </span>
                </div>

                {/* Прогресс-бар */}
                <div
                  className="mb-[8px]"
                  style={{ height: 3, borderRadius: 2, background: 'var(--surface-subtle-strong)', overflow: 'hidden' }}
                >
                  <div
                    style={{
                      width: `${pct}%`,
                      height: '100%',
                      borderRadius: 2,
                      background: t.active ? 'var(--c-green)' : 'var(--tg-theme-hint-color)',
                      transition: 'width 0.4s ease',
                    }}
                  />
                </div>

                {/* Статистика */}
                <div className="flex items-center justify-between mb-[10px]">
                  <span className="text-[12px] text-tg-hint">
                    {t.claims} из {t.max_claims} получили
                  </span>
                  <span className="text-[12px] text-tg-hint">по ₽ {fmt(t.rub_per_claim)}</span>
                </div>

                <p className="m-0 text-[11px] text-tg-hint mb-[10px]">{formatDateShort(t.created_at)}</p>

                {t.active && (
                  <button
                    onClick={() => copyLink(t.code)}
                    className="w-full py-[9px] rounded-[10px] cursor-pointer font-semibold text-[13px] transition-all"
                    style={{
                      background: 'transparent',
                      color: isCopied ? 'var(--c-green)' : 'var(--c-blue)',
                      border: isCopied
                        ? '1.5px solid rgba(var(--c-green-rgb),0.4)'
                        : '1.5px solid rgba(var(--c-blue-rgb),0.4)',
                    }}
                  >
                    {isCopied ? '✓ Скопировано' : 'Скопировать ссылку'}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function WikiPage() {
  return (
    <div className="p-[14px] flex flex-col gap-[10px]">
      {[
        { title: '💰 Как зарабатывать', body: 'Открывай паки и покупай животных у торговца → размещай их в местности с той же средой обитания, это даёт ×1.5 к доходу. Чем разнообразнее зоопарк, тем выше бонус.' },
        { title: '🌍 Местности', body: 'Первая местность бесплатна и случайна, каждая следующая дороже в 1.5 раза. Животное в своей среде обитания приносит в полтора раза больше. Местность также открывает экспедиции в эту зону.' },
        { title: '⚒️ Кузница', body: 'Предметы из кузницы дают бонусы: больше ходов в играх, скидки в банке, ускорение дохода и другие эффекты.' },
        { title: '🎮 Игры', body: 'Играй соло или против игроков. Ставки в рублях, выигрыш удваивает ставку. В коктейль-игре угадывай рецепт за 10 попыток.' },
        { title: '🏰 Кланы', body: 'Вступи в клан для получения клановых бонусов. Клан может иметь специализацию, которая даёт дополнительные преимущества.' },
      ].map(({ title, body }) => (
        <div key={title} className="card">
          <p className="m-0 mb-[6px] font-bold text-sm">{title}</p>
          <p className="m-0 text-[13px] text-tg-hint leading-relaxed">{body}</p>
        </div>
      ))}
    </div>
  );
}
