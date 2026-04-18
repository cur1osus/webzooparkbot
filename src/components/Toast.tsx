type ToastProps = {
  toast: { kind: 'success' | 'error'; message: string } | null;
};

export function Toast({ toast }: ToastProps) {
  if (!toast) return null;
  return <div className={`toast toast-${toast.kind}`}>{toast.message}</div>;
}
