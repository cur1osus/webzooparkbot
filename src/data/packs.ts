import type { Animal, GeneTier, Habitat } from '@/types';

export type GeneKey = 'survival' | 'reproduction' | 'appearance' | 'size_trait';

export const HABITAT_INFO: Record<Habitat, {
  emoji: string;
  name: string;
  color: string;
  expeditionDifficulty: string;
  expeditionReward: string;
}> = {
  // Landscape icons (not animals) so a habitat never reads as a second creature next
  // to the animal art.
  desert: {
    emoji: '🏜️',
    name: 'Пустыня',
    color: 'var(--c-gold)',
    expeditionDifficulty: 'Средняя',
    expeditionReward: 'Средний',
  },
  mountains: {
    emoji: '⛰️',
    name: 'Горы',
    color: 'var(--tg-theme-hint-color)',
    expeditionDifficulty: 'Высокая',
    expeditionReward: 'Высокий',
  },
  forest: {
    emoji: '🌲',
    name: 'Густой лес',
    color: 'var(--c-green)',
    expeditionDifficulty: 'Средняя',
    expeditionReward: 'Средний',
  },
  fields: {
    emoji: '🌾',
    name: 'Поля',
    color: 'var(--c-teal)',
    expeditionDifficulty: 'Низкая',
    expeditionReward: 'Низкий',
  },
  antarctica: {
    emoji: '🏔️',
    name: 'Антарктида',
    color: 'var(--c-cyan)',
    expeditionDifficulty: 'Очень высокая',
    expeditionReward: 'Очень высокий',
  },
};

// Collection rarity contributes a meaningful income multiplier on the server. This
// metadata is kept here so the pack-reward tile and animal card read identically.
export const SPECIES_RARITY_META: Record<Animal['species_rarity'], { label: string; color: string }> = {
  rare: { label: 'Редкое', color: '#63C268' },
  epic: { label: 'Эпическое', color: '#C072D8' },
  legendary: { label: 'Легендарное', color: '#F3B53F' },
  mythic: { label: 'Мифическое', color: '#EC7F4A' },
};

export const GENE_META: Record<GeneKey, Record<GeneTier, { label: string; color: string }>> = {
  survival: {
    low: { label: 'Слабый', color: 'var(--c-orange)' },
    medium: { label: 'Обычный', color: 'var(--tg-theme-hint-color)' },
    high: { label: 'Долгожитель', color: 'var(--c-green)' },
  },
  reproduction: {
    low: { label: 'Неохотно', color: 'var(--c-orange)' },
    medium: { label: 'Обычно', color: 'var(--tg-theme-hint-color)' },
    high: { label: 'Активное', color: 'var(--c-green)' },
  },
  appearance: {
    low: { label: 'Уродец', color: 'var(--c-orange)' },
    medium: { label: 'Обычный', color: 'var(--tg-theme-hint-color)' },
    high: { label: 'Привлекательный', color: 'var(--c-gold)' },
  },
  size_trait: {
    low: { label: 'Маленький', color: 'var(--tg-theme-hint-color)' },
    medium: { label: 'Обычный', color: 'var(--tg-theme-hint-color)' },
    high: { label: 'Гигант', color: 'var(--c-gold)' },
  },
};

const COMBAT_TIER_WEIGHT: Record<GeneTier, number> = {
  low: 1,
  medium: 2,
  high: 3,
};

export function geneLabel(key: GeneKey, value: GeneTier): string {
  return GENE_META[key][value].label;
}

export function geneColor(key: GeneKey, value: GeneTier): string {
  return GENE_META[key][value].color;
}

export function expeditionPower(animal: Pick<Animal, 'size_trait' | 'survival' | 'appearance'>): number {
  return (
    COMBAT_TIER_WEIGHT[animal.size_trait] * 3 +
    COMBAT_TIER_WEIGHT[animal.survival] * 2 +
    COMBAT_TIER_WEIGHT[animal.appearance]
  );
}

export function lifeLeft(diesAt: string | null): { label: string; color: string } | null {
  if (!diesAt) return null;
  const ms = new Date(diesAt).getTime() - Date.now();
  if (ms <= 0) return { label: 'Умер', color: 'var(--c-red)' };
  const totalHours = Math.floor(ms / 3_600_000);
  const days = Math.floor(totalHours / 24);
  const hours = totalHours % 24;
  const label = days > 0 ? `${days}д ${hours}ч` : `${Math.max(hours, 1)}ч`;
  const color = totalHours < 24 ? 'var(--c-red)' : totalHours < 48 ? 'var(--c-amber)' : 'var(--c-green)';
  return { label, color };
}

export function formatDurationMinutes(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (m === 0) return `${h} ч`;
  return `${h} ч ${m} мин`;
}
