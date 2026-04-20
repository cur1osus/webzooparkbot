import { init, miniApp, viewport, popup } from '@tma.js/sdk';

const VIEWPORT_CSS_VAR_NAMES: Record<string, string> = {
  height: '--tg-viewport-height',
  width: '--tg-viewport-width',
  stableHeight: '--tg-viewport-stable-height',
  safeAreaInsetTop: '--tg-safe-area-inset-top',
  safeAreaInsetBottom: '--tg-safe-area-inset-bottom',
  safeAreaInsetLeft: '--tg-safe-area-inset-left',
  safeAreaInsetRight: '--tg-safe-area-inset-right',
  contentSafeAreaInsetTop: '--tg-content-safe-area-inset-top',
  contentSafeAreaInsetBottom: '--tg-content-safe-area-inset-bottom',
  contentSafeAreaInsetLeft: '--tg-content-safe-area-inset-left',
  contentSafeAreaInsetRight: '--tg-content-safe-area-inset-right',
};

/** Reads safe area insets from Telegram.WebApp and writes them to CSS vars */
function syncSafeAreaVars() {
  const tg = (window as { Telegram?: { WebApp?: {
    safeAreaInset?: { top: number; bottom: number; left: number; right: number };
    contentSafeAreaInset?: { top: number; bottom: number; left: number; right: number };
  } } }).Telegram?.WebApp;
  if (!tg) return;

  const root = document.documentElement;
  const sai  = tg.safeAreaInset        ?? { top: 0, bottom: 0, left: 0, right: 0 };
  const csai = tg.contentSafeAreaInset ?? { top: 0, bottom: 0, left: 0, right: 0 };

  root.style.setProperty('--tg-safe-area-inset-top',            `${sai.top}px`);
  root.style.setProperty('--tg-safe-area-inset-bottom',         `${sai.bottom}px`);
  root.style.setProperty('--tg-safe-area-inset-left',           `${sai.left}px`);
  root.style.setProperty('--tg-safe-area-inset-right',          `${sai.right}px`);
  root.style.setProperty('--tg-content-safe-area-inset-top',    `${csai.top}px`);
  root.style.setProperty('--tg-content-safe-area-inset-bottom', `${csai.bottom}px`);
  root.style.setProperty('--tg-content-safe-area-inset-left',   `${csai.left}px`);
  root.style.setProperty('--tg-content-safe-area-inset-right',  `${csai.right}px`);
}

/** true если приложение запущено внутри Telegram */
export let inTma = false;

try {
  init();
  miniApp.mount();
  miniApp.bindCssVars();
  miniApp.ready();
  viewport.mount();
  viewport.expand();
  if (viewport.requestFullscreen.isAvailable()) {
    viewport.requestFullscreen();
  }
  viewport.bindCssVars((key) => VIEWPORT_CSS_VAR_NAMES[key]);

  // Sync safe-area insets from Telegram.WebApp directly (reliable on all clients)
  syncSafeAreaVars();
  // Re-sync after fullscreen takes effect (async in Telegram)
  setTimeout(syncSafeAreaVars, 150);
  setTimeout(syncSafeAreaVars, 500);
  const tgWa = (window as { Telegram?: { WebApp?: { onEvent?: (e: string, cb: () => void) => void } } }).Telegram?.WebApp;
  tgWa?.onEvent?.('safeAreaChanged',        syncSafeAreaVars);
  tgWa?.onEvent?.('contentSafeAreaChanged', syncSafeAreaVars);
  tgWa?.onEvent?.('viewportChanged',        syncSafeAreaVars);

  inTma = true;
} catch {
  inTma = false;
}

type HapticStyle = 'light' | 'medium' | 'heavy';

/** Trigger haptic feedback */
export function hapticImpact(style: HapticStyle = 'light') {
  if (!inTma) return;
  try {
    const impactMap: Record<HapticStyle, 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'> = {
      light: 'light',
      medium: 'medium',
      heavy: 'heavy',
    };
    // @ts-expect-error - haptic might not be on miniApp in all versions
    miniApp.haptic?.impactOccurred?.(impactMap[style]);
  } catch {
    // Haptic not available
  }
}

export function hapticNotification(type: 'success' | 'warning' | 'error' = 'success') {
  if (!inTma) return;
  try {
    // @ts-expect-error - haptic might not be on miniApp in all versions
    miniApp.haptic?.notificationOccurred?.(type);
  } catch {
    // Haptic not available
  }
}

/** Confirm dialog: uses Telegram native popup in TMA, falls back to window.confirm in browser */
export async function tmaConfirm(message: string, title?: string): Promise<boolean> {
  if (inTma) {
    try {
      const buttonId = await popup.show({
        title,
        message,
        buttons: [{ id: 'ok', type: 'ok' }, { id: 'cancel', type: 'cancel' }],
      });
      return buttonId === 'ok';
    } catch {
      // Popup not supported or failed — fall through to window.confirm
    }
  }
  return window.confirm(title ? `${title}\n${message}` : message);
}
