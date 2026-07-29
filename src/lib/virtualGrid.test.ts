import { describe, expect, it } from 'vitest';
import { getVirtualGridWindow } from './virtualGrid';

describe('getVirtualGridWindow', () => {
  it('keeps only the visible rows and overscan mounted', () => {
    expect(getVirtualGridWindow({
      itemCount: 11_500,
      columns: 2,
      rowStride: 90,
      viewportTop: 9_000,
      viewportHeight: 800,
      overscanRows: 4,
    })).toEqual({
      start: 192,
      end: 226,
      totalHeight: 517_500,
    });
  });

  it('clamps the final window to the item count', () => {
    expect(getVirtualGridWindow({
      itemCount: 13,
      columns: 2,
      rowStride: 90,
      viewportTop: 10_000,
      viewportHeight: 800,
    })).toEqual({ start: 4, end: 13, totalHeight: 630 });
  });

  it('handles an empty grid', () => {
    expect(getVirtualGridWindow({
      itemCount: 0,
      columns: 2,
      rowStride: 90,
      viewportTop: 0,
      viewportHeight: 800,
    })).toEqual({ start: 0, end: 0, totalHeight: 0 });
  });
});
