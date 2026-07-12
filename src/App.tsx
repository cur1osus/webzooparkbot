import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { useZooStore } from '@/store';
import { TabBar } from '@/components/TabBar';
import { PageSkeleton, Skeleton } from '@/components/Skeleton';
import { setDevUserId } from '@/api';
import { useLiveGameState } from '@/hooks/useLiveGameState';
import { useHashTab } from '@/lib/hashRoute';
import { inTma, hapticImpact, readyTma } from '@/lib/tma';
import { getTelegramStartParam } from '@/lib/tmaEnv';
import { ComingSoonScreen } from '@/pages/ComingSoonScreen';
import { DevBar } from '@/components/DevBar';
import { RegisterScreen } from '@/pages/RegisterScreen';

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
  const { state, loading, error, errorStatus, loadFromServer, setGameState, patchState } = useZooStore();
  const displayState = useLiveGameState(state);
  const [tab, setTab] = useHashTab();
  const [inviteGameId] = useState<number | null>(() => getInviteGameId());
  const hiddenAtRef = useRef<number | null>(null);

  const reloadFromServer = useCallback(() => {
    void loadFromServer();
  }, [loadFromServer]);

  // Initial load
  useEffect(() => { void loadFromServer(); }, [loadFromServer]);

  useEffect(() => {
    if (inviteGameId) setTab('games');
  }, [inviteGameId, setTab]);

  // Tell Telegram to hide the launch placeholder once the root tree is mounted.
  useEffect(() => {
    readyTma();
  }, []);

  // Nothing to autosave: currencies are server-authoritative and every endpoint that
  // moves them returns the new balance. `/api/save` used to run every 15 seconds to POST
  // a `data_version` nobody read.

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

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="h-full bg-tg-bg overflow-hidden">
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
                  onRefresh={reloadFromServer}
                />
              )}
              {tab === 'lab' && (
                <LabPage gs={displayState} onRefresh={reloadFromServer} />
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
