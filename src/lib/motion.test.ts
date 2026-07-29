// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest';
import { preferredTgsFps } from './motion';

afterEach(() => document.documentElement.classList.remove('motion-quality-low'));

describe('preferredTgsFps', () => {
  it('caps normal decorative stickers at 30fps', () => {
    expect(preferredTgsFps()).toBe(30);
  });

  it('uses a lower cadence on constrained devices without disabling the visual', () => {
    document.documentElement.classList.add('motion-quality-low');
    expect(preferredTgsFps()).toBe(20);
  });
});
