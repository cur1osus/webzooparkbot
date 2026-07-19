import { createPortal } from 'react-dom';
import { useQuery } from '@tanstack/react-query';
import { useCallback, useRef, useState } from 'react';
import type { PublicProfile, TopEntry } from '@/types';
import { apiGetPublicProfile, apiGetTop } from '@/api';
import { fmt } from '@/utils/format';
import { ProfileBadge, type ProfileBadgeTone } from '@/components/ProfileBadge';
import { Nickname } from '@/components/NicknameEffects';
import { wallpaperClass } from '@/data/profileWallpapers';
import { DEVELOPER_TG_ID } from '@/lib/access';
import { PROPERTY_ICON } from '@/data/itemProperties';

function rankTone(rank: number): ProfileBadgeTone {
  if (rank === 1) return 'gold';
  if (rank === 2) return 'silver';
  if (rank === 3) return 'bronze';
  return 'default';
}

function RankMark({ rank, podium = false }: { rank: number; podium?: boolean }) {
  return (
    <span className={`top-rank-mark ${podium ? 'top-rank-mark-podium' : ''} top-rank-mark-${rankTone(rank)}`}>
      #{rank}
    </span>
  );
}

function PlayerName({ entry, size = 'normal' }: { entry: Pick<TopEntry, 'nickname' | 'nickname_color' | 'is_me'>; size?: 'normal' | 'large' }) {
  return (
    <Nickname
      as="p"
      name={entry.nickname}
      color={entry.nickname_color}
      className={`m-0 top-player-name ${size === 'large' ? 'text-[17px] top-player-name-large' : 'text-[14px]'}`}
      style={{ fontWeight: entry.is_me ? 900 : 800 }}
    />
  );
}

function WallpaperLayer({ wallpaper, className }: { wallpaper: string | null | undefined; className: string }) {
  if (!wallpaper || wallpaper === 'none') return null;
  return <div className={`profile-wallpaper ${className} ${wallpaperClass(wallpaper)}`} aria-hidden="true" />;
}

function PublicProfileSheet({
  entry,
  profile,
  isLoading,
  error,
  onClose,
}: {
  entry: TopEntry;
  profile: PublicProfile | undefined;
  isLoading: boolean;
  error: boolean;
  onClose: () => void;
}) {
  return createPortal(
    <div className="modal-backdrop fixed inset-0 z-[300] flex items-end justify-center" onClick={onClose} role="presentation">
      <section
        className="sheet-panel top-profile-sheet w-full max-w-[480px] rounded-t-3xl"
        onClick={event => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={`Профиль игрока ${entry.nickname}`}
      >
        <div className="top-profile-sheet-handle" />
        <div className="top-profile-sheet-toolbar">
          <span className="top-eyebrow">ПРОФИЛЬ ИГРОКА</span>
          <button type="button" className="top-profile-close" onClick={onClose}>Закрыть</button>
        </div>

        {isLoading && <p className="top-profile-state">Загружаем профиль...</p>}
        {error && <p className="top-profile-state top-profile-state-error">Не удалось загрузить профиль.</p>}

        {profile && (
          <div className="top-profile-content">
            <div className="top-profile-identity">
              {profile.profile_wallpaper && profile.profile_wallpaper !== 'none' && (
                <div className={`profile-wallpaper ${wallpaperClass(profile.profile_wallpaper)}`} aria-hidden="true" />
              )}
              <div className="relative z-[1] flex items-center gap-[13px] w-full min-w-0">
                <ProfileBadge profileEmoji={profile.profile_emoji} fallbackTgId={profile.tg_id} size={86} tone={rankTone(profile.rank)} frame={profile.profile_frame} />
                <div className="min-w-0 flex-1">
                  <PlayerName entry={{ ...profile, is_me: entry.is_me }} size="large" />
                  <p className="m-0 mt-1 text-[12px] text-tg-hint">#{profile.rank} место в рейтинге</p>
                  {profile.clan && (
                    <p className="m-0 mt-2 text-[11px] font-bold" style={{ color: 'var(--c-purple)' }}>
                      🏰 {profile.clan.name} · уровень {profile.clan.level}
                    </p>
                  )}
                </div>
              </div>
            </div>

            <div className="top-profile-stats">
              <div><strong className="top-profile-stat-income">+{fmt(profile.income_rub_per_min)} ₽</strong><span>доход / мин</span></div>
              <div><strong className={profile.income_rub_per_min - profile.upkeep_rub_per_min >= 0 ? 'top-profile-stat-income' : 'top-profile-stat-expense'}>{fmt(profile.income_rub_per_min - profile.upkeep_rub_per_min)} ₽</strong><span>чистыми / мин</span></div>
              <div><strong>{profile.animals_count}</strong><span>животных</span></div>
              <div><strong>{profile.species_count}</strong><span>видов</span></div>
              <div><strong>{profile.localities_count}</strong><span>местностей</span></div>
              <div><strong>{profile.achievements_completed}/{profile.achievements_total}</strong><span>медалей</span></div>
            </div>

            <div className="top-profile-section">
              <p className="top-eyebrow m-0">РАЗВИТИЕ ЗООПАРКА</p>
              <div className="top-profile-development">
                <div><strong>{profile.genetics_level}</strong><span>генетический центр</span></div>
                <div><strong>{profile.vet_level}</strong><span>ветеринарный блок</span></div>
                <div><strong>{profile.locality_levels}</strong><span>уровней местностей</span></div>
              </div>
            </div>

            <div className="top-profile-section">
              <div className="flex items-center justify-between gap-3">
                <p className="top-eyebrow m-0">КОЛЛЕКЦИЯ</p>
                <span className="text-[10px] text-tg-hint">{profile.animals_count} животных</span>
              </div>
              {profile.species.length > 0 ? (
                <div className="top-profile-species">
                  {profile.species.map(species => (
                    <span key={species.name}><b>{species.emoji}</b>{species.name}<em>×{species.count}</em></span>
                  ))}
                </div>
              ) : (
                <p className="m-0 mt-2 text-[12px] text-tg-hint">Коллекция пока пуста.</p>
              )}
            </div>

            <div className="top-profile-section">
              <div className="flex items-center justify-between gap-3">
                <p className="top-eyebrow m-0">АКТИВИРОВАННЫЕ ПРЕДМЕТЫ</p>
                <span className="text-[10px] text-tg-hint">{profile.active_items.length} шт.</span>
              </div>
              {profile.active_items.length > 0 ? (
                <div className="mt-2 flex flex-col gap-2">
                  {profile.active_items.map(item => (
                    <div key={item.id} className="rounded-xl px-3 py-2 surface-subtle flex items-center gap-3">
                      <span className="text-[22px] shrink-0">{item.icon}</span>
                      <div className="min-w-0 flex-1">
                        <p className="m-0 text-[12px] font-bold truncate">{item.name}</p>
                        <div className="mt-1 flex flex-col gap-1">
                          <p className="m-0 text-[10px] text-tg-hint">ур. {item.level}</p>
                          {item.properties.length > 0 ? item.properties.map((property, index) => (
                            <p key={`${property.kind}-${property.species_code ?? 'all'}-${index}`} className="m-0 text-[10px] leading-snug text-tg-hint">
                              {PROPERTY_ICON[property.kind] ?? '✨'} {property.label}
                            </p>
                          )) : <p className="m-0 text-[10px] text-tg-hint">Без свойств</p>}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="m-0 mt-2 text-[12px] text-tg-hint">Активированных предметов пока нет.</p>
              )}
            </div>

            <p className="top-profile-footnote">В игре с {new Date(profile.registered_at).toLocaleDateString('ru-RU')}</p>
          </div>
        )}
      </section>
    </div>,
    document.body,
  );
}

function IncomeGapChart({ entries, onSelect }: { entries: TopEntry[]; onSelect: (entry: TopEntry) => void }) {
  const chartEntries = entries.slice(0, 5);
  const leaderIncome = chartEntries[0]?.income_rub_per_min ?? 0;

  return (
    <section className="top-gap-chart">
      <div className="top-section-heading">
        <h2 className="m-0 text-[18px] font-black tracking-[-0.03em]">Разрыв с лидером</h2>
      </div>
      <div className="top-gap-list">
        {chartEntries.map(entry => {
          const share = leaderIncome > 0 ? Math.max(8, Math.round((entry.income_rub_per_min / leaderIncome) * 100)) : 0;
          const gap = leaderIncome - entry.income_rub_per_min;

          return (
            <button type="button" className="top-gap-row" key={entry.tg_id} onClick={() => onSelect(entry)} aria-label={`Открыть профиль ${entry.nickname}`}>
              <div className="top-gap-meta">
                <RankMark rank={entry.rank} />
                <Nickname as="span" name={entry.nickname} color={entry.nickname_color} className="top-gap-name" />
                <span className="top-gap-value">+{fmt(entry.income_rub_per_min)} ₽</span>
              </div>
              <div className="top-gap-track" aria-hidden="true">
                <span className={`top-gap-fill ${entry.rank === 1 ? 'top-gap-fill-leader' : ''}`} style={{ width: `${share}%` }} />
              </div>
              <span className="top-gap-diff">{gap === 0 ? 'лидер' : `−${fmt(gap)} ₽ до лидера`}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function PodiumCard({ entry, onSelect }: { entry: TopEntry; onSelect: (entry: TopEntry) => void }) {
  const winner = entry.rank === 1;

  return (
    <button
      type="button"
      className={`top-podium-card top-podium-rank-${entry.rank} ${winner ? 'top-podium-card-winner' : ''}`}
      onClick={() => onSelect(entry)}
      aria-label={`Открыть профиль ${entry.nickname}`}
    >
      <WallpaperLayer wallpaper={entry.profile_wallpaper} className="profile-wallpaper--podium" />
      <RankMark rank={entry.rank} podium />
      <ProfileBadge profileEmoji={entry.profile_emoji} fallbackTgId={entry.tg_id} size={winner ? 76 : 58} tone={rankTone(entry.rank)} frame={entry.profile_frame} />
      <div className="top-podium-copy">
        <PlayerName entry={entry} size={winner ? 'large' : 'normal'} />
        <span className="top-income-value">+{fmt(entry.income_rub_per_min)} ₽<small>/мин</small></span>
      </div>
      {entry.is_me && <span className="top-you-label">это ты</span>}
    </button>
  );
}

function PlayerRow({ entry, onSelect }: { entry: TopEntry; onSelect: (entry: TopEntry) => void }) {
  return (
    <button
      type="button"
      className={`top-player-row ${entry.is_me ? 'top-player-row-me' : ''}`}
      onClick={() => onSelect(entry)}
      aria-label={`Открыть профиль ${entry.nickname}`}
    >
      {entry.profile_wallpaper && entry.profile_wallpaper !== 'none' && (
        <div className={`profile-wallpaper profile-wallpaper--row ${wallpaperClass(entry.profile_wallpaper)}`} aria-hidden="true" />
      )}
      <RankMark rank={entry.rank} />
      <ProfileBadge profileEmoji={entry.profile_emoji} fallbackTgId={entry.tg_id} size={42} frame={entry.profile_frame} />
      <div className="top-player-main">
        <div className="flex items-center gap-2 min-w-0">
          <PlayerName entry={entry} />
          {entry.is_me && <span className="top-you-label">ты</span>}
        </div>
        {entry.tg_id === DEVELOPER_TG_ID && (
          <span className="top-player-caption">смотритель зоопарка</span>
        )}
      </div>
      <span className="top-player-income">+{fmt(entry.income_rub_per_min)} ₽<small>/мин</small></span>
    </button>
  );
}

function LeaderboardHero({ leader, onSelect }: {
  leader: TopEntry;
  onSelect: (entry: TopEntry) => void;
}) {
  return (
    <section className="top-hero">
      <div className="top-hero-orbit top-hero-orbit-one" />
      <div className="top-hero-orbit top-hero-orbit-two" />
      <div className="relative z-[1]">
        <button type="button" className="top-hero-leader" onClick={() => onSelect(leader)} aria-label={`Открыть профиль ${leader.nickname}`}>
          <WallpaperLayer wallpaper={leader.profile_wallpaper} className="profile-wallpaper--hero" />
          <ProfileBadge profileEmoji={leader.profile_emoji} fallbackTgId={leader.tg_id} size={52} tone="gold" frame={leader.profile_frame} />
          <div className="min-w-0 flex-1">
            <p className="top-label m-0">лидер прямо сейчас</p>
            <PlayerName entry={leader} size="large" />
          </div>
          <div className="text-right shrink-0">
            <p className="m-0 text-[15px] font-black tabular-nums" style={{ color: 'var(--c-green)' }}>
              +{fmt(leader.income_rub_per_min)} ₽<span className="text-[10px] font-bold text-tg-hint">/мин</span>
            </p>
          </div>
        </button>

      </div>
    </section>
  );
}

export function TopPage() {
  const topPageRef = useRef<HTMLDivElement>(null);
  const scrollTopBeforeProfile = useRef(0);
  const [selectedEntry, setSelectedEntry] = useState<TopEntry | null>(null);
  const { data, error, isLoading } = useQuery({
    queryKey: ['top'],
    queryFn: apiGetTop,
    staleTime: 30_000,
  });
  const { data: publicProfile, isLoading: isProfileLoading, error: profileError } = useQuery({
    queryKey: ['public-profile', selectedEntry?.tg_id],
    queryFn: () => apiGetPublicProfile(selectedEntry!.tg_id),
    enabled: selectedEntry !== null,
    staleTime: 30_000,
  });

  const entries = data?.entries.slice(0, 20) ?? [];
  const podium = entries.slice(0, 3);
  const rest = entries.slice(3);
  const leader = entries[0];
  const myEntry = entries.find(entry => entry.is_me);
  const restTitle = rest.length === 1
    ? `Место #${rest[0].rank}`
    : `Топ ${rest[0]?.rank}–${rest[rest.length - 1]?.rank}`;
  const openProfile = useCallback((entry: TopEntry) => {
    const scrollContainer = topPageRef.current?.parentElement?.parentElement;
    scrollTopBeforeProfile.current = scrollContainer?.scrollTop ?? 0;
    setSelectedEntry(entry);
  }, []);
  const closeProfile = useCallback(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    setSelectedEntry(null);
    requestAnimationFrame(() => {
      const scrollContainer = topPageRef.current?.parentElement?.parentElement;
      if (scrollContainer) scrollContainer.scrollTop = scrollTopBeforeProfile.current;
    });
  }, []);

  return (
    <div ref={topPageRef} className="top-page">
      {isLoading && <p className="text-center text-tg-hint py-8">Собираем рейтинг...</p>}
      {error && <p className="text-[var(--c-red-soft)]">⚠️ {error instanceof Error ? error.message : 'Ошибка'}</p>}

      {leader && data && (
        <LeaderboardHero
          leader={leader}
          onSelect={openProfile}
        />
      )}

      {entries.length > 0 && <IncomeGapChart entries={entries} onSelect={openProfile} />}

      {podium.length > 0 && (
        <section>
          <div className="top-section-heading">
            <h2 className="m-0 text-[18px] font-black tracking-[-0.03em]">Топ-3</h2>
          </div>
          <div className={`top-podium top-podium-count-${podium.length}`}>
            {podium.map(entry => <PodiumCard key={entry.tg_id} entry={entry} onSelect={openProfile} />)}
          </div>
        </section>
      )}

      {data?.my_rank && !myEntry && (
        <div className="top-my-rank-card">
          <ProfileBadge size={38} />
          <div className="min-w-0 flex-1">
            <p className="m-0 text-[13px] font-extrabold">Твоё место пока за пределами топ-20</p>
            <p className="m-0 mt-1 text-[11px] text-tg-hint">До следующей строчки — ещё немного дохода.</p>
          </div>
          <strong>#{data.my_rank}</strong>
        </div>
      )}

      {rest.length > 0 && (
        <section className="top-rest-section">
          <div className="top-section-heading">
            <h2 className="m-0 text-[18px] font-black tracking-[-0.03em]">{restTitle}</h2>
          </div>
          <div className="top-player-list">
            {rest.map(entry => <PlayerRow key={entry.tg_id} entry={entry} onSelect={openProfile} />)}
          </div>
        </section>
      )}

      {!isLoading && !error && data?.entries.length === 0 && (
        <div className="top-empty-state">
          <ProfileBadge size={64} tone="gold" />
          <p className="m-0 mt-3 text-[16px] font-black">Рейтинг пока пуст</p>
          <p className="m-0 mt-1 text-[12px] text-tg-hint">Собери первый зоопарк и займи вершину.</p>
        </div>
      )}

      {selectedEntry && (
        <PublicProfileSheet
          entry={selectedEntry}
          profile={publicProfile}
          isLoading={isProfileLoading}
          error={Boolean(profileError)}
          onClose={closeProfile}
        />
      )}
    </div>
  );
}
