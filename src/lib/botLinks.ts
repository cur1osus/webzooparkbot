export function normalizeBotUsername(value: string | null | undefined): string | null {
  if (!value) return null;
  const username = value.trim().replace(/^@/, '').split(/[/?#]/, 1)[0];
  return username || null;
}

export function buildBotLink(
  username: string | null | undefined,
  params: Record<string, string | number>,
): string | null {
  const normalized = normalizeBotUsername(username);
  if (!normalized) return null;

  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => search.set(key, String(value)));
  return `https://t.me/${normalized}?${search.toString()}`;
}
