export interface AviaryDef {
  id: string;
  name: string;
  emoji: string;
  seats: number; // animals per aviary
  price_rub: number;
}

export const AVIARIES: AviaryDef[] = [
  {
    id: 'small',
    name: 'Малый вольер',
    emoji: '🏠',
    seats: 10,
    price_rub: 50000,
  },
  {
    id: 'medium',
    name: 'Средний вольер',
    emoji: '🏡',
    seats: 50,
    price_rub: 500000,
  },
  {
    id: 'large',
    name: 'Большой вольер',
    emoji: '🏰',
    seats: 200,
    price_rub: 3000000,
  },
];

export function getAviaryById(id: string): AviaryDef | undefined {
  return AVIARIES.find(a => a.id === id);
}
