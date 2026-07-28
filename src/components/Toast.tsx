import { createPortal } from 'react-dom';

type ToastProps = {
  toast: { kind: 'success' | 'error'; message: string } | null;
};

export function Toast({ toast }: ToastProps) {
  if (!toast) return null;
  return createPortal(
    <div
      className={`toast toast-${toast.kind}`}
      data-testid="app-toast"
      role={toast.kind === 'error' ? 'alert' : 'status'}
      aria-live={toast.kind === 'error' ? 'assertive' : 'polite'}
    >
      <span className="toast-icon" aria-hidden="true">{toast.kind === 'error' ? '⚠️' : '✓'}</span>
      <span className="toast-message">{toast.message}</span>
    </div>,
    document.body,
  );
}
