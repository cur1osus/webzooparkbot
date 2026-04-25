import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { ClanListResponse, ClanOut, GameState } from '@/types';
import { apiGetClanList, apiCreateClan, apiJoinClan, apiLeaveClan } from '@/api';
import { CLAN_SPECIALTIES, getClanSpecialtyLabel } from '@/utils/clan';

/* ── Specialty visual config ──────────────────────────────────────────── */
const SPEC_CFG: Record<string, { colorRgb: string; color: string; bg: string }> = {
  merchant: { colorRgb: '255,159,10',   color: 'var(--c-amber)',  bg: 'rgba(255,159,10,0.12)' },
  bank:     { colorRgb: '52,199,89',    color: 'var(--c-green)',  bg: 'rgba(52,199,89,0.12)' },
  forge:    { colorRgb: '255,107,61',   color: 'var(--c-orange)', bg: 'rgba(255,107,61,0.12)' },
  collector:{ colorRgb: '48,213,200',   color: 'var(--c-teal)',   bg: 'rgba(48,213,200,0.12)' },
};

function SpecBadge({ specialty }: { specialty: string | null | undefined }) {
  if (!specialty) return null;
  const label = getClanSpecialtyLabel(specialty);
  const cfg = SPEC_CFG[specialty];
  return (
    <span
      className="inline-flex items-center px-[8px] py-[3px] rounded-full text-[11px] font-bold leading-none"
      style={{
        background: cfg?.bg ?? 'rgba(var(--c-purple-rgb),0.15)',
        color: cfg?.color ?? 'var(--c-purple)',
        border: `1px solid rgba(${cfg?.colorRgb ?? 'var(--c-purple-rgb)'},0.3)`,
      }}
    >
      {label}
    </span>
  );
}

/* ── Skeleton pulse ───────────────────────────────────────────────────── */
function Skeleton({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={`rounded-[14px] animate-pulse ${className ?? ''}`}
      style={{ background: 'var(--surface-subtle)', ...style }}
    />
  );
}

/* ── Main component ───────────────────────────────────────────────────── */
export function ClanPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [creating, setCreating]   = useState(false);
  const [newName, setNewName]     = useState('');
  const [newSpec, setNewSpec]     = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg,   setErrorMsg]   = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const { data, error, isLoading, refetch } = useQuery<ClanListResponse>({
    queryKey: ['clans'],
    queryFn:  apiGetClanList,
    staleTime: 30_000,
  });
  const queryError = error instanceof Error ? error.message : null;

  const clearMsgs = () => { setSuccessMsg(null); setErrorMsg(null); };

  const handleCreate = async () => {
    if (newName.trim().length < 3) return;
    setCreating(true); clearMsgs();
    try {
      const res = await apiCreateClan(newName.trim(), newSpec ?? undefined);
      if (res.ok) {
        setSuccessMsg(res.message);
        setShowCreate(false); setNewName(''); setNewSpec(null);
        onRefresh(); void refetch();
      } else setErrorMsg(res.message ?? 'Ошибка');
    } catch (e) { setErrorMsg((e as Error).message ?? 'Ошибка'); }
    finally      { setCreating(false); }
  };

  const handleJoin = async (clanId: number) => {
    clearMsgs();
    try {
      const res = await apiJoinClan(clanId);
      if (res.ok) { setSuccessMsg(res.message); onRefresh(); void refetch(); }
      else          setErrorMsg(res.message ?? 'Ошибка');
    } catch (e) { setErrorMsg((e as Error).message ?? 'Ошибка'); }
  };

  const handleLeave = async () => {
    clearMsgs();
    try {
      const res = await apiLeaveClan();
      if (res.ok) { setSuccessMsg(res.message); onRefresh(); void refetch(); }
      else          setErrorMsg(res.message ?? 'Ошибка');
    } catch (e) { setErrorMsg((e as Error).message ?? 'Ошибка'); }
  };

  return (
    <div className="flex flex-col gap-3 p-[14px]">

      {/* ── Toast ──────────────────────────────────────────────────────── */}
      {successMsg && (
        <div
          className="flex items-center gap-[10px] px-4 py-3 rounded-[13px]"
          style={{ background: 'rgba(52,199,89,0.08)', border: '1px solid rgba(52,199,89,0.22)' }}
        >
          <span className="text-[15px]">✅</span>
          <p className="m-0 text-[13px] font-semibold" style={{ color: 'var(--c-green)' }}>{successMsg}</p>
        </div>
      )}
      {(errorMsg ?? queryError) && (
        <div
          className="flex items-center gap-[10px] px-4 py-3 rounded-[13px]"
          style={{ background: 'rgba(255,59,48,0.08)', border: '1px solid rgba(255,59,48,0.22)' }}
        >
          <span className="text-[15px]">⚠️</span>
          <p className="m-0 text-[13px] font-semibold" style={{ color: 'var(--c-red-soft)' }}>{errorMsg ?? queryError}</p>
        </div>
      )}

      {/* ── My clan hero ───────────────────────────────────────────────── */}
      {gs.clan && (
        <div
          className="relative overflow-hidden rounded-[22px] p-5"
          style={{
            background: 'linear-gradient(135deg, rgba(var(--c-purple-rgb),0.20) 0%, rgba(var(--c-blue-rgb),0.10) 100%)',
            border:     '1px solid rgba(var(--c-purple-rgb),0.28)',
          }}
        >
          {/* Decorative orb */}
          <div
            className="pointer-events-none absolute -top-10 -right-10 w-36 h-36 rounded-full"
            style={{ background: 'radial-gradient(circle, rgba(var(--c-purple-rgb),0.28) 0%, transparent 70%)' }}
          />
          {/* Decorative orb 2 */}
          <div
            className="pointer-events-none absolute -bottom-8 -left-6 w-28 h-28 rounded-full"
            style={{ background: 'radial-gradient(circle, rgba(var(--c-gold-rgb),0.14) 0%, transparent 70%)' }}
          />

          <div className="relative flex flex-col gap-3">
            {/* Name row */}
            <div className="flex items-center gap-[10px]">
              <span className="text-[26px] leading-none drop-shadow-sm">🏰</span>
              <h3
                className="m-0 text-[18px] font-extrabold leading-tight truncate"
                style={{
                  background: 'linear-gradient(90deg, #fff 0%, rgba(var(--c-gold-rgb),0.9) 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                «{gs.clan.name}»
              </h3>
            </div>

            {/* Badges row */}
            <div className="flex items-center flex-wrap gap-[6px]">
              <span
                className="inline-flex items-center gap-[5px] px-[10px] py-[4px] rounded-full text-[12px] font-bold leading-none"
                style={{ background: 'rgba(var(--c-gold-rgb),0.14)', color: 'var(--c-gold)', border: '1px solid rgba(var(--c-gold-rgb),0.28)' }}
              >
                ⚡ Ур. {gs.clan.level}
              </span>
              <span
                className="inline-flex items-center gap-[5px] px-[10px] py-[4px] rounded-full text-[12px] font-bold leading-none"
                style={{ background: 'rgba(var(--c-blue-rgb),0.12)', color: 'var(--c-blue)', border: '1px solid rgba(var(--c-blue-rgb),0.25)' }}
              >
                👥 {gs.clan.member_count}
              </span>
              {gs.clan.role === 'owner' ? (
                <span
                  className="inline-flex items-center gap-[5px] px-[10px] py-[4px] rounded-full text-[12px] font-bold leading-none"
                  style={{ background: 'rgba(var(--c-gold-rgb),0.14)', color: 'var(--c-gold)', border: '1px solid rgba(var(--c-gold-rgb),0.28)' }}
                >
                  👑 Владелец
                </span>
              ) : (
                <span
                  className="inline-flex items-center gap-[5px] px-[10px] py-[4px] rounded-full text-[12px] font-semibold leading-none"
                  style={{ background: 'var(--surface-subtle)', color: 'var(--tg-theme-hint-color)', border: '1px solid var(--surface-overlay-border)' }}
                >
                  👤 Участник
                </span>
              )}
              {gs.clan.specialty && <SpecBadge specialty={gs.clan.specialty} />}
            </div>

            {/* Leave button */}
            <button
              onClick={() => void handleLeave()}
              className="self-start flex items-center gap-[7px] px-[14px] py-[8px] rounded-[10px] cursor-pointer text-[13px] font-bold active:scale-95 transition-transform"
              style={{
                background: 'rgba(255,59,48,0.09)',
                color:      'var(--c-red-soft)',
                border:     '1px solid rgba(255,59,48,0.22)',
              }}
            >
              🚪 Покинуть клан
            </button>
          </div>
        </div>
      )}

      {/* ── Create clan ────────────────────────────────────────────────── */}
      {!gs.clan && (
        <div className="flex flex-col gap-[10px]">
          <button
            onClick={() => { setShowCreate(s => !s); clearMsgs(); }}
            className="relative overflow-hidden w-full py-[14px] rounded-[15px] border-none cursor-pointer font-extrabold text-[15px] active:scale-[0.98] transition-transform"
            style={{
              background: showCreate
                ? 'rgba(var(--c-blue-rgb),0.12)'
                : 'linear-gradient(135deg, rgba(var(--c-purple-rgb),1) 0%, rgba(var(--c-blue-rgb),1) 100%)',
              color:  showCreate ? 'var(--c-blue)' : '#fff',
              border: showCreate ? '1px solid rgba(var(--c-blue-rgb),0.3)' : 'none',
              boxShadow: showCreate ? 'none' : '0 4px 20px rgba(var(--c-purple-rgb),0.35)',
            }}
          >
            {!showCreate && (
              <span
                className="pointer-events-none absolute inset-0 rounded-[15px]"
                style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.08) 0%, transparent 60%)' }}
              />
            )}
            {showCreate ? '✕ Отмена' : '⚔️ Создать клан'}
          </button>

          {showCreate && (
            <div
              className="rounded-[20px] p-4 flex flex-col gap-4"
              style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)' }}
            >
              {/* Name input */}
              <div className="flex flex-col gap-[8px]">
                <div className="flex items-center justify-between">
                  <p className="m-0 text-[11px] font-bold uppercase tracking-[0.6px] text-tg-hint">
                    Название клана
                  </p>
                  <p
                    className="m-0 text-[11px] font-semibold"
                    style={{ color: newName.length >= 28 ? 'var(--c-amber)' : 'var(--tg-theme-hint-color)' }}
                  >
                    {newName.length}/30
                  </p>
                </div>
                <input
                  value={newName}
                  onChange={e => setNewName(e.target.value)}
                  placeholder="Введите название…"
                  maxLength={30}
                  className="text-input w-full text-[14px]"
                />
              </div>

              {/* Specialty grid */}
              <div className="flex flex-col gap-[8px]">
                <p className="m-0 text-[11px] font-bold uppercase tracking-[0.6px] text-tg-hint">
                  Специализация
                </p>
                <div className="grid grid-cols-2 gap-[8px]">
                  {CLAN_SPECIALTIES.map(s => {
                    const cfg     = SPEC_CFG[s.id];
                    const selected = newSpec === s.id;
                    const parts    = s.label.split(' ');
                    const icon     = parts[0];
                    const name     = parts.slice(1).join(' ');
                    return (
                      <button
                        key={s.id}
                        onClick={() => setNewSpec(prev => prev === s.id ? null : s.id)}
                        className="relative flex flex-col items-start p-3 rounded-[13px] border cursor-pointer text-left active:scale-[0.97] transition-transform"
                        style={{
                          background:   selected ? cfg?.bg ?? 'rgba(var(--c-blue-rgb),0.12)' : 'var(--surface-subtle)',
                          borderColor:  selected
                            ? (cfg ? `rgba(${cfg.colorRgb},0.45)` : 'rgba(var(--c-blue-rgb),0.4)')
                            : 'var(--surface-overlay-border)',
                        }}
                      >
                        {selected && (
                          <span
                            className="absolute top-[8px] right-[9px] text-[11px] font-black"
                            style={{ color: cfg?.color ?? 'var(--c-blue)' }}
                          >
                            ✓
                          </span>
                        )}
                        <span className="text-[22px] leading-none mb-[6px]">{icon}</span>
                        <p
                          className="m-0 text-[12px] font-bold leading-tight"
                          style={{ color: selected ? (cfg?.color ?? 'var(--c-blue)') : 'var(--tg-theme-text-color)' }}
                        >
                          {name}
                        </p>
                        <p className="m-0 mt-[3px] text-[10px] leading-tight" style={{ color: 'var(--tg-theme-hint-color)' }}>
                          {s.desc}
                        </p>
                      </button>
                    );
                  })}
                </div>
                {!newSpec && (
                  <p className="m-0 text-[11px] text-tg-hint">Можно пропустить — нейтральный клан</p>
                )}
              </div>

              {/* Submit */}
              <button
                onClick={() => void handleCreate()}
                disabled={creating || newName.trim().length < 3}
                className="relative overflow-hidden w-full py-[12px] rounded-[12px] border-none cursor-pointer font-extrabold text-[15px] text-white active:scale-[0.98] transition-transform disabled:opacity-50"
                style={{
                  background: 'linear-gradient(135deg, rgba(var(--c-purple-rgb),1) 0%, rgba(var(--c-blue-rgb),1) 100%)',
                  boxShadow: 'none',
                }}
              >
                <span
                  className="pointer-events-none absolute inset-0 rounded-[12px]"
                  style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.08) 0%, transparent 60%)' }}
                />
                {creating ? '⏳ Создаём…' : '⚔️ Основать клан'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Clan list ──────────────────────────────────────────────────── */}
      {(isLoading || (data?.clans && data.clans.length > 0)) && (
        <div className="flex flex-col gap-[10px]">
          <p
            className="m-0 text-[11px] font-bold uppercase tracking-[0.7px]"
            style={{ color: 'var(--tg-theme-hint-color)' }}
          >
            Открытые кланы
          </p>

          {isLoading && (
            <div className="flex flex-col gap-2">
              <Skeleton style={{ height: 72 }} />
              <Skeleton style={{ height: 72, opacity: 0.7 }} />
              <Skeleton style={{ height: 72, opacity: 0.45 }} />
            </div>
          )}

          {!isLoading && data?.clans && (
            <div className="flex flex-col gap-[8px]">
              {data.clans.map((clan: ClanOut, idx: number) => {
                const isFirst = idx === 0;
                return (
                  <div
                    key={clan.idpk}
                    className="flex items-center gap-3 rounded-[16px] px-[14px] py-[11px]"
                    style={{
                      background: isFirst
                        ? 'linear-gradient(135deg, rgba(var(--c-gold-rgb),0.07) 0%, rgba(var(--c-purple-rgb),0.06) 100%)'
                        : 'var(--card-bg)',
                      border: isFirst
                        ? '1px solid rgba(var(--c-gold-rgb),0.22)'
                        : '1px solid var(--card-border)',
                    }}
                  >
                    {/* Rank bubble */}
                    <div
                      className="w-[28px] h-[28px] rounded-full flex items-center justify-center text-[12px] font-black shrink-0"
                      style={isFirst
                        ? { background: 'rgba(var(--c-gold-rgb),0.18)', color: 'var(--c-gold)', border: '1px solid rgba(var(--c-gold-rgb),0.32)' }
                        : { background: 'var(--surface-subtle)', color: 'var(--tg-theme-hint-color)', border: '1px solid var(--surface-overlay-border)' }
                      }
                    >
                      {isFirst ? '👑' : idx + 1}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <p className="m-0 text-[14px] font-bold truncate leading-tight">«{clan.name}»</p>
                      <div className="flex items-center flex-wrap gap-[4px] mt-[4px]">
                        <span className="text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>⚡ {clan.level}</span>
                        <span className="text-[11px]" style={{ color: 'var(--surface-overlay-border)' }}>·</span>
                        <span className="text-[11px]" style={{ color: 'var(--tg-theme-hint-color)' }}>👥 {clan.member_count}</span>
                        <span className="text-[11px]" style={{ color: 'var(--surface-overlay-border)' }}>·</span>
                        <span className="text-[11px] max-w-[90px] truncate" style={{ color: 'var(--tg-theme-hint-color)' }}>
                          {clan.owner_nickname}
                        </span>
                        {clan.specialty && (
                          <>
                            <span className="text-[11px]" style={{ color: 'var(--surface-overlay-border)' }}>·</span>
                            <SpecBadge specialty={clan.specialty} />
                          </>
                        )}
                      </div>
                    </div>

                    {/* Join button */}
                    {!gs.clan && (
                      <button
                        onClick={() => void handleJoin(clan.idpk)}
                        className="shrink-0 px-[12px] py-[7px] rounded-[9px] border-none cursor-pointer text-[12px] font-bold active:scale-95 transition-transform"
                        style={{
                          background: 'rgba(var(--c-blue-rgb),0.12)',
                          color:      'var(--c-blue)',
                          border:     '1px solid rgba(var(--c-blue-rgb),0.25)',
                        }}
                      >
                        Вступить
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Empty state ────────────────────────────────────────────────── */}
      {!isLoading && !(errorMsg ?? queryError) && data?.clans.length === 0 && !gs.clan && (
        <div
          className="rounded-[20px] p-8 flex flex-col items-center gap-3 text-center"
          style={{ background: 'var(--surface-subtle)', border: '1px dashed rgba(var(--c-purple-rgb),0.25)' }}
        >
          <span className="text-[40px] leading-none">🏰</span>
          <div>
            <p className="m-0 text-[15px] font-bold">Кланов пока нет</p>
            <p className="m-0 mt-[4px] text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
              Стань первым основателем!
            </p>
          </div>
        </div>
      )}

    </div>
  );
}
