import type { Animal, ExpeditionGrade, GeneTier, Habitat, PackTier } from '@/types';

export type GeneKey = 'survival' | 'reproduction' | 'appearance' | 'size_trait';

export const HABITAT_INFO: Record<Habitat, {
  emoji: string;
  name: string;
  color: string;
  expeditionDifficulty: string;
}> = {
  // Landscape icons (not animals) so a habitat never reads as a second creature next
  // to the animal art.
  desert: {
    emoji: '🏜️',
    name: 'Пустыня',
    color: 'var(--c-gold)',
    expeditionDifficulty: 'Средняя',
  },
  mountains: {
    emoji: '⛰️',
    name: 'Горы',
    color: 'var(--tg-theme-hint-color)',
    expeditionDifficulty: 'Высокая',
  },
  forest: {
    emoji: '🌲',
    name: 'Густой лес',
    color: 'var(--c-green)',
    expeditionDifficulty: 'Средняя',
  },
  fields: {
    emoji: '🌾',
    name: 'Поля',
    color: 'var(--c-teal)',
    expeditionDifficulty: 'Низкая',
  },
  antarctica: {
    emoji: '🏔️',
    name: 'Антарктида',
    color: 'var(--c-cyan)',
    expeditionDifficulty: 'Очень высокая',
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

// Тиры паков растут в этом порядке: редкий всегда открыт, каждый следующий открывается
// покупкой предыдущего. Название и цвет живут здесь, потому что тир показывает и витрина
// паков, и калькулятор окупаемости.
export const PACK_TIER_ORDER: PackTier[] = ['rare', 'epic', 'legendary', 'mythic'];

export const PACK_TIER_META: Record<PackTier, { name: string; color: string }> = {
  rare: { name: 'Редкий', color: '#4A9EDD' },
  epic: { name: 'Эпический', color: '#A855F7' },
  legendary: { name: 'Легендарный', color: '#F59E0B' },
  mythic: { name: 'Мифический', color: '#EF4444' },
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

/**
 * One animal's raw combat power, 6 to 18. This is the gene half only — the server also
 * applies the player's forge items and corps level, which `ExpeditionInfo.power_multiplier`
 * carries. Use `squadPower` for the number the fight is actually decided on.
 */
export function expeditionPower(animal: Pick<Animal, 'size_trait' | 'survival' | 'appearance'>): number {
  return (
    COMBAT_TIER_WEIGHT[animal.size_trait] * 3 +
    COMBAT_TIER_WEIGHT[animal.survival] * 2 +
    COMBAT_TIER_WEIGHT[animal.appearance]
  );
}

/** Mirrors `progression.squad_power`: summed gene power, scaled by the player's bonuses. */
export function squadPower(
  animals: Pick<Animal, 'size_trait' | 'survival' | 'appearance'>[],
  powerMultiplier = 1,
): number {
  return Math.trunc(animals.reduce((total, animal) => total + expeditionPower(animal), 0) * powerMultiplier);
}

/**
 * Mirrors `catalog.EXPEDITION_GRADES`. The fight is decided on `squad_power / wild_power`
 * rather than a win/lose threshold, so the player can read how much margin they have before
 * committing — and see that surplus power still buys something.
 */
export const EXPEDITION_GRADE_META: Record<ExpeditionGrade, {
  label: string;
  minRatio: number;
  color: string;
  emoji: string;
  blurb: string;
}> = {
  rout: { label: 'Разгром', minRatio: 0, color: 'var(--c-red)', emoji: '💀', blurb: 'Отряд разбит — одно животное погибнет.' },
  defeat: { label: 'Отступление', minRatio: 0.75, color: 'var(--c-red-soft)', emoji: '🩸', blurb: 'Зверь уйдёт, отряд вернётся потрёпанным.' },
  pyrrhic: { label: 'Тяжёлая победа', minRatio: 0.95, color: 'var(--c-amber)', emoji: '🥵', blurb: 'Захват ценой ранений.' },
  victory: { label: 'Победа', minRatio: 1.15, color: 'var(--c-green)', emoji: '🏆', blurb: 'Чистый захват без потерь.' },
  confident: { label: 'Уверенная победа', minRatio: 1.6, color: 'var(--c-teal)', emoji: '✨', blurb: 'Захват, трофей и шанс улучшить гены добычи.' },
  dominant: { label: 'Доминация', minRatio: 2.2, color: 'var(--c-gold)', emoji: '👑', blurb: 'Двойной трофей, доллары и шанс на второго зверя.' },
};

const GRADES_BY_RATIO = (Object.keys(EXPEDITION_GRADE_META) as ExpeditionGrade[]).sort(
  (a, b) => EXPEDITION_GRADE_META[a].minRatio - EXPEDITION_GRADE_META[b].minRatio,
);

/** The grade a ratio lands in — the same walk the server does. */
export function expeditionGradeFor(ratio: number): ExpeditionGrade {
  let match: ExpeditionGrade = GRADES_BY_RATIO[0];
  for (const grade of GRADES_BY_RATIO) {
    if (ratio >= EXPEDITION_GRADE_META[grade].minRatio) match = grade;
  }
  return match;
}

/** Mirrors `catalog.expedition_gene_upgrade_chance`: what overkill buys, as a fraction. */
export function expeditionGeneUpgradeChance(ratio: number): number {
  return Math.min(Math.max((ratio - 1.2) * 0.35, 0), 0.5);
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
