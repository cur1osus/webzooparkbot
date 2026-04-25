export type Rarity = 'common' | 'rare' | 'epic' | 'mythic' | 'legendary';

export interface AnimalDef {
  id: string;
  name: string;
  emoji: string;
  rarity: Rarity;
  income_rub_per_min: number; // base income
  price_rub: number;
}

export const RARITY_LABEL: Record<Rarity, string> = {
  common: 'Обычный',
  rare: 'Редкий',
  epic: 'Эпический',
  mythic: 'Мифический',
  legendary: 'Легендарный',
};

export const RARITY_COLOR: Record<Rarity, string> = {
  common: 'var(--tg-theme-hint-color)',
  rare: 'var(--c-green)',
  epic: 'var(--c-purple)',
  mythic: 'var(--c-orange)',
  legendary: 'var(--c-gold)',
};

export const ANIMALS: AnimalDef[] = [
  { id: 'rabbit',     name: 'Кролик',    emoji: '🐇', rarity: 'rare',      income_rub_per_min: 12,         price_rub: 1100 },
  { id: 'mouse',      name: 'Мышь',      emoji: '🐭', rarity: 'rare',      income_rub_per_min: 77,         price_rub: 7000 },
  { id: 'flamingo',   name: 'Фламинго',  emoji: '🦩', rarity: 'rare',      income_rub_per_min: 209,        price_rub: 21900 },
  { id: 'orca',       name: 'Косатка',   emoji: '🐳', rarity: 'rare',      income_rub_per_min: 465,        price_rub: 56500 },
  { id: 'gibbon',     name: 'Гиббон',    emoji: '🐒', rarity: 'rare',      income_rub_per_min: 890,        price_rub: 108000 },
  { id: 'ferret',     name: 'Хорёк',     emoji: '🦦', rarity: 'rare',      income_rub_per_min: 1500,       price_rub: 182000 },
  { id: 'squirrel',   name: 'Белка',     emoji: '🐿️', rarity: 'rare',      income_rub_per_min: 2400,       price_rub: 290000 },
  { id: 'penguin',    name: 'Пингвин',   emoji: '🐧', rarity: 'rare',      income_rub_per_min: 3800,       price_rub: 460000 },
  { id: 'turtle',     name: 'Черепаха',  emoji: '🐢', rarity: 'rare',      income_rub_per_min: 5900,       price_rub: 715000 },
  { id: 'parrot',     name: 'Попугай',   emoji: '🦜', rarity: 'rare',      income_rub_per_min: 9100,       price_rub: 1100000 },
  { id: 'dolphin',    name: 'Дельфин',   emoji: '🐬', rarity: 'epic',      income_rub_per_min: 14000,      price_rub: 1700000 },
  { id: 'seal',       name: 'Тюлень',    emoji: '🦭', rarity: 'epic',      income_rub_per_min: 21000,      price_rub: 2600000 },
  { id: 'fox',        name: 'Лиса',      emoji: '🦊', rarity: 'epic',      income_rub_per_min: 32000,      price_rub: 3900000 },
  { id: 'wolf',       name: 'Волк',      emoji: '🐺', rarity: 'epic',      income_rub_per_min: 49000,      price_rub: 5900000 },
  { id: 'bear',       name: 'Медведь',   emoji: '🐻', rarity: 'epic',      income_rub_per_min: 74000,      price_rub: 9000000 },
  { id: 'raccoon',    name: 'Енот',      emoji: '🦝', rarity: 'epic',      income_rub_per_min: 112000,     price_rub: 13600000 },
  { id: 'panda',      name: 'Панда',     emoji: '🐼', rarity: 'epic',      income_rub_per_min: 170000,     price_rub: 20600000 },
  { id: 'elephant',   name: 'Слон',      emoji: '🐘', rarity: 'epic',      income_rub_per_min: 257000,     price_rub: 31200000 },
  { id: 'giraffe',    name: 'Жираф',     emoji: '🦒', rarity: 'epic',      income_rub_per_min: 388000,     price_rub: 47000000 },
  { id: 'zebra',      name: 'Зебра',     emoji: '🦓', rarity: 'epic',      income_rub_per_min: 586000,     price_rub: 71000000 },
  { id: 'lion',       name: 'Лев',       emoji: '🦁', rarity: 'mythic',    income_rub_per_min: 885000,     price_rub: 107000000 },
  { id: 'tiger',      name: 'Тигр',      emoji: '🐯', rarity: 'mythic',    income_rub_per_min: 1340000,    price_rub: 162000000 },
  { id: 'hippo',      name: 'Бегемот',   emoji: '🦛', rarity: 'mythic',    income_rub_per_min: 2020000,    price_rub: 245000000 },
  { id: 'rhino',      name: 'Носорог',   emoji: '🦏', rarity: 'mythic',    income_rub_per_min: 3050000,    price_rub: 370000000 },
  { id: 'camel',      name: 'Верблюд',   emoji: '🐪', rarity: 'mythic',    income_rub_per_min: 4600000,    price_rub: 558000000 },
  { id: 'kangaroo',   name: 'Кенгуру',   emoji: '🦘', rarity: 'mythic',    income_rub_per_min: 6950000,    price_rub: 843000000 },
  { id: 'gorilla',    name: 'Горилла',   emoji: '🦍', rarity: 'mythic',    income_rub_per_min: 10500000,   price_rub: 1270000000 },
  { id: 'whale',      name: 'Кит',       emoji: '🐋', rarity: 'mythic',    income_rub_per_min: 15800000,   price_rub: 1920000000 },
  { id: 'shark',      name: 'Акула',     emoji: '🦈', rarity: 'mythic',    income_rub_per_min: 23900000,   price_rub: 2900000000 },
  { id: 'polar_bear', name: 'Белый медведь', emoji: '🐻‍❄️', rarity: 'mythic', income_rub_per_min: 36100000, price_rub: 4370000000 },
  { id: 'dragon',     name: 'Дракон',    emoji: '🐲', rarity: 'legendary', income_rub_per_min: 54500000,   price_rub: 6600000000 },
  { id: 'unicorn',    name: 'Единорог',  emoji: '🦄', rarity: 'legendary', income_rub_per_min: 82300000,   price_rub: 10000000000 },
  { id: 'phoenix',    name: 'Феникс',    emoji: '🔥', rarity: 'legendary', income_rub_per_min: 124200000,  price_rub: 15000000000 },
  { id: 'kraken',     name: 'Кракен',    emoji: '🦑', rarity: 'legendary', income_rub_per_min: 187500000,  price_rub: 22700000000 },
  { id: 'griffin',    name: 'Грифон',    emoji: '🦅', rarity: 'legendary', income_rub_per_min: 283000000,  price_rub: 34300000000 },
  { id: 'fenec',      name: 'Фенек',     emoji: '🦊', rarity: 'legendary', income_rub_per_min: 427000000,  price_rub: 51700000000 },
  { id: 'mammoth',    name: 'Мамонт',    emoji: '🦣', rarity: 'legendary', income_rub_per_min: 644000000,  price_rub: 78000000000 },
  { id: 'reindeer',   name: 'Олень',     emoji: '🦌', rarity: 'legendary', income_rub_per_min: 972000000,  price_rub: 118000000000 },
  { id: 'peacock',    name: 'Павлин',    emoji: '🦚', rarity: 'legendary', income_rub_per_min: 1467000000, price_rub: 178000000000 },
  { id: 'narwhal',    name: 'Нарвал',    emoji: '🐟', rarity: 'legendary', income_rub_per_min: 2213000000, price_rub: 268000000000 },
];

export function getAnimalById(id: string): AnimalDef | undefined {
  return ANIMALS.find(a => a.id === id);
}

export function getAnimalByInfoId(id: number | null | undefined): AnimalDef | undefined {
  return typeof id === 'number' ? ANIMALS[id - 1] : undefined;
}
