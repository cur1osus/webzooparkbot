import { describe, expect, it } from 'vitest';
import { buildBotLink, normalizeBotUsername } from './botLinks';

describe('bot links', () => {
  it('normalizes Telegram usernames and encodes deep-link parameters', () => {
    expect(normalizeBotUsername('@Zoo_Park_bot')).toBe('Zoo_Park_bot');
    expect(buildBotLink('@Zoo_Park_bot', { startapp: 'transfer_a/b' })).toBe(
      'https://t.me/Zoo_Park_bot?startapp=transfer_a%2Fb',
    );
  });

  it('does not create a link without a resolved bot username', () => {
    expect(buildBotLink(null, { start: '123' })).toBeNull();
  });
});
