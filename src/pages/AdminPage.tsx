import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { createPortal } from 'react-dom';
import type { AdminCurrency } from '@/api/core';
import { apiAdminCreateAchievement, apiAdminEndMaintenance, apiAdminGrant, apiAdminOverview, apiAdminSetStatus, apiAdminStartMaintenance } from '@/api';
import type { AdminCustomAchievement, AdminOverview, AdminPlayer, MaintenanceStatus } from '@/types';
import { fmt, formatCountdown } from '@/utils/format';

type AdminTab = 'overview' | 'players' | 'achievements';

const CURRENCY_META: Record<AdminCurrency, { label: string; icon: string; color: string }> = {
  rub: { label: 'Рубли', icon: '₽', color: 'var(--c-green)' },
  usd: { label: 'Доллары', icon: '$', color: 'var(--c-gold)' },
  paw: { label: 'Лапки', icon: '🐾', color: 'var(--c-purple)' },
};

function StatCard({ label, value, hint, accent }: { label: string; value: string; hint: string; accent: string }) {
  return (
    <div className="rounded-2xl p-3" style={{ background: 'var(--surface-subtle)', border: '1px solid var(--surface-overlay-border)' }}>
      <div className="flex items-center gap-2 text-[11px] font-bold text-tg-hint">
        <span className="w-2 h-2 rounded-full" style={{ background: accent, boxShadow: `0 0 10px ${accent}` }} />
        {label}
      </div>
      <p className="m-0 mt-2 font-display text-[24px] leading-none">{value}</p>
      <p className="m-0 mt-2 text-[10px] text-tg-hint">{hint}</p>
    </div>
  );
}

function MaintenanceCard({ status, onChanged }: { status: MaintenanceStatus; onChanged: () => void }) {
  const [minutes, setMinutes] = useState('30');
  const [busy, setBusy] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (!status.active) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [status.active]);

  const remainingSeconds = status.ends_at
    ? Math.max(0, Math.floor((new Date(status.ends_at).getTime() - now) / 1000))
    : 0;

  const start = async () => {
    const duration = Number(minutes);
    if (!Number.isInteger(duration) || duration < 1 || duration > 1_440) return;
    if (!window.confirm(`Включить техперерыв на ${duration} мин.?`)) return;
    setBusy(true);
    setActionError(null);
    try {
      await apiAdminStartMaintenance(duration, 'Технический перерыв');
      onChanged();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Не удалось включить техперерыв');
    } finally {
      setBusy(false);
    }
  };

  const end = async () => {
    setBusy(true);
    setActionError(null);
    try {
      await apiAdminEndMaintenance();
      onChanged();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Не удалось завершить техперерыв');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`admin-maintenance-card${status.active ? ' admin-maintenance-card-active' : ''}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="m-0 text-[14px] font-extrabold">Технический перерыв</p>
          <p className="m-0 mt-1 text-[11px] text-tg-hint">Игроки увидят экран с обратным отсчётом</p>
        </div>
        <span className="admin-maintenance-status">{status.active ? 'идёт' : 'выключен'}</span>
      </div>

      {status.active ? (
        <div className="mt-3 flex items-center justify-between gap-3">
          <div>
            <p className="m-0 font-display text-[28px] leading-none tabular-nums">{formatCountdown(remainingSeconds)}</p>
            <p className="m-0 mt-1 text-[10px] text-tg-hint">до автоматического завершения</p>
          </div>
          <button type="button" onClick={() => void end()} disabled={busy} className="rounded-xl px-3 py-2 border-none text-[11px] font-extrabold" style={{ background: 'rgba(var(--c-green-rgb),0.14)', color: 'var(--c-green)' }}>
            {busy ? 'Завершаем…' : 'Завершить сейчас'}
          </button>
        </div>
      ) : (
        <div className="mt-3 flex items-center gap-2">
          <input
            type="number"
            min={1}
            max={1_440}
            value={minutes}
            onChange={event => setMinutes(event.target.value)}
            aria-label="Длительность техперерыва в минутах"
            className="w-[86px] rounded-xl px-3 py-2 border-none text-[12px] font-bold"
            style={{ background: 'var(--input-bg)', color: 'var(--tg-theme-text-color)' }}
          />
          <span className="text-[11px] text-tg-hint">минут</span>
          <button type="button" onClick={() => void start()} disabled={busy} className="ml-auto rounded-xl px-3 py-2 border-none text-[11px] font-extrabold" style={{ background: 'var(--c-orange)', color: 'var(--tg-theme-button-text-color)' }}>
            {busy ? 'Запускаем…' : 'Включить'}
          </button>
        </div>
      )}
      {actionError && <p className="m-0 mt-2 text-[11px]" style={{ color: 'var(--c-red-soft)' }}>{actionError}</p>}
    </div>
  );
}

function readAchievementImage(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!file.type.startsWith('image/')) {
      reject(new Error('Выбери файл изображения'));
      return;
    }
    const objectUrl = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      const maxSide = 900;
      const scale = Math.min(1, maxSide / Math.max(image.naturalWidth, image.naturalHeight));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
      const context = canvas.getContext('2d');
      if (!context) {
        URL.revokeObjectURL(objectUrl);
        reject(new Error('Не удалось обработать изображение'));
        return;
      }
      context.fillStyle = '#101411';
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(objectUrl);
      resolve(canvas.toDataURL('image/jpeg', 0.88));
    };
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error('Не удалось прочитать изображение'));
    };
    image.src = objectUrl;
  });
}

function AchievementCreator({ data, onChanged }: { data: AdminOverview; onChanged: () => void }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [audience, setAudience] = useState<'all' | 'selected'>('all');
  const [imageData, setImageData] = useState<string | null>(null);
  const [imageName, setImageName] = useState<string | null>(null);
  const [recipientSearch, setRecipientSearch] = useState('');
  const [recipientPlayers, setRecipientPlayers] = useState<AdminPlayer[]>(data.players_list);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null);

  useEffect(() => {
    if (!recipientSearch.trim()) {
      setRecipientPlayers(data.players_list);
      return;
    }
    const timer = window.setTimeout(() => {
      void apiAdminOverview(recipientSearch).then(result => setRecipientPlayers(result.players_list)).catch(() => setRecipientPlayers([]));
    }, 260);
    return () => window.clearTimeout(timer);
  }, [data.players_list, recipientSearch]);

  const chooseImage = async (file: File | undefined) => {
    if (!file) return;
    try {
      setMessage(null);
      setImageData(await readAchievementImage(file));
      setImageName(file.name);
    } catch (error) {
      setMessage({ text: error instanceof Error ? error.message : 'Не удалось загрузить фото', error: true });
    }
  };

  const toggleRecipient = (tgId: number) => {
    setSelectedIds(current => {
      const next = new Set(current);
      if (next.has(tgId)) next.delete(tgId);
      else next.add(tgId);
      return next;
    });
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!imageData) {
      setMessage({ text: 'Добавь изображение для медали', error: true });
      return;
    }
    if (audience === 'selected' && selectedIds.size === 0) {
      setMessage({ text: 'Выбери хотя бы одного получателя', error: true });
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await apiAdminCreateAchievement({
        title,
        description,
        audience,
        player_tg_ids: audience === 'selected' ? [...selectedIds] : [],
        image_data: imageData,
      });
      setTitle('');
      setDescription('');
      setAudience('all');
      setImageData(null);
      setImageName(null);
      setSelectedIds(new Set<number>());
      setMessage({ text: audience === 'all' ? 'Медаль открыта всем игрокам' : `Медаль выдана ${selectedIds.size} игрокам`, error: false });
      onChanged();
    } catch (error) {
      setMessage({ text: error instanceof Error ? error.message : 'Не удалось создать достижение', error: true });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <form onSubmit={event => void submit(event)} className="card" style={{ border: '1px solid rgba(var(--c-gold-rgb),0.34)', background: 'linear-gradient(145deg, rgba(var(--c-gold-rgb),0.10), var(--surface-subtle) 58%)' }}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="m-0 text-[15px] font-extrabold">Новое достижение</p>
            <p className="m-0 mt-1 text-[11px] text-tg-hint">Фото автоматически ужмётся и не исказится на медали.</p>
          </div>
          <span className="text-[24px] leading-none">✦</span>
        </div>

        <div className="mt-3 flex gap-3">
          <label className="grid h-[92px] w-[92px] shrink-0 cursor-pointer place-items-center overflow-hidden rounded-2xl text-center" style={{ background: 'var(--input-bg)', border: '1px dashed rgba(var(--c-gold-rgb),0.45)' }}>
            {imageData ? <img src={imageData} alt="Предпросмотр медали" className="h-full w-full object-contain p-1" /> : <span className="px-2 text-[11px] font-bold text-tg-hint">＋<br />Добавить фото</span>}
            <input type="file" accept="image/*" className="sr-only" onChange={event => void chooseImage(event.target.files?.[0])} />
          </label>
          <div className="min-w-0 flex-1 flex flex-col gap-2">
            <input required value={title} onChange={event => setTitle(event.target.value)} maxLength={80} placeholder="Название медали" className="w-full rounded-xl border-none px-3 py-2 text-[13px] font-bold" style={{ background: 'var(--input-bg)', color: 'var(--tg-theme-text-color)' }} />
            <textarea required value={description} onChange={event => setDescription(event.target.value)} maxLength={180} rows={2} placeholder="За что она выдаётся" className="w-full resize-none rounded-xl border-none px-3 py-2 text-[12px]" style={{ background: 'var(--input-bg)', color: 'var(--tg-theme-text-color)' }} />
            {imageName && <span className="truncate text-[10px] text-tg-hint">{imageName}</span>}
          </div>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-2">
          {([['all', 'Всем игрокам', 'Откроется сразу у всех'], ['selected', 'Выбранным', 'Только отмеченным аккаунтам']] as const).map(([id, label, hint]) => (
            <button key={id} type="button" onClick={() => setAudience(id)} className="rounded-xl px-3 py-2 text-left" style={{ border: `1px solid ${audience === id ? 'rgba(var(--c-gold-rgb),0.55)' : 'var(--surface-overlay-border)'}`, background: audience === id ? 'rgba(var(--c-gold-rgb),0.13)' : 'var(--surface-subtle)', color: 'var(--tg-theme-text-color)' }}>
              <span className="block text-[12px] font-extrabold">{label}</span>
              <span className="mt-1 block text-[10px] text-tg-hint">{hint}</span>
            </button>
          ))}
        </div>

        {audience === 'selected' && <div className="mt-3 rounded-xl p-2" style={{ background: 'rgba(var(--c-blue-rgb),0.08)', border: '1px solid rgba(var(--c-blue-rgb),0.2)' }}>
          <input value={recipientSearch} onChange={event => setRecipientSearch(event.target.value)} placeholder="Найти аккаунт по нику или Telegram ID" className="w-full rounded-lg border-none px-3 py-2 text-[12px]" style={{ background: 'var(--input-bg)', color: 'var(--tg-theme-text-color)' }} />
          <div className="mt-2 flex max-h-[190px] flex-col gap-1 overflow-y-auto">
            {recipientPlayers.map(player => <label key={player.tg_id} className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-2" style={{ background: selectedIds.has(player.tg_id) ? 'rgba(var(--c-blue-rgb),0.16)' : 'transparent' }}>
              <input type="checkbox" checked={selectedIds.has(player.tg_id)} onChange={() => toggleRecipient(player.tg_id)} />
              <span className="min-w-0 flex-1 truncate text-[12px] font-bold">{player.nickname}</span>
              <span className="shrink-0 text-[10px] text-tg-hint">{player.username ? `@${player.username}` : player.tg_id}</span>
            </label>)}
            {recipientPlayers.length === 0 && <p className="m-0 p-2 text-[11px] text-tg-hint">Аккаунт не найден</p>}
          </div>
          <p className="m-0 mt-1 text-[10px] text-tg-hint">Выбрано: {selectedIds.size}</p>
        </div>}

        <div className="mt-3 flex items-center gap-2">
          <button type="submit" disabled={busy} className="rounded-xl border-none px-4 py-2 text-[12px] font-extrabold" style={{ background: 'var(--c-gold)', color: '#241c08' }}>{busy ? 'Создаём…' : 'Создать и открыть'}</button>
          {message && <span className="text-[11px]" style={{ color: message.error ? 'var(--c-red-soft)' : 'var(--c-green)' }}>{message.text}</span>}
        </div>
      </form>

      <div className="card">
        <div className="flex items-center justify-between gap-3"><div><p className="m-0 text-[14px] font-extrabold">Созданные медали</p><p className="m-0 mt-1 text-[11px] text-tg-hint">Они добавляются в коллекцию игроков автоматически.</p></div><span className="text-[12px] font-extrabold text-tg-hint">{data.custom_achievements.length}</span></div>
        {data.custom_achievements.length === 0 ? <p className="m-0 mt-3 text-[12px] text-tg-hint">Пока нет кастомных достижений.</p> : <div className="mt-3 flex flex-col gap-2">{data.custom_achievements.map(achievement => <CustomAchievementRow key={achievement.id} achievement={achievement} />)}</div>}
      </div>
    </div>
  );
}

function CustomAchievementRow({ achievement }: { achievement: AdminCustomAchievement }) {
  return <div className="flex items-center gap-3 rounded-xl p-2" style={{ background: 'var(--surface-subtle)' }}>
    <img src={achievement.image_url} alt="" className="h-12 w-12 shrink-0 rounded-xl object-contain" style={{ background: 'var(--input-bg)' }} />
    <div className="min-w-0 flex-1"><p className="m-0 truncate text-[13px] font-extrabold">{achievement.title}</p><p className="m-0 mt-1 truncate text-[11px] text-tg-hint">{achievement.description}</p></div>
    <span className="shrink-0 text-right text-[10px] font-bold text-tg-hint">{achievement.audience === 'all' ? 'всем' : `${achievement.recipient_count} чел.`}</span>
  </div>;
}

function PlayerRow({ player, selected, onSelect, asOf }: { player: AdminPlayer; selected: boolean; onSelect: () => void; asOf?: string }) {
  const online = Boolean(player.last_seen_at && asOf && new Date(asOf).getTime() - new Date(player.last_seen_at).getTime() < 15 * 60 * 1000);
  return (
    <button
      type="button"
      onClick={onSelect}
      className="w-full text-left rounded-2xl p-3 border-none"
      style={{
        background: selected ? 'rgba(var(--c-blue-rgb),0.13)' : 'var(--surface-subtle)',
        boxShadow: selected ? 'inset 0 0 0 1px rgba(var(--c-blue-rgb),0.48)' : 'inset 0 0 0 1px var(--surface-overlay-border)',
      }}
    >
      <div className="flex items-center gap-3">
        <div className="relative w-10 h-10 rounded-[14px] grid place-items-center shrink-0 text-[18px]" style={{ background: 'rgba(var(--c-gold-rgb),0.13)' }}>
          {player.nickname.slice(0, 1).toUpperCase()}
          {online && <span className="absolute right-[-1px] bottom-[-1px] w-3 h-3 rounded-full" style={{ background: 'var(--c-green)', border: '2px solid var(--tg-theme-secondary-bg-color)' }} />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="m-0 truncate text-[14px] font-extrabold">{player.nickname}</p>
            {player.status === 'banned' && <span className="shrink-0 rounded-full px-2 py-[2px] text-[9px] font-extrabold" style={{ color: 'var(--c-red-soft)', background: 'rgba(var(--c-red-rgb),0.13)' }}>бан</span>}
          </div>
          <p className="m-0 mt-1 truncate text-[11px] text-tg-hint">{player.username ? `@${player.username}` : `id ${player.tg_id}`} · {player.animals_count} жив.</p>
        </div>
        <div className="text-right shrink-0">
          <p className="m-0 text-[12px] font-extrabold" style={{ color: player.net_income_rub_per_min >= 0 ? 'var(--c-green)' : 'var(--c-orange)' }}>₽ {fmt(player.net_income_rub_per_min)}/мин</p>
          <p className="m-0 mt-1 text-[10px] text-tg-hint">{fmt(player.rub)} ₽</p>
        </div>
      </div>
    </button>
  );
}

function PlayerActions({ player, onChanged, onClose }: { player: AdminPlayer; onChanged: () => void; onClose: () => void }) {
  const [currency, setCurrency] = useState<AdminCurrency>('rub');
  const [amount, setAmount] = useState('1000');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const grant = async () => {
    const parsed = Number(amount);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      setMessage('Укажи целое положительное число');
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const result = await apiAdminGrant(player.tg_id, currency, parsed);
      setMessage(`Начислено. Новый баланс: ${fmt(result.new_balance)} ${CURRENCY_META[currency].icon}`);
      onChanged();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Не удалось выполнить операцию');
    } finally {
      setBusy(false);
    }
  };

  const toggleBan = async () => {
    const next = player.status === 'banned' ? 'active' : 'banned';
    if (!window.confirm(next === 'banned' ? `Заблокировать «${player.nickname}»?` : `Вернуть доступ «${player.nickname}»?`)) return;
    setBusy(true);
    setMessage(null);
    try {
      await apiAdminSetStatus(player.tg_id, next);
      setMessage(next === 'banned' ? 'Игрок заблокирован' : 'Доступ восстановлен');
      onChanged();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Не удалось изменить статус');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-2xl p-3" style={{ background: 'linear-gradient(145deg, rgba(var(--c-blue-rgb),0.14), var(--surface-subtle) 58%)', border: '1px solid rgba(var(--c-blue-rgb),0.28)' }}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="m-0 text-[13px] font-extrabold">Управление игроком</p>
          <p className="m-0 mt-1 text-[11px] text-tg-hint">{player.nickname} · {player.tg_id}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button type="button" onClick={() => void toggleBan()} disabled={busy} className="rounded-xl px-3 py-2 border-none text-[11px] font-extrabold" style={{ color: player.status === 'banned' ? 'var(--c-green)' : 'var(--c-red-soft)', background: player.status === 'banned' ? 'rgba(var(--c-green-rgb),0.12)' : 'rgba(var(--c-red-rgb),0.12)' }}>
            {player.status === 'banned' ? 'Разблокировать' : 'Заблокировать'}
          </button>
          <button type="button" onClick={onClose} className="grid place-items-center w-8 h-8 rounded-xl border-none text-[20px] leading-none" style={{ color: 'var(--tg-theme-hint-color)', background: 'var(--surface-subtle)' }} aria-label="Закрыть управление игроком">
            ×
          </button>
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <select value={currency} onChange={e => setCurrency(e.target.value as AdminCurrency)} className="min-w-0 flex-1 rounded-xl px-3 py-2 border-none text-[12px] font-bold" style={{ background: 'var(--input-bg)', color: 'var(--tg-theme-text-color)' }}>
          {(Object.keys(CURRENCY_META) as AdminCurrency[]).map(id => <option key={id} value={id}>{CURRENCY_META[id].icon} {CURRENCY_META[id].label}</option>)}
        </select>
        <input value={amount} onChange={e => setAmount(e.target.value.replace(/[^0-9]/g, ''))} inputMode="numeric" aria-label="Количество валюты" className="w-[92px] rounded-xl px-3 py-2 border-none text-[12px] font-bold" style={{ background: 'var(--input-bg)', color: 'var(--tg-theme-text-color)' }} />
        <button type="button" onClick={() => void grant()} disabled={busy} className="rounded-xl px-3 py-2 border-none text-[12px] font-extrabold" style={{ background: 'var(--c-blue)', color: 'var(--tg-theme-button-text-color)' }}>Выдать</button>
      </div>
      {message && <p className="m-0 mt-2 text-[11px]" style={{ color: message.includes('Не') || message.includes('число') ? 'var(--c-red-soft)' : 'var(--c-green)' }}>{message}</p>}
    </div>
  );
}

export function AdminPage() {
  const [tab, setTab] = useState<AdminTab>('overview');
  const [search, setSearch] = useState('');
  const [data, setData] = useState<AdminOverview | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setError(null);
      const next = await apiAdminOverview(search);
      setData(next);
      setSelectedId(current => next.players_list.some(player => player.tg_id === current) ? current : null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось загрузить панель');
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), search ? 280 : 0);
    return () => window.clearTimeout(timer);
  }, [load, search]);

  const selectedPlayer = useMemo(() => data?.players_list.find(player => player.tg_id === selectedId) ?? null, [data, selectedId]);

  return (
    <div className="px-[14px] pt-4 pb-6 flex flex-col gap-3">
      <div className="relative overflow-hidden rounded-[24px] p-4" style={{ background: 'radial-gradient(circle at 100% 0%, rgba(var(--c-red-rgb),0.32), transparent 48%), linear-gradient(145deg, #2b2020, #1c1c1b 70%)', border: '1px solid rgba(var(--c-red-rgb),0.34)' }}>
        <div className="absolute -right-4 -top-6 text-[108px] leading-none opacity-[0.08]">⌘</div>
        <div className="relative">
          <div className="flex items-center gap-2"><span className="rounded-full px-2 py-1 text-[9px] font-extrabold uppercase tracking-[1px]" style={{ color: 'var(--c-red-soft)', background: 'rgba(var(--c-red-rgb),0.15)' }}>owner access</span><span className="text-[10px] text-tg-hint">операционный центр</span></div>
          <h1 className="m-0 mt-3 font-display text-[26px] leading-none">Админ-панель</h1>
          <p className="m-0 mt-2 max-w-[260px] text-[12px] leading-[1.45] text-tg-hint">Состояние зоопарка, экономика и быстрые действия в одном месте.</p>
          <div className="mt-4 flex items-center gap-2"><span className="w-2 h-2 rounded-full" style={{ background: 'var(--c-green)', boxShadow: '0 0 10px var(--c-green)' }} /><span className="text-[11px] font-bold">{data ? `Обновлено ${new Date(data.generated_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}` : 'Подключаемся к серверу'}</span></div>
        </div>
      </div>

      <div className="flex rounded-2xl p-1" style={{ background: 'var(--surface-subtle)', border: '1px solid var(--surface-overlay-border)' }}>
        {([['overview', 'Сводка'], ['players', 'Игроки'], ['achievements', 'Медали']] as const).map(([id, label]) => <button key={id} type="button" onClick={() => setTab(id)} className="flex-1 rounded-xl py-2 border-none text-[12px] font-extrabold" style={{ background: tab === id ? 'rgba(var(--c-gold-rgb),0.15)' : 'transparent', color: tab === id ? 'var(--tg-theme-text-color)' : 'var(--tg-theme-hint-color)' }}>{label}</button>)}
      </div>

      {loading && !data && <div className="card text-center text-[13px] text-tg-hint">Загружаем данные панели…</div>}
      {error && <div className="rounded-2xl p-3 text-[12px]" style={{ background: 'rgba(var(--c-red-rgb),0.11)', border: '1px solid rgba(var(--c-red-rgb),0.25)', color: 'var(--c-red-soft)' }}>⚠️ {error}<button type="button" onClick={() => void load()} className="ml-2 border-none bg-transparent underline font-bold" style={{ color: 'inherit' }}>Повторить</button></div>}
      {data && <MaintenanceCard status={data.maintenance} onChanged={() => void load()} />}

      {data && tab === 'overview' && <>
        <div className="grid grid-cols-2 gap-2">
          <StatCard label="Игроки" value={fmt(data.stats.players)} hint={`${fmt(data.stats.active_players)} активных`} accent="var(--c-blue)" />
          <StatCard label="Онлайн" value={fmt(data.stats.online_players)} hint="за последние 15 минут" accent="var(--c-green)" />
          <StatCard label="Животные" value={fmt(data.stats.animals)} hint="в активных зоопарках" accent="var(--c-gold)" />
          <StatCard label="Операции" value={fmt(data.stats.ledger_entries_today)} hint="записей ledger сегодня" accent="var(--c-purple)" />
        </div>
        <div className="card">
          <div className="flex items-center justify-between gap-3"><div><p className="m-0 text-[14px] font-extrabold">Экономика</p><p className="m-0 mt-1 text-[11px] text-tg-hint">Балансы игроков · казна</p></div>{data.bank_rate && <span className="rounded-full px-2 py-1 text-[10px] font-extrabold" style={{ color: 'var(--c-gold)', background: 'rgba(var(--c-gold-rgb),0.12)' }}>1$ = {fmt(data.bank_rate)} ₽</span>}</div>
          <div className="mt-3 grid grid-cols-3 gap-2">{(Object.keys(CURRENCY_META) as AdminCurrency[]).map(id => <div key={id} className="rounded-xl p-2" style={{ background: 'var(--surface-subtle)' }}><p className="m-0 text-[11px] text-tg-hint">{CURRENCY_META[id].icon} {CURRENCY_META[id].label}</p><p className="m-0 mt-1 text-[13px] font-extrabold" style={{ color: CURRENCY_META[id].color }}>{fmt(data.balances[id])}</p><p className="m-0 mt-1 text-[10px] text-tg-hint">казна {fmt(data.treasury[id])}</p></div>)}</div>
        </div>
        <div className="card"><div className="flex items-center justify-between"><p className="m-0 text-[14px] font-extrabold">Последние игроки</p><button type="button" onClick={() => setTab('players')} className="border-none bg-transparent text-[11px] font-bold" style={{ color: 'var(--c-blue)' }}>Все игроки →</button></div><div className="mt-3 flex flex-col gap-2">{data.players_list.slice(0, 3).map(player => <PlayerRow key={player.tg_id} player={player} selected={false} asOf={data.generated_at} onSelect={() => { setSelectedId(player.tg_id); setTab('players'); }} />)}</div></div>
      </>}

      {data && tab === 'players' && <>
        <div className="relative"><span className="absolute left-3 top-1/2 -translate-y-1/2 text-tg-hint">⌕</span><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Никнейм, username или Telegram ID" className="w-full rounded-2xl border-none py-3 pl-9 pr-3 text-[12px]" style={{ background: 'var(--input-bg)', color: 'var(--tg-theme-text-color)', boxShadow: 'inset 0 0 0 1px var(--input-border)' }} /></div>
        <p className="m-0 px-1 text-[11px] text-tg-hint">Показаны последние 50 · найдено: {data.players_list.length}</p>
        {data.players_list.length === 0 ? <div className="card text-center text-[13px] text-tg-hint">Игроки не найдены</div> : <div className="flex flex-col gap-2">{data.players_list.map(player => <PlayerRow key={player.tg_id} player={player} selected={player.tg_id === selectedId} asOf={data.generated_at} onSelect={() => setSelectedId(player.tg_id === selectedId ? null : player.tg_id)} />)}</div>}
      </>}

      {data && tab === 'achievements' && <AchievementCreator data={data} onChanged={() => void load()} />}

      {selectedPlayer && createPortal(
        <div
          className="admin-player-backdrop fixed inset-0 z-[240] flex items-end justify-center"
          role="dialog"
          aria-modal="true"
          aria-label={`Управление игроком ${selectedPlayer.nickname}`}
          onClick={event => { if (event.target === event.currentTarget) setSelectedId(null); }}
        >
          <div className="admin-player-drawer w-full max-w-[480px] overflow-y-auto">
            <PlayerActions player={selectedPlayer} onChanged={() => void load()} onClose={() => setSelectedId(null)} />
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}
