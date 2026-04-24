import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { useZooStore } from './store';
import { TabBar, type RootTab } from './components/TabBar';
import { PageSkeleton, Skeleton } from './components/Skeleton';
import { apiRegister, isDevMode, setDevUserId, clearDevUserId, apiBuyAviary } from './api';
import { useLiveGameState } from './hooks/useLiveGameState';
import { inTma, hapticImpact, hapticNotification, readyTma } from './tma';
import { getTelegramStartParam } from './tmaEnv';
import type { GameState } from './types';

const AUTOSAVE_MS = 15_000;
const HIDDEN_RELOAD_MS = 30_000;

function getInviteGameId(): number | null {
  const startParam = getTelegramStartParam();
  const match = startParam?.match(/^mpgame_(\d+)$/);
  return match ? Number(match[1]) : null;
}

// ─── Lazy page imports ────────────────────────────────────────────────────────

const ZooPage   = lazy(() => import('./pages/ZooPage').then(m => ({ default: m.ZooPage })));
const ShopPage  = lazy(() => import('./pages/ShopPage').then(m => ({ default: m.ShopPage })));
const LabPage   = lazy(() => import('./pages/LabPage').then(m => ({ default: m.LabPage })));
const GamesPage = lazy(() => import('./pages/GamesPage').then(m => ({ default: m.GamesPage })));
const MorePage  = lazy(() => import('./pages/MorePage').then(m => ({ default: m.MorePage })));

// ─── Register screen ──────────────────────────────────────────────────────────

function RegisterScreen({ onDone }: { onDone: (gs: GameState) => void }) {
  const [nickname, setNickname] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async () => {
    const n = nickname.trim();
    if (n.length < 3) { setError('Никнейм слишком короткий (мин. 3 символа)'); return; }
    setLoading(true);
    setError(null);
    try {
      const res = await apiRegister(n);
      if (res.ok) onDone(res.game_state);
      else setError('Ошибка регистрации');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-dvh flex items-center px-6 max-w-[480px] mx-auto">
      <div className="w-full bg-tg-secondary rounded-[20px] p-6 border" style={{ borderColor: 'var(--surface-overlay-border)' }}>
        <div className="text-center mb-6">
          <div className="text-[56px] mb-2">🦁</div>
          <p className="m-0 text-[22px] font-extrabold">ZooPark</p>
          <p className="mt-[6px] mb-0 text-sm text-tg-hint">
            Строй свой зоопарк и зарабатывай!
          </p>
        </div>

        <div className="flex flex-col gap-3">
          <input
            value={nickname}
            onChange={e => setNickname(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && void handleRegister()}
            placeholder="Твой никнейм"
            maxLength={64}
            className="text-input text-base"
            style={{ fontSize: 16, padding: '12px 14px' }}
          />
          {error && (
            <p className="m-0 text-[var(--c-red-soft)] text-[13px]">⚠️ {error}</p>
          )}
          <button
            onClick={() => void handleRegister()}
            disabled={loading || nickname.trim().length < 3}
            className="py-[14px] rounded-xl border-none bg-tg-button text-[var(--tg-theme-button-text-color)] font-extrabold text-base disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {loading ? 'Создаём профиль...' : 'Начать игру 🚀'}
          </button>
        </div>

        <div className="surface-subtle mt-5 p-[14px] rounded-xl">
          <p className="m-0 mb-[6px] text-[13px] font-semibold">Как играть:</p>
          {[
            '🏗️ Купи вольер → размести животных',
            '🐾 Зарабатывай рубли каждую минуту',
            '💱 Обменивай рубли на доллары в банке',
            '🎮 Участвуй в играх и турнирах',
          ].map(t => (
            <p key={t} className="m-0 mb-1 text-xs text-tg-hint">{t}</p>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Dev bar ──────────────────────────────────────────────────────────────────

function DevBar({ onLogin }: { onLogin: (id: string) => void }) {
  const [val, setVal] = useState('');
  return (
    <div className="surface-overlay fixed top-0 left-1/2 -translate-x-1/2 w-full max-w-[480px] z-[200] px-3 py-2 flex gap-2 items-center backdrop-blur-xl">
      <input
        value={val}
        onChange={e => setVal(e.target.value)}
        placeholder="Dev user ID"
        onKeyDown={e => e.key === 'Enter' && val.trim() && onLogin(val.trim())}
        className="text-input flex-1 min-h-0 py-[7px] text-[13px]"
      />
      <button
        onClick={() => val.trim() && onLogin(val.trim())}
        className="px-[14px] py-[7px] rounded-lg bg-[var(--c-blue)] text-[var(--tg-theme-button-text-color)] text-[13px] border-none cursor-pointer"
      >
        Войти
      </button>
      {isDevMode() && (
        <button
          onClick={() => { clearDevUserId(); window.location.reload(); }}
          className="px-[10px] py-[7px] rounded-lg border bg-transparent text-tg-hint text-[13px] cursor-pointer"
          style={{ borderColor: 'var(--surface-overlay-border)' }}
        >
          ✕
        </button>
      )}
    </div>
  );
}

// ─── Toast ────────────────────────────────────────────────────────────────────

function Toast({ msg }: { msg: { kind: 'ok' | 'err'; text: string } | null }) {
  if (!msg) return null;
  return (
    <div
      className={[
        'fixed bottom-20 left-1/2 -translate-x-1/2 z-[500] pointer-events-none',
        'rounded-[14px] px-[18px] py-3 text-sm font-semibold text-[var(--tg-theme-button-text-color)]',
        'shadow-[0_4px_24px_rgba(0,0,0,0.4)] border',
        'max-w-[440px] text-center',
        'animate-slide-up',
        msg.kind === 'ok' ? 'bg-[rgba(46,117,76,0.95)]' : 'bg-[rgba(139,41,62,0.95)]',
      ].join(' ')}
      style={{ borderColor: 'var(--surface-overlay-border)' }}
    >
      {msg.text}
    </div>
  );
}

// ─── Coming Soon ──────────────────────────────────────────────────────────────

function ComingSoonScreen() {
  return (
    <div className="min-h-dvh flex items-center justify-center px-6 max-w-[480px] mx-auto">
      <div className="w-full text-center bg-tg-secondary rounded-[20px] py-8 px-6 border" style={{ borderColor: 'var(--surface-overlay-border)' }}>
        <div className="text-[64px] mb-4">🚧</div>
        <p className="m-0 mb-2 text-[22px] font-extrabold">Игра в разработке</p>
        <p className="m-0 text-sm text-tg-hint leading-relaxed">
          Скоро откроемся для всех!<br />Следи за обновлениями.
        </p>
      </div>
    </div>
  );
}

// ─── Page suspense fallback ───────────────────────────────────────────────────

function PageFallback() {
  return (
    <div className="pb-20">
      <PageSkeleton />
    </div>
  );
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const { state, loading, error, errorStatus, loadFromServer, persistStateSilently, setGameState, patchState } = useZooStore();
  const displayState = useLiveGameState(state);
  const [tab, setTab] = useState<RootTab>('zoo');
  const [inviteGameId] = useState<number | null>(() => getInviteGameId());
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);
  const displayStateRef = useRef<GameState | null>(null);
  const toastRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hiddenAtRef = useRef<number | null>(null);
  const autosaveRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const showToast = useCallback((kind: 'ok' | 'err', text: string) => {
    setToast({ kind, text });
    if (toastRef.current) clearTimeout(toastRef.current);
    toastRef.current = setTimeout(() => setToast(null), 3500);
  }, []);

  useEffect(() => {
    displayStateRef.current = displayState;
  }, [displayState]);

  const persistDisplayedStateSilently = useCallback((keepalive = false) => {
    void persistStateSilently({ keepalive, snapshot: displayStateRef.current ?? undefined });
  }, [persistStateSilently]);

  const reloadFromServer = useCallback(() => {
    void loadFromServer();
  }, [loadFromServer]);

  // Initial load
  useEffect(() => { void loadFromServer(); }, [loadFromServer]);

  useEffect(() => {
    if (inviteGameId) setTab('games');
  }, [inviteGameId]);

  // Tell Telegram to hide the launch placeholder once the root tree is mounted.
  useEffect(() => {
    readyTma();
  }, []);

  // Autosave every 15s
  useEffect(() => {
    autosaveRef.current = setInterval(() => {
      persistDisplayedStateSilently();
    }, AUTOSAVE_MS);
    return () => { if (autosaveRef.current) clearInterval(autosaveRef.current); };
  }, [persistDisplayedStateSilently]);

  // Flush on page hide
  useEffect(() => {
    const onHide = () => { persistDisplayedStateSilently(true); };
    window.addEventListener('pagehide', onHide);
    return () => window.removeEventListener('pagehide', onHide);
  }, [persistDisplayedStateSilently]);

  // Reload if hidden > 30s
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'hidden') {
        hiddenAtRef.current = Date.now();
      } else if (hiddenAtRef.current && Date.now() - hiddenAtRef.current > HIDDEN_RELOAD_MS) {
        reloadFromServer();
      }
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [reloadFromServer]);

  // BroadcastChannel sync
  useEffect(() => {
    const bc = new BroadcastChannel('zooparkbot-sync');
    bc.onmessage = (e) => {
      if (e.data?.type === 'state') patchState(e.data.state);
    };
    return () => bc.close();
  }, [patchState]);

  const handleLogin = (id: string) => {
    hapticImpact('medium');
    setDevUserId(id);
    void loadFromServer();
  };

  // ── Action handlers ──────────────────────────────────────────────────────

  const handleBuyAviary = async (aviaryId: string) => {
    if (!state) return;
    hapticImpact('medium');
    try {
      const res = await apiBuyAviary(aviaryId);
      if (!res.ok) { hapticNotification('error'); showToast('err', 'Не удалось купить вольер'); return; }
      hapticNotification('success');
      const existingIdx = state.aviaries.findIndex(a => a.aviary_id === aviaryId);
      const newAviaries = existingIdx >= 0
        ? state.aviaries.map((a, i) => i === existingIdx ? { ...a, count: res.new_count } : a)
        : [...state.aviaries, { aviary_id: aviaryId, count: res.new_count }];
      patchState({
        rub: res.new_rub,
        aviaries: newAviaries,
        total_seats: res.new_total_seats,
        free_seats: res.new_free_seats,
      });
      showToast('ok', '🏗️ Вольер куплен!');
    } catch (e) {
      hapticNotification('error');
      showToast('err', e instanceof Error ? e.message : 'Ошибка покупки');
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="h-full bg-tg-bg overflow-hidden">
      <Toast msg={toast} />

      {!inTma && <DevBar onLogin={handleLogin} />}

      {/* Loading */}
      {loading && !state && (
        <div className="pb-20">
          <div className="px-[14px] pt-4">
            <div className="card mb-3">
              <div className="flex items-center gap-3">
                <Skeleton width={44} height={44} variant="circular" />
                <div>
                  <Skeleton width={120} height={20} className="mb-1" />
                  <Skeleton width={80} height={12} />
                </div>
              </div>
            </div>
            <div className="flex gap-2 mb-3">
              <Skeleton width={70} height={28} />
              <Skeleton width={70} height={28} />
              <Skeleton width={70} height={28} />
            </div>
            <PageSkeleton />
          </div>
        </div>
      )}

      {/* Access denied (closed beta) */}
      {errorStatus === 403 && !state && <ComingSoonScreen />}

      {/* Error */}
      {error && !state && errorStatus !== 403 && (
        <div className={`max-w-[480px] mx-auto p-6 ${!inTma ? 'pt-[70px]' : ''}`}>
          <div className="bg-tg-secondary rounded-2xl p-5 border border-[rgba(var(--c-red-rgb),0.28)]">
            <p className="m-0 mb-[6px] text-lg font-bold">⚠️ Ошибка загрузки</p>
            <p className="m-0 mb-[14px] text-tg-hint text-[13px]">{error}</p>
            <button
              onClick={reloadFromServer}
              className="w-full py-3 rounded-xl border-none bg-[var(--c-blue)] text-[var(--tg-theme-button-text-color)] cursor-pointer font-bold"
            >
              Повторить
            </button>
          </div>
        </div>
      )}

      {/* Register */}
      {!loading && !error && !state && !errorStatus && (
        <RegisterScreen onDone={setGameState} />
      )}

      {/* Main app */}
      {state && displayState && (
        <div
          className={`app-shell max-w-[480px] mx-auto relative ${!inTma ? 'pt-12' : ''}`}
          style={inTma ? { paddingTop: 'var(--safe-top)' } : undefined}
        >
          <div key={tab} className="page-enter page-scroll-area">
            <Suspense fallback={<PageFallback />}>
              {tab === 'zoo' && (
                <ZooPage gs={displayState} onRefresh={reloadFromServer} />
              )}
              {tab === 'shop' && (
                <ShopPage
                  gs={displayState}
                  onBuyAviary={id => void handleBuyAviary(id)}
                  onRefresh={reloadFromServer}
                />
              )}
              {tab === 'lab' && (
                <LabPage gs={displayState} />
              )}
              {tab === 'games' && (
                <GamesPage gs={displayState} onRefresh={reloadFromServer} initialTab={inviteGameId ? 'multi' : undefined} inviteGameId={inviteGameId ?? undefined} />
              )}
              {tab === 'more' && (
                <MorePage gs={displayState} onRefresh={reloadFromServer} />
              )}
            </Suspense>
          </div>

          <TabBar active={tab} onChange={setTab} />
        </div>
      )}
    </div>
  );
}
