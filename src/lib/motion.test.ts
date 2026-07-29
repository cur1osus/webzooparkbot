// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest';
import { preferredTgsFps } from './motion';

afterEach(() => document.documentElement.classList.remove('motion-quality-low'));

describe('preferredTgsFps', () => {
  it('keeps TGS animations at their full authored cadence', () => {
    expect(preferredTgsFps()).toBe(60);
  });

  it('does not reduce TGS cadence on constrained devices', () => {
    document.documentElement.classList.add('motion-quality-low');
    expect(preferredTgsFps()).toBe(60);
  });
});
