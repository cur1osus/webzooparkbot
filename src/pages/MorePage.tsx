import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import type { GameState, TransferOut } from '../types';
import { BankPage } from './BankPage';
import { BonusPage } from './more/BonusPage';
import { MerchantPage } from './more/MerchantPage';
import { ClanPage } from './more/ClanPage';
import { TopPage } from './more/TopPage';
import { ReferralPage } from './more/ReferralPage';
import { DonatePage } from './more/DonatePage';
import { apiCreateTransfer, apiGetMyTransfers } from '../api';
import { fmt, formatDateShort } from '../utils/format';
import { inTma } from '../tma';

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
      { id: 'clan',     emoji: '🏰',  title: 'Клан',               desc: 'Создай клан и получи бонусы' },
      { id: 'top',      emoji: '🏆',  title: 'Таблица лидеров',    desc: 'Топ-20 по доходу' },
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
        <div className="px-[14px] pt-[14px] pb-[10px] flex items-center gap-3 border-b border-white/[0.07] bg-tg-bg/95 backdrop-blur-xl shrink-0">
          <button
            onClick={onBack}
            className="flex items-center gap-1 px-3 py-[6px] rounded-lg border border-white/[0.12] bg-transparent text-white cursor-pointer text-[13px] shrink-0"
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

  const back = () => setSection(null);
  const openSection = (nextSection: SectionId) => setSection(nextSection);

  if (section === 'bank') return (
    <MoreSectionLayer title="🏦 Банк" onBack={back}>
      <BankPage gs={gs} onRefresh={onRefresh} />
    </MoreSectionLayer>
  );

  if (section === 'bonus') return (
    <MoreSectionLayer title="🎁 Ежедневный бонус" onBack={back}>
      <BonusPage gs={gs} onClaim={onRefresh} />
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
    <MoreSectionLayer title="🏆 Таблица лидеров" onBack={back}>
      <TopPage gs={gs} />
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
      <GiveawayPage gs={gs} onRefresh={onRefresh} />
    </MoreSectionLayer>
  );

  if (section === 'wiki') return (
    <MoreSectionLayer title="📖 База знаний" onBack={back}>
      <WikiPage />
    </MoreSectionLayer>
  );

  return (
    <div className="page-content-safe p-[14px] flex flex-col gap-[14px]">
      <p className="m-0 text-[20px] font-extrabold">☰ Ещё</p>

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
                    {item.id === 'bonus' && gs.bonus === 1 && (
                      <span className="text-[10px] font-bold bg-[var(--c-green)] text-white px-[6px] py-[2px] rounded-full">Доступен</span>
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
          onClick={() => {}}
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
  );
}

// ─── Inline sub-pages ─────────────────────────────────────────────────────────

function GiveawayPage({ gs, onRefresh: _onRefresh }: { gs: GameState; onRefresh: () => void }) {
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
      loadTransfers();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка создания');
    } finally {
      setCreating(false);
    }
  };

  const copyLink = (key: string) => {
    const link = `https://t.me/ZooParkBot?start=transfer_${key}`;
    navigator.clipboard.writeText(link).then(() => {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    }).catch(() => {});
  };

  const total = parseFloat(amount) || 0;
  const max = parseInt(parts) || 0;
  const perPart = total && max ? Math.floor(total / max) : 0;

  return (
    <div className="p-[14px] flex flex-col gap-3">
      <div className="card flex flex-col gap-0">
        <p className="m-0 mb-[10px] font-bold">Создать раздачу</p>
        <input
          type="number"
          value={amount}
          onChange={e => setAmount(e.target.value)}
          placeholder="Сумма ₽"
          className="w-full px-3 py-[10px] rounded-[10px] mb-2 border border-white/[0.12] bg-black/20 text-white text-sm"
        />
        <input
          type="number"
          value={parts}
          onChange={e => setParts(e.target.value)}
          placeholder="Количество получателей"
          className="w-full px-3 py-[10px] rounded-[10px] mb-[10px] border border-white/[0.12] bg-black/20 text-white text-sm"
        />
        {perPart > 0 && (
          <p className="m-0 mb-[10px] text-[13px] text-tg-hint">
            Каждый получит: <strong className="text-white">₽ {fmt(perPart)}</strong>
          </p>
        )}
        {error && <p className="m-0 mb-2 text-[var(--c-red-soft)] text-[13px]">⚠️ {error}</p>}
        <button
          onClick={() => void handleCreate()}
          disabled={creating || !total || !max || total > gs.rub}
          className="w-full py-3 rounded-[10px] border-none cursor-pointer font-bold text-sm disabled:opacity-50"
          style={{ background: 'var(--c-green)', color: 'white' }}
        >
          {creating ? 'Создаём...' : 'Создать ссылку'}
        </button>
      </div>

      {loadingList ? (
        <p className="text-center text-tg-hint text-[13px]">Загрузка раздач...</p>
      ) : transfers.length > 0 ? (
        <div>
          <p className="m-0 mb-2 text-[11px] font-bold text-tg-hint tracking-[0.6px] uppercase">Мои раздачи</p>
          <div className="flex flex-col gap-2">
            {transfers.map(t => (
              <div
                key={t.key}
                className="card"
                style={{ opacity: t.active ? 1 : 0.55 }}
              >
                <div className="flex justify-between items-start mb-[6px]">
                  <div>
                    <p className="m-0 font-bold text-[14px]">₽ {fmt(t.total_rub)}</p>
                    <p className="mt-[2px] mb-0 text-xs text-tg-hint">
                      {t.claims}/{t.max_claims} получили · по ₽{fmt(t.rub_per_claim)}
                    </p>
                  </div>
                  <span
                    className="text-[11px] font-bold px-2 py-[3px] rounded-full"
                    style={{
                      background: t.active ? 'rgba(var(--c-green-rgb),0.15)' : 'rgba(255,255,255,0.08)',
                      color: t.active ? 'var(--c-green)' : 'var(--tg-theme-hint-color)',
                    }}
                  >
                    {t.active ? 'Активна' : 'Завершена'}
                  </span>
                </div>
                <p className="m-0 mb-[8px] text-[11px] text-tg-hint">{formatDateShort(t.created_at)}</p>
                {t.active && (
                  <button
                    onClick={() => copyLink(t.key)}
                    className="w-full py-2 rounded-[8px] border-none cursor-pointer font-semibold text-[13px]"
                    style={{
                      background: copiedKey === t.key ? 'rgba(var(--c-green-rgb),0.15)' : 'rgba(255,255,255,0.08)',
                      color: copiedKey === t.key ? 'var(--c-green)' : 'var(--tg-theme-text-color)',
                    }}
                  >
                    {copiedKey === t.key ? '✅ Скопировано' : '📋 Скопировать ссылку'}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function WikiPage() {
  return (
    <div className="p-[14px] flex flex-col gap-[10px]">
      {[
        { title: '💰 Как зарабатывать', body: 'Покупай животных в Зоомаркете → размещай в вольерах → получай доход каждую минуту. Чем больше видов — тем выше бонус к доходу.' },
        { title: '🏗️ Вольеры', body: 'Вольеры — вместилища для животных. Без вольеров нет мест для животных. Покупай вольеры разного размера — от малого до большого.' },
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
