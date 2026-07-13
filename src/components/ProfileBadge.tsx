import { ACHIEVEMENT_TGS, PROFILE_ACHIEVEMENT_PREFIX } from '@/data/achievements';
import { TgsPlayer } from '@/components/TgsPlayer';

export type ProfileBadgeTone = 'default' | 'gold' | 'silver' | 'bronze' | 'blue';

interface ProfileBadgeProps {
  profileEmoji?: string | null;
  size?: number;
  tone?: ProfileBadgeTone;
  className?: string;
}

/**
 * One profile rendering surface for the leaderboard and future profile styles.
 * The data contract stays intentionally small: a badge may be an achievement TGS,
 * a Telegram/custom emoji, or the neutral zoo mark until more cosmetics are added.
 */
export function ProfileBadge({ profileEmoji, size = 44, tone = 'default', className = '' }: ProfileBadgeProps) {
  const achievementId = profileEmoji?.startsWith(PROFILE_ACHIEVEMENT_PREFIX)
    ? profileEmoji.slice(PROFILE_ACHIEVEMENT_PREFIX.length)
    : null;
  const achievementTgs = achievementId ? ACHIEVEMENT_TGS[achievementId] : null;
  const toneClass = `profile-badge-${tone}`;

  return (
    <div
      className={`profile-badge ${toneClass} ${className}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      {achievementTgs ? (
        <TgsPlayer src={achievementTgs} loop />
      ) : (
        <span className="profile-badge-glyph">{profileEmoji || '🐾'}</span>
      )}
      <span className="profile-badge-sheen" />
    </div>
  );
}
