import type { Animal } from '@/types';

export type ProfileAnimal = Pick<Animal, 'species_code' | 'species_name' | 'species_emoji'> & {
  id?: number;
};

/** Catalog animals used only as a profile placeholder before the player owns one. */
export const DEFAULT_PROFILE_ANIMALS: ProfileAnimal[] = [
  { species_code: 'rabbit', species_name: 'Кролик', species_emoji: '🐇' },
  { species_code: 'flamingo', species_name: 'Фламинго', species_emoji: '🦩' },
  { species_code: 'fox', species_name: 'Лиса', species_emoji: '🦊' },
  { species_code: 'panda', species_name: 'Панда', species_emoji: '🐼' },
  { species_code: 'lion', species_name: 'Лев', species_emoji: '🦁' },
  { species_code: 'tiger', species_name: 'Тигр', species_emoji: '🐯' },
  { species_code: 'giraffe', species_name: 'Жираф', species_emoji: '🦒' },
  { species_code: 'penguin', species_name: 'Пингвин', species_emoji: '🐧' },
  { species_code: 'dragon', species_name: 'Дракон', species_emoji: '🐲' },
  { species_code: 'unicorn', species_name: 'Единорог', species_emoji: '🦄' },
];

const STORAGE_PREFIX = 'zoopark-default-profile-animal-v1:';

type StoredProfileAnimal = { id?: number; species_code?: string };

function storageKey(tgId: number): string {
  return `${STORAGE_PREFIX}${tgId}`;
}

function readStored(tgId: number): StoredProfileAnimal | null {
  try {
    const raw = window.localStorage.getItem(storageKey(tgId));
    if (!raw) return null;
    const value = JSON.parse(raw) as StoredProfileAnimal;
    return typeof value === 'object' && value !== null ? value : null;
  } catch {
    return null;
  }
}

function writeStored(tgId: number, value: StoredProfileAnimal): void {
  try {
    window.localStorage.setItem(storageKey(tgId), JSON.stringify(value));
  } catch {
    // Storage can be unavailable in a restricted Telegram/browser context.
  }
}

function random<T>(items: T[]): T {
  return items[Math.floor(Math.random() * items.length)]!;
}

/**
 * Keep one profile animal stable per player. Owned animals take priority; a catalog
 * animal is used only while the player has not received their first one yet.
 */
export function getDefaultProfileAnimal(tgId: number, animals: Animal[]): ProfileAnimal {
  const stored = readStored(tgId);

  if (animals.length > 0) {
    const owned = typeof stored?.id === 'number' ? animals.find(animal => animal.id === stored.id) : undefined;
    if (owned) return owned;

    const selected = random(animals);
    writeStored(tgId, { id: selected.id });
    return selected;
  }

  const catalogAnimal = DEFAULT_PROFILE_ANIMALS.find(animal => animal.species_code === stored?.species_code);
  if (catalogAnimal) return catalogAnimal;

  const selected = random(DEFAULT_PROFILE_ANIMALS);
  writeStored(tgId, { species_code: selected.species_code });
  return selected;
}
