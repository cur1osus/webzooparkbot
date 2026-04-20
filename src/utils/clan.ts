export const CLAN_SPECIALTIES = [
  { id: 'merchant', label: '🧙 Торговец', desc: 'Скидки у случайного торговца' },
  { id: 'bank', label: '🏦 Банкир', desc: 'Льготный курс обмена в банке' },
  { id: 'forge', label: '⚒️ Кузнец', desc: 'Бонусы к предметам кузницы' },
  { id: 'collector', label: '🦁 Зоолог', desc: 'Бонус к доходу за разнообразие' },
] as const;

export function getClanSpecialtyLabel(specialty: string | null | undefined): string | null {
  if (!specialty) return null;
  return CLAN_SPECIALTIES.find((entry) => entry.id === specialty)?.label ?? specialty;
}
