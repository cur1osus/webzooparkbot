import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { useZooStore } from '@/store';
import { TabBar } from '@/components/TabBar';
import { PageSkeleton, Skeleton } from '@/components/Skeleton';
import { ApiError, apiClaimTransfer, setDevUserId } from '@/api';
import { useLiveGameState } from '@/hooks/useLiveGameState';
import { useHashTab } from '@/lib/hashRoute';
import { inTma, hapticImpact, readyTma } from '@/lib/tma';
import { getTelegramStartParam } from '@/lib/tmaEnv';
import { fmt, formatCountdown } from '@/utils/format';
import { ComingSoonScreen } from '@/pages/ComingSoonScreen';
import { DevBar } from '@/components/DevBar';
import { RegisterScreen } from '@/pages/RegisterScreen';

const HIDDEN_RELOAD_MS = 30_000;
const TRANSFER_HANDLED_STORAGE_KEY = 'zoopark_transfer_claims_v1';

function getInviteGameId(): number | null {
  const startParam = getTelegramStartParam();
  const match = startParam?.match(/^mpgame_(\d+)$/);
  return match ? Number(match[1]) : null;
}

function getTransferCode(): string | null {
  const startParam = getTelegramStartParam();
  const match = startParam?.match(/^transfer_([A-Za-z0-9_-]+)$/);
  return match ? match[1] : null;
}

function transferHandledKey(tgId: number, code: string): string {
  return `${TRANSFER_HANDLED_STORAGE_KEY}:${tgId}:${code}`;
}

function wasTransferHandled(tgId: number, code: string): boolean {
  try {
    return window.localStorage.getItem(transferHandledKey(tgId, code)) === '1';
  } catch {
    return false;
  }
}

function rememberTransferHandled(tgId: number, code: string): void {
  try {
    window.localStorage.setItem(transferHandledKey(tgId, code), '1');
  } catch {
    // Storage can be unavailable in a restricted Telegram/browser context.
  }
}

function isTerminalTransferError(error: unknown): boolean {
  if (!(error instanceof ApiError) || error.status !== 400) return false;
  return [
    'Ты уже получил этот перевод',
    'Ссылка уже израсходована',
    'Срок действия ссылки истёк',
    'Нельзя получить собственный перевод',
  ].some(message => error.message.includes(message));
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

function MaintenanceScreen({ message, endsAt, onRefresh }: { message: string; endsAt: string | null; onRefresh: () => void }) {
  const [now, setNow] = useState(() => Date.now());
  const refreshedRef = useRef(false);
  const remainingSeconds = endsAt
    ? Math.max(0, Math.floor((new Date(endsAt).getTime() - now) / 1000))
    : 0;

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (remainingSeconds > 0 || refreshedRef.current) return;
    refreshedRef.current = true;
    onRefresh();
  }, [onRefresh, remainingSeconds]);

  return (
    <div className="maintenance-screen min-h-full flex items-center justify-center px-5 py-12">
      <div className="maintenance-screen-card w-full max-w-[390px] text-center">
        <div className="maintenance-screen-icon">🔧</div>
        <p className="m-0 mt-5 font-display text-[28px] leading-none">Технический перерыв</p>
        <p className="m-0 mt-3 text-[13px] leading-[1.5] text-tg-hint">{message}</p>
        <div className="maintenance-countdown mt-6">
          <span>{formatCountdown(remainingSeconds)}</span>
          <small>до возвращения игры</small>
        </div>
        <p className="m-0 mt-5 text-[11px] text-tg-hint">Страница обновится автоматически</p>
      </div>
    </div>
  );
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const { state, loading, error, errorStatus, loadFromServer, setGameState, patchState } = useZooStore();
  const displayState = useLiveGameState(state);
  const [tab, setTab] = useHashTab();
  const [tabResetSignal, setTabResetSignal] = useState(0);
  const [inviteGameId] = useState<number | null>(() => getInviteGameId());
  const [transferCode] = useState<string | null>(() => getTransferCode());
  const transferClaimStartedRef = useRef<string | null>(null);
  const [transferNotice, setTransferNotice] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);
  const hiddenAtRef = useRef<number | null>(null);

  const reloadFromServer = useCallback(() => {
    void loadFromServer();
  }, [loadFromServer]);

  // Initial load
  useEffect(() => { void loadFromServer(); }, [loadFromServer]);

  useEffect(() => {
    if (inviteGameId) setTab('games');
  }, [inviteGameId, setTab]);

  // A giveaway deep link carries `transfer_<code>`. Claim it after the player is
  // loaded; for a brand-new recipient this naturally runs after registration.
  useEffect(() => {
    if (!state || !transferCode) return;
    const claimKey = `${state.tg_id}:${transferCode}`;
    if (transferClaimStartedRef.current === claimKey) return;
    transferClaimStartedRef.current = claimKey;
    if (wasTransferHandled(state.tg_id, transferCode)) return;

    void apiClaimTransfer(transferCode)
      .then((result) => {
        rememberTransferHandled(state.tg_id, transferCode);
        patchState({ rub: result.new_rub });
        setTransferNotice({ kind: 'success', message: `Получено ₽ ${fmt(result.rub_received)} из раздачи` });
      })
      .catch((e) => {
        // A launch parameter survives reloads in Telegram. Once the server confirms
        // that this account cannot claim the code anymore, suppress future retries.
        if (isTerminalTransferError(e)) {
          rememberTransferHandled(state.tg_id, transferCode);
          return;
        }
        setTransferNotice({
          kind: 'error',
          message: e instanceof Error ? `Раздача не получена: ${e.message}` : 'Не удалось получить раздачу',
        });
      });
  }, [patchState, state, transferCode]);

  // Keep the result visible long enough to read, then return the interface to
  // its normal state. A new notice restarts the timer.
  useEffect(() => {
    if (!transferNotice) return;
    const timeoutId = window.setTimeout(() => setTransferNotice(null), 4_000);
    return () => window.clearTimeout(timeoutId);
  }, [transferNotice]);

  // Keep a player on the maintenance screen in sync if the administrator ends the
  // break early. The server's absolute deadline remains the source of truth.
  useEffect(() => {
    if (!state?.maintenance?.active || state.is_admin) return;
    const timer = window.setInterval(() => void loadFromServer(), 10_000);
    return () => window.clearInterval(timer);
  }, [loadFromServer, state?.is_admin, state?.maintenance?.active]);

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

  const handleTabChange = useCallback((nextTab: typeof tab) => {
    if (nextTab === tab) {
      setTabResetSignal(signal => signal + 1);
      return;
    }
    setTab(nextTab);
  }, [setTab, tab]);

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

      {/* Technical break for regular players; admins keep access to end it. */}
      {state?.maintenance?.active && !state.is_admin && (
        <MaintenanceScreen
          message={state.maintenance.message}
          endsAt={state.maintenance.ends_at}
          onRefresh={reloadFromServer}
        />
      )}

      {/* Main app */}
      {state && displayState && (!state.maintenance?.active || state.is_admin) && (
        <div
          className={`app-shell max-w-[480px] mx-auto relative ${!inTma ? 'pt-12' : ''}`}
          style={inTma ? { paddingTop: 'var(--safe-top)' } : undefined}
        >
          {transferNotice && (
            <div className={`transfer-claim-toast transfer-claim-toast-${transferNotice.kind}`} role="status">
              <span>{transferNotice.kind === 'success' ? '🎉' : '⚠️'}</span>
              <span>{transferNotice.message}</span>
            </div>
          )}
          <div key={`${tab}-${tabResetSignal}`} className="page-enter page-scroll-area">
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

          <TabBar active={tab} onChange={handleTabChange} />
        </div>
      )}
    </div>
  );
}
