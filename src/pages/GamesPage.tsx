import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fmt } from '@/utils/format';
import type { Duel, GameState } from '@/types';
import { GAMES } from '@/data/games';
import {
  apiConfig,
  apiCreateDuel,
  apiGetOpenDuels,
  apiGetSoloStats,
  apiJoinDuel,
} from '@/api';
import { CocktailTab } from '@/features/games/CocktailTab';
import { SoloGameFlow } from '@/features/games/SoloGameFlow';
import { PageHeader } from '@/components/PageHeader';
import { copyTmaText, shareTmaUrl } from '@/lib/tma';

type GamesTab = 'solo' | 'multi' | 'cocktail';
type BetAmount = 1 | 10 | 100;
type MultiScreen = 'list' | 'share';

const BET_AMOUNTS: BetAmount[] = [1, 10, 100];

const GAME_COLORS: Record<string, { from: string; to: string; glow: string }> = {
  basketball: { from: 'var(--c-orange)', to: 'var(--c-red)', glow: 'rgba(var(--c-orange-rgb),0.35)' },
  darts:    { from: 'var(--c-purple)', to: 'var(--c-blue)', glow: 'rgba(var(--c-purple-rgb),0.35)' },
  bowling:  { from: 'var(--c-green)', to: 'var(--c-teal)', glow: 'rgba(var(--c-green-rgb),0.35)' },
  dice:     { from: 'var(--c-blue)', to: 'var(--c-cyan)', glow: 'rgba(var(--c-blue-rgb),0.35)' },
  football: { from: 'var(--c-gold)', to: 'var(--c-amber)', glow: 'rgba(var(--c-gold-rgb),0.35)' },
};

function getGameDef(gameType: string) {
  return GAMES.find((game) => game.id === gameType);
}

function parseRubInput(value: string): number {
  return Number(value.replace(/\D/g, '') || 0);
}

/* ──────────────────────────── MULTI ────────────────────────────────── */
function MultiTab({ gs, onRefresh, inviteGameId }: { gs: GameState; onRefresh: () => void; inviteGameId?: number }) {
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selectedGame, setSelectedGame] = useState<string>('dice');
  const [betInput, setBetInput] = useState('1');
  const [message, setMessage] = useState<string | null>(null);
  const [screen, setScreen] = useState<MultiScreen>('list');
  const [createdGame, setCreatedGame] = useState<Duel | null>(null);
  const [copiedInvite, setCopiedInvite] = useState(false);
  const { data: openGames, error: openGamesError, isLoading, refetch: refetchGames } = useQuery({
    queryKey: ['mp-games', 'open'],
    queryFn: apiGetOpenDuels,
    staleTime: 10_000,
  });
  const { data: config } = useQuery({
    queryKey: ['config'],
    queryFn: apiConfig,
    staleTime: 300_000,
  });

  const games = openGames?.games ?? [];
  const botUsername = config?.bot_username ?? 'ZooParkBot';
  const error = actionError ?? (openGamesError instanceof Error ? openGamesError.message : null);
  const bet = parseRubInput(betInput);
  const betTooHigh = bet > gs.rub;
  const canCreate = bet > 0 && !betTooHigh;
  const createdGameDef = createdGame ? getGameDef(createdGame.kind) : null;
  const createdGameLink = createdGame ? `https://t.me/${botUsername}?startapp=mpgame_${createdGame.id}` : '';
  const invitedGameAvailable = inviteGameId ? games.some((game) => game.id === inviteGameId) : false;
  const visibleGames = inviteGameId
    ? [...games].sort((a, b) => Number(b.id === inviteGameId) - Number(a.id === inviteGameId))
    : games;

  const setPresetBet = (amount: BetAmount) => {
    setBetInput(String(amount));
  };

  const updateBetInput = (value: string) => {
    setBetInput(value.replace(/\D/g, '').slice(0, 15));
  };

  const createGame = async () => {
    if (busy || !canCreate) return;
    setBusy(true);
    setMessage(null);
    setActionError(null);
    setCreatedGame(null);
    setCopiedInvite(false);
    try {
      const result = await apiCreateDuel(selectedGame, bet);
      setCreatedGame(result.game);
      setScreen('share');
      setMessage('Игра создана. Ждём второго игрока.');
      onRefresh();
      void refetchGames();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Ошибка создания игры');
    } finally {
      setBusy(false);
    }
  };

  const backToList = () => {
    setScreen('list');
    setCopiedInvite(false);
  };

  const copyInviteLink = async () => {
    if (!createdGameLink) return;
    if (await copyTmaText(createdGameLink)) {
      setCopiedInvite(true);
      setTimeout(() => setCopiedInvite(false), 2000);
    }
  };

  const shareInviteLink = () => {
    if (!createdGame || !createdGameLink) return;
    const title = createdGameDef?.name ?? createdGame.kind;
    void shareTmaUrl(createdGameLink, `Заходи сыграть в ${title} в ZooPark. Ставка: ₽${fmt(createdGame.stake_rub)}`);
  };

  const joinGame = async (gameId: number) => {
    if (busy) return;
    setBusy(true);
    setMessage(null);
    setActionError(null);
    try {
      await apiJoinDuel(gameId);
      setMessage('Ты присоединился к игре.');
      onRefresh();
      void refetchGames();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Ошибка входа в игру');
    } finally {
      setBusy(false);
    }
  };

  if (screen === 'share' && createdGame) {
    return (
      <div className="p-[14px] flex flex-col gap-3">
        <div className="flex items-center gap-3 mb-1">
          <button
            type="button"
            onClick={backToList}
            className="w-10 h-10 rounded-xl border-none text-[18px] shrink-0"
            style={{ background: 'var(--tg-theme-secondary-bg-color)', color: 'var(--tg-theme-text-color)' }}
          >
            ←
          </button>
          <div className="min-w-0">
            <p className="m-0 text-[18px] font-extrabold">Поделиться игрой</p>
            <p className="m-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>Отправь приглашение в чат или скопируй ссылку</p>
          </div>
        </div>

        <div className="card flex flex-col items-center text-center gap-3" style={{ background: 'rgba(var(--c-blue-rgb),0.08)', borderColor: 'rgba(var(--c-blue-rgb),0.24)' }}>
          <div className="w-[88px] h-[88px] rounded-3xl grid place-items-center text-[44px]" style={{ background: 'rgba(var(--c-blue-rgb),0.15)', border: '1px solid rgba(var(--c-blue-rgb),0.25)' }}>
            {createdGameDef?.emoji ?? '🎲'}
          </div>
          <div>
            <p className="m-0 font-extrabold text-[18px]">Игра создана</p>
            <p className="m-0 mt-1 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
              {createdGameDef?.name ?? createdGame.kind} · ставка ₽{fmt(createdGame.stake_rub)}
            </p>
          </div>
          <div className="surface-subtle w-full px-3 py-[10px] rounded-xl text-[12px] break-all select-all text-left" style={{ color: 'var(--tg-theme-hint-color)' }}>
            {createdGameLink}
          </div>
        </div>

        <button
          onClick={shareInviteLink}
          className="py-[15px] rounded-2xl border-none font-extrabold text-[16px]"
          style={{ background: 'var(--c-blue)', color: 'var(--tg-theme-button-text-color)', boxShadow: '0 4px 16px rgba(var(--c-blue-rgb),0.3)' }}
        >
          Поделиться в Telegram
        </button>

        <button
          onClick={() => void copyInviteLink()}
          className="py-[14px] rounded-2xl border-none font-bold text-[15px]"
          style={{ background: copiedInvite ? 'rgba(var(--c-green-rgb),0.2)' : 'rgba(var(--c-blue-rgb),0.18)', color: copiedInvite ? 'var(--c-green)' : 'var(--c-blue)' }}
        >
          {copiedInvite ? 'Ссылка скопирована' : 'Копировать ссылку'}
        </button>

        <button
          onClick={backToList}
          className="py-[12px] rounded-2xl border-none font-bold text-[14px]"
          style={{ background: 'var(--surface-subtle)', color: 'var(--tg-theme-hint-color)' }}
        >
          К списку игр
        </button>
      </div>
    );
  }

  return (
    <div className="p-[14px] flex flex-col gap-3">
      <div className="card flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <p className="m-0 font-bold text-[15px]">Создать игру</p>
          <span className="text-[12px] text-tg-hint">Баланс: ₽{fmt(gs.rub)}</span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {GAMES.map((game) => {
            const active = game.id === selectedGame;
            return (
              <button
                key={game.id}
                onClick={() => setSelectedGame(game.id)}
                className="px-3 py-2 rounded-xl border-none text-left"
                style={{
                  background: active ? 'rgba(var(--c-blue-rgb),0.15)' : 'var(--surface-subtle)',
                  color: active ? 'var(--tg-theme-text-color)' : 'var(--tg-theme-hint-color)',
                  border: `1px solid ${active ? 'rgba(var(--c-blue-rgb),0.35)' : 'var(--surface-overlay-border)'}`,
                }}
              >
                <span className="block font-semibold text-[13px]">{game.emoji} {game.name}</span>
              </button>
            );
          })}
        </div>

        <div className="flex gap-2">
          {BET_AMOUNTS.map((amount) => {
            const active = amount === bet;
            return (
              <button
                key={amount}
                onClick={() => setPresetBet(amount)}
                className="flex-1 py-2 rounded-xl border-none font-bold text-[13px]"
                style={{
                  background: active ? 'rgba(var(--c-green-rgb),0.15)' : 'var(--surface-subtle)',
                  color: active ? 'var(--c-green)' : 'var(--tg-theme-hint-color)',
                  border: `1px solid ${active ? 'rgba(var(--c-green-rgb),0.3)' : 'var(--surface-overlay-border)'}`,
                }}
              >
                ₽{fmt(amount)}
              </button>
            );
          })}
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-[12px] font-semibold" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Произвольная ставка
          </label>
          <input
            value={betInput}
            onChange={(event) => updateBetInput(event.target.value)}
            inputMode="numeric"
            placeholder="Введите сумму в рублях"
            className="text-input text-[15px]"
            style={{ padding: '12px 14px' }}
          />
          {betInput && bet === 0 && (
            <p className="m-0 text-[12px]" style={{ color: 'var(--c-red-soft)' }}>Ставка должна быть больше нуля</p>
          )}
          {betTooHigh && (
            <p className="m-0 text-[12px]" style={{ color: 'var(--c-red-soft)' }}>Недостаточно рублей для ставки ₽{fmt(bet)}</p>
          )}
        </div>

        <button
          onClick={() => void createGame()}
          disabled={busy || !canCreate}
          className="py-[15px] rounded-2xl border-none font-extrabold text-base disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, var(--c-green), #30b34e)', color: 'var(--tg-theme-button-text-color)', boxShadow: '0 4px 16px rgba(var(--c-green-rgb),0.3)' }}
        >
          {busy ? 'Создаём...' : '+ Создать игру'}
        </button>
      </div>

      {message && <div className="card" style={{ background: 'rgba(var(--c-green-rgb),0.1)', borderColor: 'rgba(var(--c-green-rgb),0.25)' }}><p className="m-0 text-[13px]" style={{ color: 'var(--c-green)' }}>{message}</p></div>}

      {inviteGameId && !isLoading && !invitedGameAvailable && (
        <div className="card" style={{ background: 'rgba(var(--c-orange-rgb),0.1)', borderColor: 'rgba(var(--c-orange-rgb),0.25)' }}>
          <p className="m-0 text-[13px] font-semibold" style={{ color: 'var(--c-orange)' }}>
            Игра по ссылке уже недоступна или была сыграна.
          </p>
        </div>
      )}

      {isLoading && (
        <div className="flex justify-center py-6">
          <div className="spinner" />
        </div>
      )}
      {error && (
        <p className="text-center text-sm" style={{ color: 'var(--c-red-soft)' }}>{error}</p>
      )}

      {!isLoading && !error && games.length === 0 && (
        <div className="text-center py-10">
          <div className="text-[48px] mb-3">🏆</div>
          <p className="m-0 font-bold">Нет открытых игр</p>
          <p className="mt-1 mb-0 text-[13px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
            Создай первую и пригласи друга!
          </p>
        </div>
      )}

      {visibleGames.map(g => {
        const gameDef = getGameDef(g.kind);
        const invited = inviteGameId === g.id;
        return (
        <div
          key={g.id}
          className="card flex items-center gap-3"
          style={invited ? { borderColor: 'rgba(var(--c-blue-rgb),0.45)', boxShadow: '0 0 18px rgba(var(--c-blue-rgb),0.18)' } : undefined}
        >
          <div
            className="w-10 h-10 rounded-xl grid place-items-center text-xl shrink-0"
            style={{ background: 'rgba(var(--c-blue-rgb),0.15)', border: '1px solid rgba(var(--c-blue-rgb),0.25)' }}
          >
            {gameDef?.emoji ?? '🎲'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 min-w-0">
              <p className="m-0 font-bold text-sm truncate">{gameDef ? `${gameDef.emoji} ${gameDef.name}` : g.kind}</p>
              {invited && (
                <span className="text-[10px] font-bold px-2 py-[2px] rounded-full shrink-0" style={{ background: 'rgba(var(--c-blue-rgb),0.16)', color: 'var(--c-blue)' }}>
                  По ссылке
                </span>
              )}
            </div>
            <p className="mt-[2px] mb-0 text-xs" style={{ color: 'var(--tg-theme-hint-color)' }}>
              {g.creator_nickname} · ставка ₽{fmt(g.stake_rub)}
            </p>
          </div>
          <button
            onClick={() => void joinGame(g.id)}
            disabled={busy}
            className="px-4 py-2 rounded-xl border-none font-bold text-[13px] shrink-0"
            style={{ background: 'linear-gradient(135deg, var(--c-blue), #0066dd)', color: 'var(--tg-theme-button-text-color)', boxShadow: '0 2px 8px rgba(var(--c-blue-rgb),0.3)' }}
          >
            Войти
          </button>
        </div>
      )})}
    </div>
  );
}

/* ──────────────────────────── SOLO ─────────────────────────────────── */
function SoloTab({ gs, onRefresh }: { gs: GameState; onRefresh: () => void }) {
  const [showStats, setShowStats] = useState(false);
  const [activeGameId, setActiveGameId] = useState<string | null>(null);
  const { data: stats } = useQuery({
    queryKey: ['solo-stats'],
    queryFn: apiGetSoloStats,
    enabled: showStats,
    staleTime: 30_000,
  });

  if (activeGameId) {
    const activeGame = getGameDef(activeGameId);
    if (!activeGame) {
      return null;
    }

    return (
      <SoloGameFlow
        game={activeGame}
        availableRub={gs.rub}
        onBack={() => setActiveGameId(null)}
        onRefresh={onRefresh}
      />
    );
  }

  const winRate = stats && stats.games_played > 0
    ? Math.round((stats.wins / stats.games_played) * 100)
    : 0;

  return (
    <div className="p-[14px] flex flex-col gap-[10px]">

      {/* Stats toggle */}
      <button
        onClick={() => setShowStats(s => !s)}
        className="flex items-center gap-3 px-[14px] py-[12px] rounded-2xl border-none text-left w-full"
        style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 15%, transparent)' }}
      >
        <span className="text-lg">📊</span>
        <span className="flex-1 font-semibold text-sm">Моя статистика</span>
        <span className="text-xs" style={{ color: 'var(--tg-theme-hint-color)' }}>{showStats ? '▲' : '▼'}</span>
      </button>

      {showStats && stats && (
        <div className="card flex flex-col gap-3">
          <div className="grid grid-cols-3 gap-2">
            <div className="text-center rounded-xl py-3" style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 7%, transparent)' }}>
              <p className="m-0 text-[20px] font-extrabold">{stats.games_played}</p>
              <p className="m-0 text-[11px] mt-1" style={{ color: 'var(--tg-theme-hint-color)' }}>Игр</p>
            </div>
            <div className="text-center rounded-xl py-3" style={{ background: 'rgba(var(--c-green-rgb),0.08)' }}>
              <p className="m-0 text-[20px] font-extrabold" style={{ color: 'var(--c-green)' }}>{stats.wins}</p>
              <p className="m-0 text-[11px] mt-1" style={{ color: 'var(--tg-theme-hint-color)' }}>Победы</p>
            </div>
            <div className="text-center rounded-xl py-3" style={{ background: 'rgba(var(--c-orange-rgb),0.08)' }}>
              <p className="m-0 text-[20px] font-extrabold" style={{ color: 'var(--c-orange)' }}>{stats.losses}</p>
              <p className="m-0 text-[11px] mt-1" style={{ color: 'var(--tg-theme-hint-color)' }}>Поражения</p>
            </div>
          </div>

          {stats.games_played > 0 && (
            <div>
              <div className="flex justify-between text-[12px] mb-1">
                <span style={{ color: 'var(--tg-theme-hint-color)' }}>Процент побед</span>
                <span className="font-bold" style={{ color: winRate >= 50 ? 'var(--c-green)' : 'var(--c-orange)' }}>
                  {winRate}%
                </span>
              </div>
              <div className="h-[6px] rounded-full" style={{ background: 'color-mix(in srgb, var(--tg-theme-hint-color) 15%, transparent)' }}>
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${winRate}%`,
                    background: winRate >= 50
                      ? 'linear-gradient(90deg, var(--c-green), var(--c-teal))'
                      : 'linear-gradient(90deg, var(--c-amber), var(--c-red))',
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Game list */}
      {GAMES.map(g => {
        const colors = GAME_COLORS[g.id] ?? GAME_COLORS.dice;
        return (
          <div
            key={g.id}
            onClick={() => setActiveGameId(g.id)}
            className="rounded-2xl p-[14px] flex items-center gap-[14px] cursor-pointer"
            style={{
              background: `linear-gradient(135deg, color-mix(in srgb, ${colors.from} 10%, transparent), color-mix(in srgb, ${colors.to} 6%, transparent))`,
              border: `1.5px solid color-mix(in srgb, ${colors.from} 22%, transparent)`,
              transition: 'border 200ms',
            }}
          >
            <div
              className="w-[48px] h-[48px] rounded-xl grid place-items-center text-[24px] shrink-0"
              style={{
                background: `linear-gradient(135deg, color-mix(in srgb, ${colors.from} 15%, transparent), color-mix(in srgb, ${colors.to} 8%, transparent))`,
                border: `1px solid color-mix(in srgb, ${colors.from} 19%, transparent)`,
              }}
            >
              {g.emoji}
            </div>
            <div className="flex-1 min-w-0">
              <p className="m-0 font-bold text-[15px]">{g.name}</p>
              <p className="mt-[3px] mb-0 text-[12px]" style={{ color: 'var(--tg-theme-hint-color)' }}>
                {g.description}
              </p>
              <p className="mt-[1px] mb-0 text-[11px]" style={{ color: colors.from, opacity: 0.8 }}>
                {g.detail}
              </p>
            </div>
            <div
              className="w-6 h-6 rounded-full grid place-items-center shrink-0 text-[14px]"
              style={{ background: `linear-gradient(135deg, ${colors.from}, ${colors.to})`, color: 'var(--tg-theme-button-text-color)' }}
            >
              →
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ──────────────────────────── MAIN PAGE ────────────────────────────── */
export function GamesPage({ gs, onRefresh, initialTab = 'solo', inviteGameId }: { gs: GameState; onRefresh: () => void; initialTab?: GamesTab; inviteGameId?: number }) {
  const [tab, setTab] = useState<GamesTab>(initialTab);

  const tabs: { id: GamesTab; emoji: string; label: string }[] = [
    { id: 'solo',     emoji: '🤖', label: 'Соло' },
    { id: 'multi',    emoji: '🏆', label: 'Мульти' },
    { id: 'cocktail', emoji: '🥤', label: 'Коктейль' },
  ];

  return (
    <div className="page-content-safe">

      <PageHeader
        emoji="🎮"
        title="Игры"
        subtitle="Играй против ИИ или соревнуйся с друзьями!"
        accent="var(--c-blue-rgb)"
      />

      {/* Tabs */}
      <div
        className="flex mx-[14px] rounded-2xl p-1 mb-1"
        style={{ background: 'var(--tg-theme-secondary-bg-color)', border: '1px solid color-mix(in srgb, var(--tg-theme-hint-color) 18%, transparent)' }}
      >
        {tabs.map(t => {
          const isActive = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className="flex-1 flex items-center justify-center gap-[6px] py-[9px] rounded-xl border-none transition-all duration-200"
              style={{
                background: isActive ? 'color-mix(in srgb, var(--tg-theme-button-color) 15%, transparent)' : 'transparent',
                color: isActive ? 'var(--tg-theme-text-color)' : 'var(--tg-theme-hint-color)',
                boxShadow: isActive ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
              }}
            >
              <span className="text-[15px]">{t.emoji}</span>
              <span className="text-[12px] font-bold">{t.label}</span>
            </button>
          );
        })}
      </div>

      <div>
        {tab === 'solo'     && <SoloTab gs={gs} onRefresh={onRefresh} />}
        {tab === 'multi'    && <MultiTab gs={gs} onRefresh={onRefresh} inviteGameId={inviteGameId} />}
        {tab === 'cocktail' && <CocktailTab onRefresh={onRefresh} />}
      </div>
    </div>
  );
}
