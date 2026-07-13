import { useEffect, useState } from 'react';
import { Nickname } from '@/components/NicknameEffects';
import { ProfileBadge } from '@/components/ProfileBadge';
import type { MaintenancePollStatus } from '@/types';

const MAX_VISIBLE_PLAYERS = 15;

export function OnlinePlayersIndicator({ data, devBarVisible = false }: { data: MaintenancePollStatus; devBarVisible?: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const players = data.online_players.slice(0, MAX_VISIBLE_PLAYERS);

  useEffect(() => {
    if (data.online_count === 0) setExpanded(false);
  }, [data.online_count]);

  return (
    <div className={`online-presence${devBarVisible ? ' online-presence-dev' : ''}`}>
      {expanded && (
        <div className="online-presence-panel" role="dialog" aria-label="Игроки онлайн">
          <div className="online-presence-heading">
            <span>Сейчас в игре</span>
            <strong>{data.online_count}</strong>
          </div>
          <div className="online-presence-list">
            {players.length > 0 ? players.map(player => (
              <div key={player.id} className={`online-presence-player${player.is_me ? ' online-presence-player-me' : ''}`}>
                <ProfileBadge profileEmoji={player.profile_emoji} frame={player.profile_frame} size={30} />
                <Nickname name={player.nickname} color={player.nickname_color} className="online-presence-name" />
                {player.is_me && <span className="online-presence-you">ты</span>}
              </div>
            )) : (
              <p className="online-presence-empty">Пока никого нет</p>
            )}
          </div>
          {data.online_count > players.length && (
            <p className="online-presence-footnote">Показаны первые {MAX_VISIBLE_PLAYERS}</p>
          )}
        </div>
      )}

      <button
        type="button"
        className={`online-presence-toggle${data.online_count > 0 ? ' online-presence-toggle-active' : ''}`}
        onClick={() => setExpanded(value => !value)}
        aria-expanded={expanded}
        aria-label={`${data.online_count} игроков онлайн`}
      >
        <span className="online-presence-beacon" aria-hidden="true" />
        <span className="online-presence-count">{data.online_count}</span>
      </button>
    </div>
  );
}
