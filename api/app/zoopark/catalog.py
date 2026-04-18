from __future__ import annotations


ANIMALS = [
    {"id": "rabbit", "name": "Кролик", "emoji": "🐇", "rarity": "rare", "income": 12, "price": 1100},
    {"id": "mouse", "name": "Мышь", "emoji": "🐭", "rarity": "rare", "income": 77, "price": 7000},
    {"id": "flamingo", "name": "Фламинго", "emoji": "🦩", "rarity": "rare", "income": 209, "price": 21900},
    {"id": "orca", "name": "Косатка", "emoji": "🐳", "rarity": "rare", "income": 465, "price": 56500},
    {"id": "gibbon", "name": "Гиббон", "emoji": "🐒", "rarity": "rare", "income": 890, "price": 108000},
    {"id": "ferret", "name": "Хорёк", "emoji": "🦦", "rarity": "rare", "income": 1500, "price": 182000},
    {"id": "squirrel", "name": "Белка", "emoji": "🐿", "rarity": "rare", "income": 2400, "price": 290000},
    {"id": "penguin", "name": "Пингвин", "emoji": "🐧", "rarity": "rare", "income": 3800, "price": 460000},
    {"id": "turtle", "name": "Черепаха", "emoji": "🐢", "rarity": "rare", "income": 5900, "price": 715000},
    {"id": "parrot", "name": "Попугай", "emoji": "🦜", "rarity": "rare", "income": 9100, "price": 1100000},
    {"id": "dolphin", "name": "Дельфин", "emoji": "🐬", "rarity": "epic", "income": 14000, "price": 1700000},
    {"id": "seal", "name": "Тюлень", "emoji": "🦭", "rarity": "epic", "income": 21000, "price": 2600000},
    {"id": "fox", "name": "Лиса", "emoji": "🦊", "rarity": "epic", "income": 32000, "price": 3900000},
    {"id": "wolf", "name": "Волк", "emoji": "🐺", "rarity": "epic", "income": 49000, "price": 5900000},
    {"id": "bear", "name": "Медведь", "emoji": "🐻", "rarity": "epic", "income": 74000, "price": 9000000},
    {"id": "raccoon", "name": "Енот", "emoji": "🦝", "rarity": "epic", "income": 112000, "price": 13600000},
    {"id": "panda", "name": "Панда", "emoji": "🐼", "rarity": "epic", "income": 170000, "price": 20600000},
    {"id": "elephant", "name": "Слон", "emoji": "🐘", "rarity": "epic", "income": 257000, "price": 31200000},
    {"id": "giraffe", "name": "Жираф", "emoji": "🦒", "rarity": "epic", "income": 388000, "price": 47000000},
    {"id": "zebra", "name": "Зебра", "emoji": "🦓", "rarity": "epic", "income": 586000, "price": 71000000},
    {"id": "lion", "name": "Лев", "emoji": "🦁", "rarity": "mythic", "income": 885000, "price": 107000000},
    {"id": "tiger", "name": "Тигр", "emoji": "🐯", "rarity": "mythic", "income": 1340000, "price": 162000000},
    {"id": "hippo", "name": "Бегемот", "emoji": "🦛", "rarity": "mythic", "income": 2020000, "price": 245000000},
    {"id": "rhino", "name": "Носорог", "emoji": "🦏", "rarity": "mythic", "income": 3050000, "price": 370000000},
    {"id": "camel", "name": "Верблюд", "emoji": "🐪", "rarity": "mythic", "income": 4600000, "price": 558000000},
    {"id": "kangaroo", "name": "Кенгуру", "emoji": "🦘", "rarity": "mythic", "income": 6950000, "price": 843000000},
    {"id": "gorilla", "name": "Горилла", "emoji": "🦍", "rarity": "mythic", "income": 10500000, "price": 1270000000},
    {"id": "whale", "name": "Кит", "emoji": "🐋", "rarity": "mythic", "income": 15800000, "price": 1920000000},
    {"id": "shark", "name": "Акула", "emoji": "🦈", "rarity": "mythic", "income": 23900000, "price": 2900000000},
    {"id": "polar_bear", "name": "Белый медведь", "emoji": "🐻", "rarity": "mythic", "income": 36100000, "price": 4370000000},
    {"id": "dragon", "name": "Дракон", "emoji": "🐲", "rarity": "legendary", "income": 54500000, "price": 6600000000},
    {"id": "unicorn", "name": "Единорог", "emoji": "🦄", "rarity": "legendary", "income": 82300000, "price": 10000000000},
    {"id": "phoenix", "name": "Феникс", "emoji": "🔥", "rarity": "legendary", "income": 124200000, "price": 15000000000},
    {"id": "kraken", "name": "Кракен", "emoji": "🦑", "rarity": "legendary", "income": 187500000, "price": 22700000000},
    {"id": "griffin", "name": "Грифон", "emoji": "🦅", "rarity": "legendary", "income": 283000000, "price": 34300000000},
    {"id": "fenec", "name": "Фенек", "emoji": "🦊", "rarity": "legendary", "income": 427000000, "price": 51700000000},
    {"id": "mammoth", "name": "Мамонт", "emoji": "🦣", "rarity": "legendary", "income": 644000000, "price": 78000000000},
    {"id": "reindeer", "name": "Олень", "emoji": "🦌", "rarity": "legendary", "income": 972000000, "price": 118000000000},
    {"id": "peacock", "name": "Павлин", "emoji": "🦚", "rarity": "legendary", "income": 1467000000, "price": 178000000000},
    {"id": "narwhal", "name": "Нарвал", "emoji": "🐟", "rarity": "legendary", "income": 2213000000, "price": 268000000000},
]

AVIARIES = [
    {"id": "small", "name": "Малый вольер", "emoji": "🏠", "seats": 10, "price": 50000},
    {"id": "medium", "name": "Средний вольер", "emoji": "🏡", "seats": 50, "price": 500000},
    {"id": "large", "name": "Большой вольер", "emoji": "🏰", "seats": 200, "price": 3000000},
]

ANIMAL_BY_ID = {animal["id"]: animal for animal in ANIMALS}
ANIMAL_BY_DB_ID = {index + 1: animal for index, animal in enumerate(ANIMALS)}
ANIMAL_STRING_TO_DB = {animal["id"]: index + 1 for index, animal in enumerate(ANIMALS)}

AVIARY_BY_ID = {aviary["id"]: aviary for aviary in AVIARIES}
AVIARY_BY_DB_ID = {index + 1: aviary for index, aviary in enumerate(AVIARIES)}
AVIARY_STRING_TO_DB = {aviary["id"]: index + 1 for index, aviary in enumerate(AVIARIES)}

RUB_PER_USD = 90
STARS_TO_PAW = 10
DIVERSITY_BONUS_PER_SPECIES = 0.01
