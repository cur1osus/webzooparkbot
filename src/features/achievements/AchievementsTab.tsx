import { TgsPlayer } from '@/components/TgsPlayer';
import { ACHIEVEMENT_TGS, profileAchievementValue } from '@/data/achievements';
import type { Achievement } from '@/types';

export function AchievementsTab({
  achievements,
  profileAvatar,
  onSetProfileAvatar,
}: {
  achievements: Achievement[];
  profileAvatar: string | null;
  onSetProfileAvatar: (avatar: string | null) => void;
}) {
  const completed = achievements.filter(achievement => achievement.completed).length;

  return (
    <div className="px-[14px] pt-3 pb-4 page-enter">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <p className="m-0 text-[11px] font-extrabold uppercase tracking-[1px] text-tg-hint">Коллекция наград</p>
          <h2 className="m-0 mt-1 text-[20px] font-extrabold">Твои медали</h2>
        </div>
        <span
          className="shrink-0 rounded-full px-3 py-[6px] text-[12px] font-extrabold tabular-nums"
          style={{
            color: 'var(--c-gold)',
            background: 'rgba(var(--c-gold-rgb),0.12)',
            border: '1px solid rgba(var(--c-gold-rgb),0.28)',
          }}
        >
          {completed}/{achievements.length} открыто
        </span>
      </div>

      <div className="flex flex-col gap-2">
        {achievements.map(achievement => (
          <div key={achievement.id}>
            <AchievementCard
              achievement={achievement}
              profileAvatar={profileAvatar}
              onSetProfileAvatar={onSetProfileAvatar}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function AchievementCard({
  achievement,
  profileAvatar,
  onSetProfileAvatar,
}: {
  achievement: Achievement;
  profileAvatar: string | null;
  onSetProfileAvatar: (avatar: string | null) => void;
}) {
  const percent = Math.min(100, (achievement.value / achievement.target) * 100);
  const art = ACHIEVEMENT_TGS[achievement.id] ?? ACHIEVEMENT_TGS.first_beast;
  const profileValue = profileAchievementValue(achievement.id);
  const isProfileAvatar = profileAvatar === profileValue;

  return (
    <article
      className="card flex items-center gap-3"
      style={{
        padding: '11px 12px',
        borderColor: achievement.completed
          ? 'rgba(var(--c-gold-rgb),0.48)'
          : 'color-mix(in srgb, var(--tg-theme-text-color) 9%, transparent)',
        boxShadow: achievement.completed
          ? '0 0 18px rgba(var(--c-gold-rgb),0.08), inset 0 1px 0 rgba(var(--c-gold-rgb),0.16)'
          : undefined,
      }}
    >
      <div
        className="relative grid h-[72px] w-[72px] shrink-0 place-items-center rounded-full"
        style={{
          background: `conic-gradient(var(--c-gold) ${percent}%, color-mix(in srgb, var(--tg-theme-hint-color) 19%, transparent) 0)`,
          boxShadow: achievement.completed ? '0 0 16px rgba(var(--c-gold-rgb),0.2)' : undefined,
        }}
        aria-label={`Прогресс: ${achievement.value} из ${achievement.target}`}
      >
        <div
          className="grid h-[62px] w-[62px] place-items-center overflow-hidden rounded-full"
          style={{
            background: 'var(--tg-theme-secondary-bg-color)',
            border: '2px solid color-mix(in srgb, var(--c-gold) 18%, transparent)',
          }}
        >
          <TgsPlayer src={art} size={56} loop />
        </div>
        <span
          className="absolute -bottom-[2px] right-[1px] grid h-[20px] min-w-[20px] place-items-center rounded-full px-1 text-[10px] font-black"
          style={{
            color: achievement.completed ? '#241c08' : 'var(--tg-theme-text-color)',
            background: achievement.completed ? 'var(--c-gold)' : 'var(--tg-theme-secondary-bg-color)',
            border: `1px solid ${achievement.completed ? 'var(--c-gold)' : 'color-mix(in srgb, var(--tg-theme-hint-color) 30%, transparent)'}`,
          }}
        >
          {achievement.completed ? '✓' : `${Math.round(percent)}%`}
        </span>
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start gap-2">
          <h3 className="m-0 min-w-0 flex-1 text-[15px] font-extrabold leading-tight">{achievement.title}</h3>
          {achievement.completed && (
            <span className="shrink-0 text-[10px] font-extrabold uppercase tracking-[0.5px]" style={{ color: 'var(--c-gold)' }}>
              Получено
            </span>
          )}
        </div>
        <p className="m-0 mt-[3px] text-[12px] leading-snug text-tg-hint">{achievement.description}</p>
        <div className="mt-[8px] flex items-center gap-2">
          <div className="h-[5px] min-w-0 flex-1 overflow-hidden rounded-full" style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 14%, transparent)' }}>
            <div
              className="h-full rounded-full transition-[width] duration-500"
              style={{ width: `${percent}%`, background: 'linear-gradient(90deg, var(--c-amber), var(--c-gold))' }}
            />
          </div>
          <span className="shrink-0 text-[12px] font-extrabold tabular-nums" style={{ color: achievement.completed ? 'var(--c-gold)' : 'var(--tg-theme-text-color)' }}>
            {achievement.value}/{achievement.target}
          </span>
        </div>
        {achievement.completed && (
          <button
            type="button"
            onClick={() => onSetProfileAvatar(isProfileAvatar ? null : profileValue)}
            className="mt-[8px] rounded-lg border px-2 py-[4px] text-[11px] font-extrabold"
            style={{
              color: isProfileAvatar ? '#241c08' : 'var(--c-gold)',
              background: isProfileAvatar ? 'var(--c-gold)' : 'rgba(var(--c-gold-rgb),0.10)',
              borderColor: 'rgba(var(--c-gold-rgb),0.35)',
            }}
          >
            {isProfileAvatar ? 'В профиле · убрать' : 'Поставить в профиль'}
          </button>
        )}
      </div>
    </article>
  );
}
