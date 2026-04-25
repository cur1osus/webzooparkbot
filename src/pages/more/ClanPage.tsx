import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { ClanListResponse, ClanOut, GameState } from '@/types';
import { apiGetClanList, apiCreateClan, apiJoinClan, apiLeaveClan } from '@/api';
import { CLAN_SPECIALTIES, getClanSpecialtyLabel } from '@/utils/clan';

const CLAN_NAME_MIN_LENGTH = 1;
const CLAN_NAME_MAX_LENGTH = 20;

function formatMembers(count: number): string {
  const abs = Math.abs(count);
  const mod10 = abs % 10;
  const mod100 = abs % 100;
  const noun = mod10 === 1 && mod100 !== 11
    ? 'участник'
    : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)
      ? 'участника'
      : 'участников';

  return `${count} ${noun}`;
}

export function ClanPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [creating, setCreating] = useState(false);
  const [joiningClanId, setJoiningClanId] = useState<number | null>(null);
  const [leaving, setLeaving] = useState(false);
  const [newName, setNewName] = useState('');
  const [newSpec, setNewSpec] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [confirmLeave, setConfirmLeave] = useState(false);
  const { data, error, isLoading, refetch } = useQuery<ClanListResponse>({
    queryKey: ['clans'],
    queryFn: apiGetClanList,
    staleTime: 30_000,
  });
  const queryError = error instanceof Error ? error.message : null;
  const openClans = data?.clans ?? [];
  const trimmedName = newName.trim();
  const canAffordCreate = gs.usd >= 1;
  const canCreate = trimmedName.length >= CLAN_NAME_MIN_LENGTH && trimmedName.length <= CLAN_NAME_MAX_LENGTH && canAffordCreate;
  const mySpecialty = gs.clan?.specialty ? CLAN_SPECIALTIES.find((s) => s.id === gs.clan?.specialty) : null;
  const isOwner = gs.clan?.role === 'owner';

  const clearMsgs = () => { setSuccessMsg(null); setErrorMsg(null); };

  const handleCreate = async () => {
    if (!canCreate) return;
    setCreating(true);
    clearMsgs();
    try {
      const res = await apiCreateClan(trimmedName, newSpec ?? undefined);
      if (res.ok) {
        setSuccessMsg(res.message);
        setShowCreate(false);
        setNewName('');
        setNewSpec(null);
        onRefresh();
        void refetch();
      } else {
        setErrorMsg(res.message ?? 'Ошибка');
      }
    } catch (e) {
      setErrorMsg((e as Error).message ?? 'Ошибка');
    } finally {
      setCreating(false);
    }
  };

  const handleJoin = async (clanId: number) => {
    if (joiningClanId !== null) return;
    setJoiningClanId(clanId);
    clearMsgs();
    try {
      const res = await apiJoinClan(clanId);
      if (res.ok) {
        setSuccessMsg(res.message);
        onRefresh();
        void refetch();
      } else {
        setErrorMsg(res.message ?? 'Ошибка');
      }
    } catch (e) {
      setErrorMsg((e as Error).message ?? 'Ошибка');
    } finally {
      setJoiningClanId(null);
    }
  };

  const handleLeave = async () => {
    if (!confirmLeave) {
      setConfirmLeave(true);
      return;
    }
    setLeaving(true);
    clearMsgs();
    try {
      const res = await apiLeaveClan();
      if (res.ok) {
        setSuccessMsg(res.message);
        setConfirmLeave(false);
        onRefresh();
        void refetch();
      } else {
        setErrorMsg(res.message ?? 'Ошибка');
      }
    } catch (e) {
      setErrorMsg((e as Error).message ?? 'Ошибка');
    } finally {
      setLeaving(false);
    }
  };

  return (
    <div className="p-[14px] flex flex-col gap-4 page-enter">
      {isLoading && !data && (
        <div className="card flex items-center gap-3">
          <div className="spinner shrink-0" />
          <div>
            <p className="m-0 font-bold">Загружаем кланы</p>
            <p className="m-0 text-[12px] text-tg-hint">Подбираем активные сообщества</p>
          </div>
        </div>
      )}

      {successMsg && (
        <div className="card bg-[rgba(var(--c-green-rgb),0.1)] border border-[rgba(var(--c-green-rgb),0.3)]">
          <p className="m-0 font-bold text-[var(--c-green)]">✅ {successMsg}</p>
        </div>
      )}
      {errorMsg && (
        <div className="card bg-[rgba(var(--c-red-rgb),0.1)] border border-[rgba(var(--c-red-rgb),0.3)]">
          <p className="m-0 text-[var(--c-red-soft)]">⚠️ {errorMsg}</p>
        </div>
      )}
      {queryError && !errorMsg && (
        <div className="card bg-[rgba(var(--c-red-rgb),0.1)] border border-[rgba(var(--c-red-rgb),0.3)]">
          <p className="m-0 text-[var(--c-red-soft)]">⚠️ {queryError}</p>
        </div>
      )}

      {gs.clan && (
        <div
          className="card overflow-hidden relative border border-[rgba(var(--c-purple-rgb),0.35)]"
          style={{
            background: 'linear-gradient(145deg, rgba(var(--c-purple-rgb),0.2), rgba(var(--c-blue-rgb),0.08) 52%, var(--card-bg))',
            boxShadow: '0 16px 36px rgba(0,0,0,0.18)',
          }}
        >
          <div className="absolute top-[-34px] right-[-22px] text-[104px] opacity-[0.08] leading-none pointer-events-none">🏰</div>
          <div className="relative">
            <div className="flex items-start gap-3 mb-4">
              <div className="w-[54px] h-[54px] rounded-[18px] grid place-items-center text-[28px] glow-purple shrink-0" style={{ background: 'rgba(var(--c-purple-rgb),0.18)' }}>
                🏰
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-[4px]">
                  <span className="text-[10px] font-extrabold uppercase tracking-[0.6px] px-2 py-[3px] rounded-full bg-[rgba(var(--c-purple-rgb),0.18)] text-[var(--c-purple)]">
                    Твой клан
                  </span>
                  <span className="text-[10px] font-extrabold px-2 py-[3px] rounded-full bg-[rgba(var(--c-gold-rgb),0.14)] text-[var(--c-gold)]">
                    Ур. {gs.clan.level}
                  </span>
                </div>
                <p className="m-0 text-[20px] leading-tight font-extrabold truncate">«{gs.clan.name}»</p>
                <p className="mt-[3px] mb-0 text-[12px] text-tg-hint">
                  {mySpecialty?.label ?? getClanSpecialtyLabel(gs.clan.specialty) ?? 'Без специализации'}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 mb-3">
              <div className="surface-subtle rounded-[14px] px-3 py-[10px]">
                <p className="m-0 text-[11px] text-tg-hint">Участники</p>
                <p className="m-0 mt-[2px] font-extrabold">{formatMembers(gs.clan.member_count)}</p>
              </div>
              <div className="surface-subtle rounded-[14px] px-3 py-[10px]">
                <p className="m-0 text-[11px] text-tg-hint">Твоя роль</p>
                <p className="m-0 mt-[2px] font-extrabold">{isOwner ? '👑 Владелец' : '👤 Участник'}</p>
              </div>
            </div>

            {mySpecialty?.desc && (
              <div className="surface-subtle rounded-[14px] px-3 py-[10px] mb-3">
                <p className="m-0 text-[11px] text-tg-hint">Бонус специализации</p>
                <p className="m-0 mt-[2px] text-[13px] font-bold">{mySpecialty.desc}</p>
              </div>
            )}

            {confirmLeave && (
              <div className="rounded-[14px] px-3 py-[10px] mb-3 border bg-[rgba(var(--c-red-rgb),0.08)]" style={{ borderColor: 'rgba(var(--c-red-rgb),0.24)' }}>
                <p className="m-0 text-[13px] text-[var(--c-red-soft)]">
                  {isOwner ? 'Выход владельца удалит клан и исключит участников.' : 'Ты потеряешь доступ к бонусам клана.'}
                </p>
              </div>
            )}

            <div className="flex gap-2">
              {confirmLeave && (
                <button
                  onClick={() => setConfirmLeave(false)}
                  disabled={leaving}
                  className="flex-1 py-[11px] rounded-xl border font-bold text-sm bg-transparent text-tg-text"
                  style={{ borderColor: 'var(--surface-overlay-border)' }}
                >
                  Остаться
                </button>
              )}
              <button
                onClick={() => void handleLeave()}
                disabled={leaving}
                className="flex-1 py-[11px] rounded-xl border-none cursor-pointer bg-[rgba(var(--c-red-rgb),0.14)] text-[var(--c-red-soft)] font-extrabold text-sm"
              >
                {leaving ? 'Выходим...' : confirmLeave ? 'Да, выйти' : 'Покинуть клан'}
              </button>
            </div>
          </div>
        </div>
      )}

      {!gs.clan && (
        <>
          <div
            className="card overflow-hidden relative border border-[rgba(var(--c-blue-rgb),0.28)]"
            style={{ background: 'linear-gradient(150deg, rgba(var(--c-blue-rgb),0.16), rgba(var(--c-purple-rgb),0.14) 48%, var(--card-bg))' }}
          >
            <div className="absolute top-[-42px] right-[-28px] text-[118px] opacity-[0.08] leading-none pointer-events-none">🏰</div>
            <div className="relative">
              <span className="inline-flex mb-3 text-[10px] font-extrabold uppercase tracking-[0.7px] px-2 py-[4px] rounded-full bg-[rgba(var(--c-blue-rgb),0.18)] text-[var(--c-blue)]">
                Сообщество
              </span>
              <p className="m-0 text-[22px] leading-[1.12] font-extrabold">Найди клан или создай свой</p>
              <p className="mt-2 mb-4 text-[13px] leading-[1.35] text-tg-hint">
                Кланы помогают быстрее развиваться: вступай к активным игрокам или собери свою команду за $1.
              </p>
              <div className="grid grid-cols-3 gap-2">
                {[
                  ['⚡', 'Бонусы'],
                  ['👥', 'Команда'],
                  ['🏆', 'Рейтинг'],
                ].map(([icon, label]) => (
                  <div key={label} className="surface-subtle rounded-[14px] px-2 py-[9px] text-center">
                    <p className="m-0 text-[18px] leading-none">{icon}</p>
                    <p className="mt-[5px] mb-0 text-[11px] font-bold text-tg-hint">{label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <button
            onClick={() => { setShowCreate(s => !s); clearMsgs(); }}
            className="py-[13px] rounded-xl border-none cursor-pointer text-[var(--tg-theme-button-text-color)] font-extrabold text-sm btn-primary"
            style={{ background: showCreate ? 'rgba(var(--c-blue-rgb),0.28)' : undefined }}
          >
            {showCreate ? '✕ Свернуть создание' : '+ Создать свой клан'}
          </button>

          {showCreate && (
            <div className="card flex flex-col gap-0 border border-[rgba(var(--c-green-rgb),0.22)]">
              <div className="flex items-start justify-between gap-3 mb-[10px]">
                <div>
                  <p className="m-0 font-extrabold">Новый клан</p>
                  <p className="mt-[2px] mb-0 text-[12px] text-tg-hint">Стоимость создания: <strong className="text-[var(--c-gold)]">$1</strong></p>
                </div>
                <span className="text-[11px] font-bold px-2 py-[4px] rounded-full bg-[rgba(var(--c-green-rgb),0.14)] text-[var(--c-green)]">Основатель</span>
              </div>
              <input
                value={newName}
                onChange={e => setNewName(e.target.value)}
                placeholder="Название клана"
                maxLength={CLAN_NAME_MAX_LENGTH}
                className="text-input text-sm"
              />
              <div className="flex justify-between mt-[6px] mb-[12px] text-[11px]">
                <span className={canAffordCreate ? 'text-tg-hint' : 'text-[var(--c-red-soft)]'}>
                  {canAffordCreate ? 'Можно изменить до создания' : 'Недостаточно долларов для создания'}
                </span>
                <span className="text-tg-hint">{trimmedName.length}/{CLAN_NAME_MAX_LENGTH}</span>
              </div>

              <p className="m-0 mb-[8px] text-[13px] font-extrabold">Специализация</p>
              <div className="grid grid-cols-1 gap-[7px] mb-[12px]">
                {CLAN_SPECIALTIES.map(s => (
                  <button
                    key={s.id}
                    onClick={() => setNewSpec(prev => prev === s.id ? null : s.id)}
                    aria-pressed={newSpec === s.id}
                    className="flex items-center gap-3 px-3 py-[11px] rounded-[14px] border cursor-pointer text-left"
                    style={{
                      background: newSpec === s.id ? 'rgba(var(--c-blue-rgb),0.15)' : 'var(--surface-subtle)',
                      borderColor: newSpec === s.id ? 'rgba(var(--c-blue-rgb),0.5)' : 'var(--surface-overlay-border)',
                    }}
                  >
                    <div className="flex-1">
                      <p className="m-0 text-[13px] font-extrabold">{s.label}</p>
                      <p className="m-0 text-[11px] text-tg-hint">{s.desc}</p>
                    </div>
                    <span className={newSpec === s.id ? 'text-[var(--c-blue)] font-extrabold' : 'text-tg-hint'}>{newSpec === s.id ? '✓' : '+'}</span>
                  </button>
                ))}
              </div>
              <button
                onClick={() => void handleCreate()}
                disabled={creating || !canCreate}
                className="w-full py-[12px] rounded-xl border-none cursor-pointer bg-[var(--c-green)] text-[var(--tg-theme-button-text-color)] font-extrabold text-sm disabled:opacity-60"
              >
                {creating ? 'Создаём...' : 'Создать'}
              </button>
            </div>
          )}
        </>
      )}

      {openClans.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="m-0 text-[11px] font-bold text-tg-hint tracking-[0.6px] uppercase">Открытые кланы</p>
            <span className="text-[11px] text-tg-hint">{openClans.length}</span>
          </div>
          <div className="flex flex-col gap-2 stagger-children">
            {openClans.map((clan: ClanOut) => {
              const specialtyLabel = getClanSpecialtyLabel(clan.specialty);
              const isJoining = joiningClanId === clan.idpk;

              return (
                <div key={clan.idpk} className="card card-pressable">
                  <div className="flex gap-3 items-start">
                    <div className="w-11 h-11 rounded-[14px] grid place-items-center text-[22px] shrink-0" style={{ background: 'rgba(var(--c-purple-rgb),0.13)' }}>
                      🏰
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 min-w-0">
                        <p className="m-0 font-extrabold truncate">«{clan.name}»</p>
                        <span className="shrink-0 text-[10px] font-bold px-[6px] py-[2px] rounded-full bg-[rgba(var(--c-gold-rgb),0.13)] text-[var(--c-gold)]">Ур. {clan.level}</span>
                      </div>
                      <p className="mt-[3px] mb-0 text-xs text-tg-hint truncate">
                        👑 {clan.owner_nickname} · {formatMembers(clan.member_count)}
                      </p>
                      <p className="mt-[3px] mb-0 text-[11px] text-tg-hint truncate">
                        {specialtyLabel ?? 'Без специализации'}
                      </p>
                    </div>
                    {!gs.clan && (
                      <button
                        onClick={() => void handleJoin(clan.idpk)}
                        disabled={joiningClanId !== null}
                        className="px-3 py-[8px] rounded-xl border-none cursor-pointer bg-[rgba(var(--c-blue-rgb),0.16)] text-[var(--c-blue)] font-extrabold text-[13px] shrink-0 disabled:opacity-60"
                      >
                        {isJoining ? '...' : 'Вступить'}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!isLoading && !errorMsg && !queryError && openClans.length === 0 && !gs.clan && (
        <div className="card text-center">
          <p className="m-0 text-[28px]">🌱</p>
          <p className="mt-2 mb-1 font-extrabold">Пока нет открытых кланов</p>
          <p className="m-0 text-[13px] text-tg-hint">Создай первый клан и стань основателем сообщества.</p>
        </div>
      )}
    </div>
  );
}
