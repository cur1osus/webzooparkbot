import { mockTelegramEnv, retrieveLaunchParams, retrieveRawInitData, serializeLaunchParamsQuery } from '@tma.js/sdk';

const MOCK_THEME_PARAMS = {
  accentTextColor: '#5ac8fa',
  bgColor: '#0f111a',
  bottomBarBgColor: '#1a1d2b',
  secondaryBgColor: '#1a1d2b',
  textColor: '#ffffff',
  hintColor: '#8f95ab',
  buttonColor: '#0a84ff',
  buttonTextColor: '#ffffff',
  destructiveTextColor: '#ff6b63',
  headerBgColor: '#0f111a',
  linkColor: '#5ac8fa',
  sectionBgColor: '#1a1d2b',
  sectionHeaderTextColor: '#8f95ab',
  sectionSeparatorColor: '#2a2f42',
  subtitleTextColor: '#b9bfd3',
} as const;

const hasWindow = typeof window !== 'undefined';
const telegramWindow = hasWindow ? (window as Window & { Telegram?: { WebApp?: unknown } }) : undefined;
const hasTelegramWebApp = Boolean(telegramWindow?.Telegram?.WebApp);

let mockConfigured = false;

export function hasTelegramLaunchParams(): boolean {
  if (!hasWindow) return false;

  try {
    retrieveLaunchParams();
    return true;
  } catch {
    return false;
  }
}

export const hasRealTelegramRuntime = hasTelegramWebApp || hasTelegramLaunchParams();

export function ensureTelegramMockEnv(): void {
  if (!hasWindow || hasRealTelegramRuntime || mockConfigured) return;

  mockTelegramEnv({
    launchParams: serializeLaunchParamsQuery({
      tgWebAppPlatform: 'tdesktop',
      tgWebAppVersion: '8.0',
      tgWebAppFullscreen: true,
      tgWebAppThemeParams: MOCK_THEME_PARAMS,
    }),
  });

  mockConfigured = true;
}

export function getRawTelegramInitData(): string | undefined {
  if (!hasWindow) return undefined;

  try {
    return retrieveRawInitData();
  } catch {
    return undefined;
  }
}

export function getTelegramStartParam(): string | undefined {
  if (!hasWindow) return undefined;

  try {
    const launchParams = retrieveLaunchParams() as unknown as {
      tgWebAppStartParam?: string;
      startParam?: string;
    };
    return launchParams.tgWebAppStartParam || launchParams.startParam || undefined;
  } catch {
    const params = new URLSearchParams(window.location.search);
    return params.get('tgWebAppStartParam') || params.get('startapp') || params.get('start') || undefined;
  }
}
