import { useQuery } from '@tanstack/react-query';
import type { TopEntry } from '@/types';
import { apiGetTop } from '@/api';
import { fmt } from '@/utils/format';
import { ProfileBadge, type ProfileBadgeTone } from '@/components/ProfileBadge';
import { nicknameColorClass, nicknameColorValue } from '@/data/nicknameColors';

function rankTone(rank: number): ProfileBadgeTone {
  if (rank === 1) return 'gold';
  if (rank === 2) return 'silver';
  if (rank === 3) return 'bronze';
  return 'default';
}

function RankMark({ rank, podium = false }: { rank: number; podium?: boolean }) {
  const medal = rank === 1 ? '♛' : rank === 2 ? '◆' : rank === 3 ? '✦' : null;

  return (
    <span className={`top-rank-mark ${podium ? 'top-rank-mark-podium' : ''} top-rank-mark-${rankTone(rank)}`}>
      {medal ? <span aria-hidden="true">{medal}</span> : `#${rank}`}
    </span>
  );
}

function PlayerName({ entry, size = 'normal' }: { entry: TopEntry; size?: 'normal' | 'large' }) {
  return (
    <p
      className={`m-0 truncate ${size === 'large' ? 'text-[17px]' : 'text-[14px]'} ${nicknameColorClass(entry.nickname_color)}`}
      style={{
        color: nicknameColorValue(entry.nickname_color),
        fontWeight: entry.is_me ? 900 : 800,
      }}
    >
      {entry.nickname}
    </p>
  );
}

function PodiumCard({ entry }: { entry: TopEntry }) {
  const winner = entry.rank === 1;

  return (
    <div className={`top-podium-card top-podium-rank-${entry.rank} ${winner ? 'top-podium-card-winner' : ''}`}>
      <RankMark rank={entry.rank} podium />
      <ProfileBadge profileEmoji={entry.profile_emoji} size={winner ? 76 : 58} tone={rankTone(entry.rank)} />
      <div className="top-podium-copy">
        <PlayerName entry={entry} size={winner ? 'large' : 'normal'} />
        <span className="top-income-value">+{fmt(entry.income_rub_per_min)} ₽<small>/мин</small></span>
      </div>
      {entry.is_me && <span className="top-you-label">это ты</span>}
    </div>
  );
}

function PlayerRow({ entry }: { entry: TopEntry }) {
  return (
    <div className={`top-player-row ${entry.is_me ? 'top-player-row-me' : ''}`}>
      <RankMark rank={entry.rank} />
      <ProfileBadge profileEmoji={entry.profile_emoji} size={42} />
      <div className="top-player-main">
        <div className="flex items-center gap-2 min-w-0">
          <PlayerName entry={entry} />
          {entry.is_me && <span className="top-you-label">ты</span>}
        </div>
        <span className="top-player-caption">смотритель зоопарка</span>
      </div>
      <span className="top-player-income">+{fmt(entry.income_rub_per_min)} ₽<small>/мин</small></span>
    </div>
  );
}

function LeaderboardHero({ leader, myRank, myEntry, shownCount }: {
  leader: TopEntry;
  myRank: number | null;
  myEntry: TopEntry | undefined;
  shownCount: number;
}) {
  return (
    <section className="top-hero">
      <div className="top-hero-orbit top-hero-orbit-one" />
      <div className="top-hero-orbit top-hero-orbit-two" />
      <div className="relative z-[1]">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="top-eyebrow">ЛИГА СМОТРИТЕЛЕЙ</p>
            <h1 className="m-0 mt-1 text-[23px] leading-[1.05] font-black tracking-[-0.04em]">Топ зоопарков</h1>
            <p className="m-0 mt-2 text-[12px] leading-snug text-tg-hint max-w-[210px]">
              Место определяется доходом зоопарка за минуту.
            </p>
          </div>
          <div className="top-hero-crown" aria-hidden="true">♛</div>
        </div>

        <div className="top-hero-leader">
          <ProfileBadge profileEmoji={leader.profile_emoji} size={52} tone="gold" />
          <div className="min-w-0 flex-1">
            <p className="top-label m-0">лидер прямо сейчас</p>
            <PlayerName entry={leader} size="large" />
          </div>
          <div className="text-right shrink-0">
            <p className="top-label m-0">доход</p>
            <p className="m-0 mt-1 text-[15px] font-black tabular-nums" style={{ color: 'var(--c-green)' }}>
              +{fmt(leader.income_rub_per_min)} ₽<span className="text-[10px] font-bold text-tg-hint">/мин</span>
            </p>
          </div>
        </div>

        <div className="top-hero-stats">
          <div>
            <span className="top-label">в рейтинге</span>
            <strong>{shownCount}</strong>
            <small>игроков показано</small>
          </div>
          <div>
            <span className="top-label">твоё место</span>
            <strong>{myRank ? `#${myRank}` : '—'}</strong>
            <small>{myEntry ? 'ты в двадцатке' : 'развивай зоопарк'}</small>
          </div>
        </div>
      </div>
    </section>
  );
}

export function TopPage() {
  const { data, error, isLoading } = useQuery({
    queryKey: ['top'],
    queryFn: apiGetTop,
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

  return (
    <div className="top-page">
      {isLoading && <p className="text-center text-tg-hint py-8">Собираем рейтинг...</p>}
      {error && <p className="text-[var(--c-red-soft)]">⚠️ {error instanceof Error ? error.message : 'Ошибка'}</p>}

      {leader && data && (
        <LeaderboardHero leader={leader} myRank={data.my_rank} myEntry={myEntry} shownCount={entries.length} />
      )}

      {podium.length > 0 && (
        <section>
          <div className="top-section-heading">
            <div>
              <p className="top-eyebrow m-0">ПЕРВЫЕ МЕСТА</p>
              <h2 className="m-0 mt-1 text-[18px] font-black tracking-[-0.03em]">Пьедестал сезона</h2>
            </div>
            <span className="top-section-note">доход / мин</span>
          </div>
          <div className={`top-podium top-podium-count-${podium.length}`}>
            {podium.map(entry => <PodiumCard key={entry.tg_id} entry={entry} />)}
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
            <div>
              <p className="top-eyebrow m-0">ОСТАЛЬНЫЕ УЧАСТНИКИ</p>
              <h2 className="m-0 mt-1 text-[18px] font-black tracking-[-0.03em]">{restTitle}</h2>
            </div>
          </div>
          <div className="top-player-list">
            {rest.map(entry => <PlayerRow key={entry.tg_id} entry={entry} />)}
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
    </div>
  );
}
