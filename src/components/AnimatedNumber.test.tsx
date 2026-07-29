// @vitest-environment jsdom

import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AnimatedNumber } from './AnimatedNumber';

describe('AnimatedNumber', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('finishes the count-up without a permanent requestAnimationFrame loop', () => {
    const raf = vi.spyOn(window, 'requestAnimationFrame');
    const view = render(<AnimatedNumber value={0} format={String} durationMs={850} />);
    view.rerender(<AnimatedNumber value={100} format={String} durationMs={850} />);

    act(() => vi.advanceTimersByTime(1_000));

    expect(screen.getByText('100')).toBeTruthy();
    expect(raf).not.toHaveBeenCalled();
  });
});
