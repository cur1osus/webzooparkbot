import { useState } from 'react';
import { apiRegister } from '@/api';
import type { GameState } from '@/types';

export function RegisterScreen({ onDone }: { onDone: (gs: GameState) => void }) {
  const [nickname, setNickname] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async () => {
    const n = nickname.trim();
    if (n.length < 3) { setError('Никнейм слишком короткий (мин. 3 символа)'); return; }
    setLoading(true);
    setError(null);
    try {
      const res = await apiRegister(n);
      if (res.ok) onDone(res.game_state);
      else setError('Ошибка регистрации');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-dvh flex items-center px-6 max-w-[480px] mx-auto">
      <div className="w-full bg-tg-secondary rounded-[20px] p-6 border" style={{ borderColor: 'var(--surface-overlay-border)' }}>
        <div className="text-center mb-6">
          <div className="text-[56px] mb-2">🦁</div>
          <p className="m-0 text-[22px] font-extrabold">ZooPark</p>
          <p className="mt-[6px] mb-0 text-sm text-tg-hint">
            Строй свой зоопарк и зарабатывай!
          </p>
        </div>

        <div className="flex flex-col gap-3">
          <input
            value={nickname}
            onChange={e => setNickname(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && void handleRegister()}
            placeholder="Твой никнейм"
            maxLength={64}
            className="text-input text-base"
            style={{ fontSize: 16, padding: '12px 14px' }}
          />
          {error && (
            <p className="m-0 text-[var(--c-red-soft)] text-[13px]">⚠️ {error}</p>
          )}
          <button
            onClick={() => void handleRegister()}
            disabled={loading || nickname.trim().length < 3}
            className="py-[14px] rounded-xl border-none bg-tg-button text-[var(--tg-theme-button-text-color)] font-extrabold text-base disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {loading ? 'Создаём профиль...' : 'Начать игру 🚀'}
          </button>
        </div>

        <div className="surface-subtle mt-5 p-[14px] rounded-xl">
          <p className="m-0 mb-[6px] text-[13px] font-semibold">Как играть:</p>
          {[
            '🏗️ Купи вольер → размести животных',
            '🐾 Зарабатывай рубли каждую минуту',
            '💱 Обменивай рубли на доллары в банке',
            '🎮 Участвуй в играх и турнирах',
          ].map(t => (
            <p key={t} className="m-0 mb-1 text-xs text-tg-hint">{t}</p>
          ))}
        </div>
      </div>
    </div>
  );
}
