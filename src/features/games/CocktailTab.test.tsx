// @vitest-environment jsdom

import { act, cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CocktailState } from '@/types';

vi.mock('@/api', () => ({
  apiCocktailGuess: vi.fn(),
  apiGetCocktailState: vi.fn(),
}));

import { apiGetCocktailState } from '@/api';
import { CocktailTab } from './CocktailTab';

const playable: CocktailState = {
  ok: true,
  attempts_left: 10,
  history: [],
  solved: false,
  rewarded: false,
  was_first: false,
  winner_nickname: null,
  solved_today: 0,
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function deferredState() {
  let resolve!: (state: CocktailState) => void;
  const promise = new Promise<CocktailState>((done) => { resolve = done; });
  vi.mocked(apiGetCocktailState).mockReturnValue(promise);
  return resolve;
}

describe('CocktailTab initial state', () => {
  it('does not expose the playable board before the server snapshot arrives', async () => {
    const resolve = deferredState();
    render(<CocktailTab onRefresh={vi.fn()} />);

    expect(screen.getByText('Проверяем коктейль дня…')).toBeTruthy();
    expect(screen.queryByText('Угадать! 🔮')).toBeNull();

    await act(async () => resolve(playable));

    expect(screen.getByText('Угадать! 🔮')).toBeTruthy();
  });

  it('goes directly from loading to the solved card without flashing the board', async () => {
    const resolve = deferredState();
    render(<CocktailTab onRefresh={vi.fn()} />);

    expect(screen.queryByText('Угадать! 🔮')).toBeNull();
    await act(async () => resolve({
      ...playable,
      attempts_left: 4,
      solved: true,
      rewarded: true,
      was_first: true,
      winner_nickname: 'Смотритель',
      solved_today: 3,
    }));

    expect(screen.getByText('Рецепт разгадан')).toBeTruthy();
    expect(screen.getByText('Ты первый!')).toBeTruthy();
    expect(screen.queryByText('Угадать! 🔮')).toBeNull();
  });
});
