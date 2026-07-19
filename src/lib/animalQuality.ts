import type { Animal, GeneTier } from '@/types';

/**
 * «Качество» животного — редкость вида плюс уровень генов, одной осью.
 * Редкость главнее: внутри одной редкости животные упорядочены по сумме генов.
 * Используется и в «Мои животные», и в пикере родителей на скрещивании.
 */

// Порядок повторяет доходность вида: редкое ×0,9, эпическое ×1,0, мифическое ×1,1,
// легендарное ×1,2 — поэтому легендарное стоит выше мифического.
export const RARITY_RANK: Record<Animal['species_rarity'], number> = {
  rare: 0, epic: 1, mythic: 2, legendary: 3,
};

const GENE_TIER_INDEX: Record<GeneTier, number> = { low: 0, medium: 1, high: 2 };
const GENE_KEYS = ['survival', 'reproduction', 'appearance', 'size_trait'] as const;

/** Суммарный уровень генов, 0–8. */
export function geneScore(animal: Animal): number {
  return GENE_KEYS.reduce((acc, key) => acc + GENE_TIER_INDEX[animal[key]], 0);
}

/** Лучшие первыми: сначала редкость, потом гены, потом доход как стабильный тай-брейк. */
export function compareByQuality(a: Animal, b: Animal): number {
  return RARITY_RANK[b.species_rarity] - RARITY_RANK[a.species_rarity]
    || geneScore(b) - geneScore(a)
    || b.income - a.income;
}
