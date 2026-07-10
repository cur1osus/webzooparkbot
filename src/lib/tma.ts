import { hapticFeedback, init, miniApp, openLink, openTelegramLink, popup, shareURL, themeParams, viewport } from '@tma.js/sdk';
import { ensureTelegramMockEnv, hasRealTelegramRuntime } from './tmaEnv';

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

type HapticStyle = 'light' | 'medium' | 'heavy';

let sdkInitialized = false;
let readyRequested = false;
let readySent = false;

ensureTelegramMockEnv();

/** true если приложение запущено внутри реального Telegram */
export const inTma = hasRealTelegramRuntime;

/** Reads safe area insets from Telegram.WebApp and writes them to CSS vars */
function syncSafeAreaVars() {
  const tg = (window as { Telegram?: { WebApp?: {
    safeAreaInset?: { top: number; bottom: number; left: number; right: number };
    contentSafeAreaInset?: { top: number; bottom: number; left: number; right: number };
  } } }).Telegram?.WebApp;
  if (!tg) return;

  const root = document.documentElement;
  const safeAreaInset = tg.safeAreaInset ?? { top: 0, bottom: 0, left: 0, right: 0 };
  const contentSafeAreaInset = tg.contentSafeAreaInset ?? { top: 0, bottom: 0, left: 0, right: 0 };

  root.style.setProperty('--tg-safe-area-inset-top', `${safeAreaInset.top}px`);
  root.style.setProperty('--tg-safe-area-inset-bottom', `${safeAreaInset.bottom}px`);
  root.style.setProperty('--tg-safe-area-inset-left', `${safeAreaInset.left}px`);
  root.style.setProperty('--tg-safe-area-inset-right', `${safeAreaInset.right}px`);
  root.style.setProperty('--tg-content-safe-area-inset-top', `${contentSafeAreaInset.top}px`);
  root.style.setProperty('--tg-content-safe-area-inset-bottom', `${contentSafeAreaInset.bottom}px`);
  root.style.setProperty('--tg-content-safe-area-inset-left', `${contentSafeAreaInset.left}px`);
  root.style.setProperty('--tg-content-safe-area-inset-right', `${contentSafeAreaInset.right}px`);
}

function scheduleSafeAreaResync() {
  syncSafeAreaVars();
  window.setTimeout(syncSafeAreaVars, 150);
  window.setTimeout(syncSafeAreaVars, 500);

  const tgWebApp = (window as { Telegram?: { WebApp?: { onEvent?: (event: string, cb: () => void) => void } } }).Telegram?.WebApp;
  tgWebApp?.onEvent?.('safeAreaChanged', syncSafeAreaVars);
  tgWebApp?.onEvent?.('contentSafeAreaChanged', syncSafeAreaVars);
  tgWebApp?.onEvent?.('viewportChanged', syncSafeAreaVars);
}

function buildTelegramShareUrl(url: string, text?: string): string {
  const params = new URLSearchParams({ url });
  if (text) params.set('text', text);
  return `https://t.me/share/url?${params.toString()}`;
}

function isTelegramUrl(url: string | URL): boolean {
  const parsed = typeof url === 'string' ? new URL(url, window.location.href) : url;
  return parsed.hostname === 't.me' || parsed.hostname.endsWith('.t.me');
}

function openBrowserFallback(url: string): void {
  window.open(url, '_blank', 'noopener,noreferrer');
}

function mountThemeParams(): void {
  // The game commits to its own "safari lodge at dusk" palette (defined in
  // index.css) and deliberately does NOT inherit the user's Telegram theme, so
  // its identity is consistent for every player. We mount themeParams (some SDK
  // features expect it) but never bind its CSS vars over ours.
  if (!themeParams.mount.isAvailable()) return;
  themeParams.mount();
}

async function initializeTma(): Promise<void> {
  try {
    init();
    mountThemeParams();
    miniApp.mount();
    miniApp.bindCssVars();
    // Match the native Telegram header to our dusk ground so there is no seam at
    // the top edge. Progressive enhancement — never block init.
    try {
      if (miniApp.setHeaderColor.isAvailable()) miniApp.setHeaderColor('#14140e');
    } catch { /* ignore — cosmetic only */ }
    sdkInitialized = true;

    if (readyRequested) {
      readyTma();
    }
  } catch {
    sdkInitialized = false;
    return;
  }

  try {
    await viewport.mount();
    viewport.bindCssVars((key) => VIEWPORT_CSS_VAR_NAMES[key]);
    viewport.expand();

    if (viewport.requestFullscreen.isAvailable()) {
      try {
        await viewport.requestFullscreen();
      } catch {
        // Fullscreen is a progressive enhancement and should never block app startup.
      }
    }

    scheduleSafeAreaResync();
  } catch {
    // Viewport/fullscreen integrations are progressive enhancements.
  }
}

void initializeTma();

/** Hides Telegram's loading placeholder once the React tree is mounted. */
export function readyTma() {
  readyRequested = true;
  if (!sdkInitialized || readySent) return;
  if (!miniApp.ready.isAvailable()) return;

  try {
    miniApp.ready();
    readySent = true;
  } catch {
    // No-op outside Telegram.
  }
}

/** Trigger haptic feedback */
export function hapticImpact(style: HapticStyle = 'light') {
  if (!inTma) return;

  try {
    hapticFeedback.impactOccurred(style);
  } catch {
    // Haptic feedback is optional across Telegram clients.
  }
}

export function hapticNotification(type: 'success' | 'warning' | 'error' = 'success') {
  if (!inTma) return;

  try {
    hapticFeedback.notificationOccurred(type);
  } catch {
    // Haptic feedback is optional across Telegram clients.
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
      // Popup is optional across Telegram clients.
    }
  }

  return window.confirm(title ? `${title}\n${message}` : message);
}

/** Shares a link using Telegram-native primitives when possible, with browser fallbacks for previews. */
export async function shareTmaUrl(url: string, text?: string): Promise<void> {
  const telegramShareUrl = buildTelegramShareUrl(url, text);

  if (inTma) {
    if (shareURL.isAvailable()) {
      try {
        shareURL(url, text);
        return;
      } catch {
        // Fall through to the next Telegram-native fallback.
      }
    }

    if (openLink.isAvailable()) {
      try {
        openLink(telegramShareUrl);
        return;
      } catch {
        // Fall through to browser-level fallbacks.
      }
    }
  }

  if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
    try {
      await navigator.share({ text, url });
      return;
    } catch {
      // If user cancels share sheet, silently keep the final fallback.
    }
  }

  openBrowserFallback(telegramShareUrl);
}

/** Opens external URLs with Telegram-native APIs when available. */
export function openTmaLink(url: string): void {
  if (inTma) {
    if (isTelegramUrl(url) && openTelegramLink.isAvailable()) {
      try {
        openTelegramLink(url);
        return;
      } catch {
        // Fall through to generic link opening.
      }
    }

    if (openLink.isAvailable()) {
      try {
        openLink(url);
        return;
      } catch {
        // Fall through to browser fallback.
      }
    }
  }

  openBrowserFallback(url);
}

/** Copies text using the browser clipboard with a legacy fallback for older WebViews. */
export async function copyTmaText(value: string): Promise<boolean> {
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value);
      return true;
    } catch {
      // Fall through to execCommand fallback.
    }
  }

  try {
    const textarea = document.createElement('textarea');
    textarea.value = value;
    textarea.setAttribute('readonly', 'true');
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    textarea.style.pointerEvents = 'none';
    document.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, value.length);
    const copied = document.execCommand('copy');
    document.body.removeChild(textarea);
    return copied;
  } catch {
    return false;
  }
}
