export interface VirtualGridWindowOptions {
  itemCount: number;
  columns: number;
  rowStride: number;
  viewportTop: number;
  viewportHeight: number;
  overscanRows?: number;
}

export interface VirtualGridWindow {
  start: number;
  end: number;
  totalHeight: number;
}

/**
 * Return the small item window that intersects the viewport. The full grid height is
 * retained by one spacer, so the scrollbar behaves exactly like a normal grid while
 * off-screen cards are unmounted instead of accumulating in the mobile WebView.
 */
export function getVirtualGridWindow({
  itemCount,
  columns,
  rowStride,
  viewportTop,
  viewportHeight,
  overscanRows = 4,
}: VirtualGridWindowOptions): VirtualGridWindow {
  if (itemCount <= 0 || columns <= 0 || rowStride <= 0) {
    return { start: 0, end: 0, totalHeight: 0 };
  }

  const rowCount = Math.ceil(itemCount / columns);
  const firstVisibleRow = Math.min(
    rowCount - 1,
    Math.max(0, Math.floor(Math.max(0, viewportTop) / rowStride)),
  );
  const lastVisibleRow = Math.min(
    rowCount,
    Math.ceil((Math.max(0, viewportTop) + Math.max(0, viewportHeight)) / rowStride),
  );
  const startRow = Math.max(0, firstVisibleRow - overscanRows);
  const endRow = Math.min(rowCount, lastVisibleRow + overscanRows);

  return {
    start: startRow * columns,
    end: Math.min(itemCount, endRow * columns),
    totalHeight: rowCount * rowStride,
  };
}
