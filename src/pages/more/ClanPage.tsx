import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { ClanListResponse, ClanOut, GameState } from '@/types';
import { apiGetClanList, apiCreateClan, apiJoinClan, apiLeaveClan } from '@/api';
import { CLAN_SPECIALTIES, getClanSpecialtyLabel } from '@/utils/clan';

export function ClanPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [newSpec, setNewSpec] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const { data, error, isLoading, refetch } = useQuery<ClanListResponse>({
    queryKey: ['clans'],
    queryFn: apiGetClanList,
    staleTime: 30_000,
  });
  const queryError = error instanceof Error ? error.message : null;

  const clearMsgs = () => { setSuccessMsg(null); setErrorMsg(null); };

  const handleCreate = async () => {
    if (newName.trim().length < 3) return;
    setCreating(true);
    clearMsgs();
    try {
      const res = await apiCreateClan(newName.trim(), newSpec ?? undefined);
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
    clearMsgs();
    try {
      const res = await apiJoinClan(clanId);
      if (res.ok) setSuccessMsg(res.message);
      else setErrorMsg(res.message ?? 'Ошибка');
    } catch (e) {
      setErrorMsg((e as Error).message ?? 'Ошибка');
    }
  };

  const handleLeave = async () => {
    clearMsgs();
    try {
      const res = await apiLeaveClan();
      if (res.ok) {
        setSuccessMsg(res.message);
        onRefresh();
        void refetch();
      } else {
        setErrorMsg(res.message ?? 'Ошибка');
      }
    } catch (e) {
      setErrorMsg((e as Error).message ?? 'Ошибка');
    }
  };

  return (
    <div className="p-[14px] flex flex-col gap-3">
      {isLoading && <p className="text-center text-tg-hint">Загрузка...</p>}

      {successMsg && (
        <div className="card bg-[rgba(var(--c-green-rgb),0.1)] border border-[rgba(var(--c-green-rgb),0.3)]">
          <p className="m-0 text-[var(--c-green)]">✅ {successMsg}</p>
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
        <div className="card border border-[rgba(var(--c-purple-rgb),0.3)]">
          <p className="m-0 mb-[6px] font-bold text-[15px]">🏰 «{gs.clan.name}»</p>
          <p className="m-0 mb-1 text-[13px] text-tg-hint">
            Ур. {gs.clan.level} · {gs.clan.member_count} уч.
            {gs.clan.specialty ? ` · ${getClanSpecialtyLabel(gs.clan.specialty)}` : ' · Без специализации'}
          </p>
          <p className="m-0 mb-[10px] text-xs text-tg-hint">
            Роль: <strong>{gs.clan.role === 'owner' ? '👑 Владелец' : '👤 Участник'}</strong>
          </p>
          <button
            onClick={() => void handleLeave()}
            className="px-[14px] py-2 rounded-lg border-none cursor-pointer bg-[rgba(var(--c-red-rgb),0.12)] text-[var(--c-red-soft)] font-semibold text-[13px]"
          >
            Покинуть клан
          </button>
        </div>
      )}

      {!gs.clan && (
        <>
          <button
            onClick={() => { setShowCreate(s => !s); clearMsgs(); }}
            className="py-3 rounded-[10px] border-none cursor-pointer text-[var(--tg-theme-button-text-color)] font-bold text-sm"
            style={{ background: showCreate ? 'rgba(var(--c-blue-rgb),0.3)' : 'var(--c-blue)' }}
          >
            {showCreate ? '✕ Отмена' : '+ Создать клан'}
          </button>

          {showCreate && (
            <div className="card flex flex-col gap-0">
              <p className="m-0 mb-[10px] font-bold">Новый клан</p>
              <input
                value={newName}
                onChange={e => setNewName(e.target.value)}
                placeholder="Название клана (мин. 3 символа)"
                maxLength={30}
                className="text-input mb-[10px] text-sm"
              />
              <p className="m-0 mb-[8px] text-[13px] font-semibold">Специализация (необязательно):</p>
              <div className="flex flex-col gap-[6px] mb-[10px]">
                {CLAN_SPECIALTIES.map(s => (
                  <button
                    key={s.id}
                    onClick={() => setNewSpec(prev => prev === s.id ? null : s.id)}
                    className="flex items-center gap-3 px-3 py-[10px] rounded-[10px] border cursor-pointer text-left"
                    style={{
                      background: newSpec === s.id ? 'rgba(var(--c-blue-rgb),0.15)' : 'var(--surface-subtle)',
                      borderColor: newSpec === s.id ? 'rgba(var(--c-blue-rgb),0.5)' : 'var(--surface-overlay-border)',
                    }}
                  >
                    <div className="flex-1">
                      <p className="m-0 text-[13px] font-semibold">{s.label}</p>
                      <p className="m-0 text-[11px] text-tg-hint">{s.desc}</p>
                    </div>
                    {newSpec === s.id && <span className="text-[var(--c-blue)]">✓</span>}
                  </button>
                ))}
              </div>
              <button
                onClick={() => void handleCreate()}
                disabled={creating || newName.trim().length < 3}
                className="w-full py-[10px] rounded-[10px] border-none cursor-pointer bg-[var(--c-green)] text-[var(--tg-theme-button-text-color)] font-bold text-sm disabled:opacity-60"
              >
                {creating ? 'Создаём...' : 'Создать'}
              </button>
            </div>
          )}
        </>
      )}

      {data?.clans && data.clans.length > 0 && (
        <div>
          <p className="m-0 mb-2 text-[11px] font-bold text-tg-hint tracking-[0.6px] uppercase">Открытые кланы</p>
          <div className="flex flex-col gap-2">
            {data.clans.map((clan: ClanOut) => (
              <div key={clan.idpk} className="card">
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                    <p className="m-0 font-bold truncate">🏰 «{clan.name}»</p>
                    <p className="mt-[2px] mb-0 text-xs text-tg-hint">
                      Ур. {clan.level} · {clan.member_count} уч. · {clan.owner_nickname}
                      {clan.specialty ? ` · ${getClanSpecialtyLabel(clan.specialty)}` : ''}
                    </p>
                  </div>
                  {!gs.clan && (
                    <button
                      onClick={() => void handleJoin(clan.idpk)}
                      className="ml-2 px-3 py-[7px] rounded-lg border-none cursor-pointer bg-[rgba(var(--c-blue-rgb),0.15)] text-[var(--c-blue)] font-semibold text-[13px] shrink-0"
                    >
                      Вступить
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!isLoading && !errorMsg && !queryError && data?.clans.length === 0 && !gs.clan && (
        <div className="card text-center">
          <p className="m-0 text-tg-hint">Открытых кланов нет. Создай первый!</p>
        </div>
      )}
    </div>
  );
}
