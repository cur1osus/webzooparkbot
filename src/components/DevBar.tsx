import { useState } from 'react';
import { clearDevUserId, isDevMode } from '@/api';

export function DevBar({ onLogin }: { onLogin: (id: string) => void }) {
  const [val, setVal] = useState('');
  return (
    <div className="surface-overlay fixed top-0 left-1/2 -translate-x-1/2 w-full max-w-[480px] z-[200] px-3 py-2 flex gap-2 items-center backdrop-blur-xl">
      <input
        value={val}
        onChange={e => setVal(e.target.value)}
        placeholder="Dev user ID"
        onKeyDown={e => e.key === 'Enter' && val.trim() && onLogin(val.trim())}
        className="text-input flex-1 min-h-0 py-[7px] text-[13px]"
      />
      <button
        onClick={() => val.trim() && onLogin(val.trim())}
        className="px-[14px] py-[7px] rounded-lg bg-[var(--c-blue)] text-[var(--tg-theme-button-text-color)] text-[13px] border-none cursor-pointer"
      >
        Войти
      </button>
      {isDevMode() && (
        <button
          onClick={() => { clearDevUserId(); window.location.reload(); }}
          className="px-[10px] py-[7px] rounded-lg border bg-transparent text-tg-hint text-[13px] cursor-pointer"
          style={{ borderColor: 'var(--surface-overlay-border)' }}
        >
          ✕
        </button>
      )}
    </div>
  );
}
