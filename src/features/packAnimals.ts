import type { GeneTier, Habitat, PackAnimal } from '../types';

export type GeneKey = 'survival' | 'reproduction' | 'appearance' | 'size_trait';

export const HABITAT_INFO: Record<Habitat, {
  emoji: string;
  name: string;
  color: string;
  expeditionDifficulty: string;
  expeditionReward: string;
}> = {
  desert: {
    emoji: '🐪',
    name: 'Пустыня',
    color: '#ffd60a',
    expeditionDifficulty: 'Средняя',
    expeditionReward: 'Средний',
  },
  mountains: {
    emoji: '🦅',
    name: 'Горы',
    color: '#8f95ab',
    expeditionDifficulty: 'Высокая',
    expeditionReward: 'Высокий',
  },
  forest: {
    emoji: '🐆',
    name: 'Густой лес',
    color: '#34c759',
    expeditionDifficulty: 'Средняя',
    expeditionReward: 'Средний',
  },
  fields: {
    emoji: '🐴',
    name: 'Поля',
    color: '#30d5c8',
    expeditionDifficulty: 'Низкая',
    expeditionReward: 'Низкий',
  },
  antarctica: {
    emoji: '🐧',
    name: 'Антарктида',
    color: '#5ac8fa',
    expeditionDifficulty: 'Очень высокая',
    expeditionReward: 'Очень высокий',
  },
};

export const GENE_META: Record<GeneKey, Record<GeneTier, { label: string; color: string }>> = {
  survival: {
    low: { label: 'Слабый', color: '#ff6b3d' },
    medium: { label: 'Обычный', color: '#8f95ab' },
    high: { label: 'Долгожитель', color: '#34c759' },
  },
  reproduction: {
    low: { label: 'Неохотно', color: '#ff6b3d' },
    medium: { label: 'Обычно', color: '#8f95ab' },
    high: { label: 'Активное', color: '#34c759' },
  },
  appearance: {
    low: { label: 'Уродец', color: '#ff6b3d' },
    medium: { label: 'Обычный', color: '#8f95ab' },
    high: { label: 'Привлекательный', color: '#ffd60a' },
  },
  size_trait: {
    low: { label: 'Маленький', color: '#8f95ab' },
    medium: { label: 'Обычный', color: '#8f95ab' },
    high: { label: 'Гигант', color: '#ffd60a' },
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

export function expeditionPower(animal: Pick<PackAnimal, 'size_trait' | 'survival' | 'appearance'>): number {
  return (
    COMBAT_TIER_WEIGHT[animal.size_trait] * 3 +
    COMBAT_TIER_WEIGHT[animal.survival] * 2 +
    COMBAT_TIER_WEIGHT[animal.appearance]
  );
}

export function lifeLeft(diesAt: string | null): { label: string; color: string } | null {
  if (!diesAt) return null;
  const ms = new Date(diesAt).getTime() - Date.now();
  if (ms <= 0) return { label: 'Умер', color: '#ff3b30' };
  const totalHours = Math.floor(ms / 3_600_000);
  const days = Math.floor(totalHours / 24);
  const hours = totalHours % 24;
  const label = days > 0 ? `${days}д ${hours}ч` : `${Math.max(hours, 1)}ч`;
  const color = totalHours < 24 ? '#ff3b30' : totalHours < 48 ? '#ff9f0a' : '#34c759';
  return { label, color };
}

export function formatDurationMinutes(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (m === 0) return `${h} ч`;
  return `${h} ч ${m} мин`;
}
