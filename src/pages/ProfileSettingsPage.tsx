import { useState } from 'react';
import type { GameState, GameTheme } from '@/types';
import { apiSetTheme, apiUpdateNickname } from '@/api';
import { PageHeader } from '@/components/PageHeader';
import { ProfileBadge } from '@/components/ProfileBadge';
import { Nickname } from '@/components/NicknameEffects';

const NICKNAME_COST = 50;

const THEMES: Array<{ id: GameTheme; label: string; note: string; colors: [string, string, string] }> = [
  { id: 'dusk', label: 'Сумерки', note: 'Тёплый графит', colors: ['#141414', '#1e1e1d', '#f0a93c'] },
  { id: 'meadow', label: 'Луг', note: 'Фисташковый свет', colors: ['#101812', '#18251a', '#7fba62'] },
  { id: 'ocean', label: 'Лагуна', note: 'Глубокая вода', colors: ['#0b151c', '#11232d', '#4fc0cf'] },
  { id: 'sunset', label: 'Закат', note: 'Терракота и янтарь', colors: ['#1b1210', '#2b1b17', '#ee8f53'] },
];

export function ProfileSettingsPage({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [nickname, setNickname] = useState(gs.nickname);
  const [theme, setTheme] = useState<GameTheme>(gs.theme ?? 'dusk');
  const [savingNickname, setSavingNickname] = useState(false);
  const [savingTheme, setSavingTheme] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cleanNickname = nickname.trim();
  const nicknameChanged = cleanNickname.length > 0 && cleanNickname !== gs.nickname;

  const saveNickname = async () => {
    if (!nicknameChanged || savingNickname) return;
    setSavingNickname(true);
    setMessage(null);
    setError(null);
    try {
      const result = await apiUpdateNickname(cleanNickname);
      setNickname(result.nickname);
      setMessage(`Никнейм изменён. Списано ${NICKNAME_COST} 🐾.`);
      onRefresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось изменить никнейм');
    } finally {
      setSavingNickname(false);
    }
  };

  const chooseTheme = async (next: GameTheme) => {
    if (savingTheme || next === gs.theme) return;
    setTheme(next);
    setSavingTheme(true);
    setMessage(null);
    setError(null);
    try {
      await apiSetTheme(next);
      setMessage('Тема оформления сохранена.');
      onRefresh();
    } catch (cause) {
      setTheme(gs.theme ?? 'dusk');
      setError(cause instanceof Error ? cause.message : 'Не удалось сохранить тему');
    } finally {
      setSavingTheme(false);
    }
  };

  return (
    <div className="page-content-safe">
      <PageHeader emoji="⚙️" title="Профиль" subtitle="Имя и атмосфера твоего зоопарка" accent="var(--c-gold-rgb)" />

      {(message || error) && (
        <div className="px-[14px] pt-3">
          <div className="card" style={{ borderColor: error ? 'rgba(var(--c-red-rgb),0.35)' : 'rgba(var(--c-green-rgb),0.35)', background: error ? 'rgba(var(--c-red-rgb),0.08)' : 'rgba(var(--c-green-rgb),0.08)' }}>
            <p className="m-0 text-[13px] font-bold" style={{ color: error ? 'var(--c-red-soft)' : 'var(--c-green)' }}>{error ?? message}</p>
          </div>
        </div>
      )}

      <div className="px-[14px] pt-3 flex flex-col gap-3">
        <section className="card flex items-center gap-3" aria-label="Текущий профиль">
          <ProfileBadge profileEmoji={gs.profile_emoji} size={56} frame={gs.profile_frame} />
          <div className="min-w-0">
            <Nickname as="p" name={gs.nickname} color={gs.nickname_color} className="m-0 text-[18px] font-black truncate" />
            <p className="m-0 mt-1 text-[12px] text-tg-hint">🐾 {gs.paw_coins} PawCoins</p>
          </div>
        </section>

        <section className="card">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="m-0 text-[16px] font-black">Никнейм</h2>
              <p className="m-0 mt-1 text-[12px] leading-relaxed text-tg-hint">Изменение стоит {NICKNAME_COST} 🐾 и сразу видно в рейтинге и клане.</p>
            </div>
            <span className="shrink-0 rounded-full px-2 py-1 text-[10px] font-black" style={{ background: 'rgba(var(--c-purple-rgb),0.14)', color: 'var(--c-purple)' }}>{NICKNAME_COST} 🐾</span>
          </div>
          <input
            value={nickname}
            onChange={event => setNickname(event.target.value.slice(0, 32))}
            className="text-input mt-3"
            maxLength={32}
            aria-label="Новый никнейм"
          />
          <button
            type="button"
            onClick={() => void saveNickname()}
            disabled={!nicknameChanged || savingNickname || gs.paw_coins < NICKNAME_COST}
            className="mt-3 min-h-[46px] w-full rounded-xl border-none text-[14px] font-extrabold disabled:opacity-50"
            style={{ background: 'var(--c-purple)', color: 'var(--tg-theme-button-text-color)' }}
          >
            {savingNickname ? 'Сохраняем…' : gs.paw_coins < NICKNAME_COST ? 'Нужно больше PawCoins' : 'Изменить никнейм'}
          </button>
        </section>

        <section className="card">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="m-0 text-[16px] font-black">Тема оформления</h2>
              <p className="m-0 mt-1 text-[12px] leading-relaxed text-tg-hint">Меняет фон, поверхности и акцент всего приложения.</p>
            </div>
            {savingTheme && <span className="text-[11px] font-bold text-tg-hint">Сохраняем…</span>}
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {THEMES.map(option => {
              const active = option.id === theme;
              return (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => void chooseTheme(option.id)}
                  aria-pressed={active}
                  className="min-h-[92px] rounded-2xl border-none px-3 py-3 text-left"
                  style={{ background: option.colors[0], border: `1px solid ${active ? option.colors[2] : 'rgba(255,255,255,0.12)'}`, boxShadow: active ? `0 0 0 1px ${option.colors[2]}55, 0 8px 20px ${option.colors[2]}20` : 'none' }}
                >
                  <span className="flex gap-1.5">
                    {option.colors.map(color => <span key={color} className="h-4 w-4 rounded-full" style={{ background: color, border: '1px solid rgba(255,255,255,0.18)' }} />)}
                  </span>
                  <strong className="mt-3 block text-[13px]" style={{ color: '#fff' }}>{option.label}</strong>
                  <span className="mt-1 block text-[10px]" style={{ color: 'rgba(255,255,255,0.64)' }}>{option.note}</span>
                </button>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
