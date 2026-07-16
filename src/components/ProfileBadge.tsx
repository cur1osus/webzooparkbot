import type { CSSProperties } from 'react';
import { ACHIEVEMENT_TGS, customAchievementImage, PROFILE_ACHIEVEMENT_PREFIX } from '@/data/achievements';
import { profileFrameClass } from '@/data/profileFrames';
import { TgsPlayer } from '@/components/TgsPlayer';

export type ProfileBadgeTone = 'default' | 'gold' | 'silver' | 'bronze' | 'blue';

interface ProfileBadgeProps {
  profileEmoji?: string | null;
  size?: number;
  tone?: ProfileBadgeTone;
  className?: string;
  /** Purchased avatar frame id; draws a decorative ring on the badge rim. */
  frame?: string | null;
}

/**
 * One profile rendering surface for the leaderboard and future profile styles.
 * The data contract stays intentionally small: a badge may be an achievement TGS,
 * a Telegram/custom emoji, or the neutral zoo mark until more cosmetics are added.
 */
export function ProfileBadge({ profileEmoji, size = 44, tone = 'default', className = '', frame }: ProfileBadgeProps) {
  const achievementId = profileEmoji?.startsWith(PROFILE_ACHIEVEMENT_PREFIX)
    ? profileEmoji.slice(PROFILE_ACHIEVEMENT_PREFIX.length)
    : null;
  const achievementTgs = achievementId ? ACHIEVEMENT_TGS[achievementId] : null;
  const achievementImage = achievementId ? customAchievementImage(achievementId) : null;
  const toneClass = `profile-badge-${tone}`;

  const badge = (
    <div
      className={`profile-badge ${toneClass} ${className}`}
      style={{
        width: size,
        height: size,
        '--profile-badge-size': `${size}px`,
      } as CSSProperties}
      aria-hidden="true"
    >
      {achievementImage ? (
        <img src={achievementImage} alt="" className="h-full w-full object-contain p-1" />
      ) : achievementTgs ? (
        <TgsPlayer src={achievementTgs} loop />
      ) : (
        <span className="profile-badge-glyph">{profileEmoji || '🐾'}</span>
      )}
      <span className="profile-badge-sheen" />
    </div>
  );

  const frameClass = profileFrameClass(frame);
  if (!frameClass) return badge;

  // The ring is drawn on top of the badge rim (not around it), so equipping a frame
  // never changes the badge's footprint in tight leaderboard rows. Thickness scales
  // with the badge so it reads the same on a 42px row and an 86px card.
  const ringWidth = Math.max(2, Math.round(size * 0.075));
  return (
    <div className={`profile-badge-frame ${frameClass}`} style={{ '--frame-w': `${ringWidth}px` } as CSSProperties}>
      {badge}
    </div>
  );
}
