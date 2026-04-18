# Telegram Gifts In Mini App

## Для LLM

Если нужно использовать Telegram gift/NFT-анимации в этом проекте, придерживайся следующих правил.

## Главный вывод

- Для production в Telegram Mini App используй исходный `.tgs`.
- Не используй `.gif` и `.webp` как основной формат для интерфейса игры.
- `.gif/.webp` нужны только как локальный preview для проверки вручную.

Почему именно `.tgs`:

- это исходный Telegram animated sticker формат;
- он уже используется в проекте через `lottie-web`;
- он лучше масштабируется на мобильных экранах;
- он легче и визуально ближе к тому, как Telegram показывает анимацию;
- у `.gif` хуже качество и нет нормальной векторной четкости;
- `.webp` удобен как fallback, но это уже растер, а не исходная анимация.

## Что реально отдает Telegram

Для unique gift Telegram Bot API не отдает готовую "цельную" gift-анимацию одним файлом.

Обычно приходят отдельные части:

- `gift.model.sticker` -> отдельный sticker, часто `.tgs`
- `gift.symbol.sticker` -> отдельный sticker, часто `.tgs`
- `gift.backdrop.colors` -> только цвета фона, не готовая анимация фона

Следствие:

- если в игре нужен визуал "как в Telegram gift-card", его нужно собирать в интерфейсе самостоятельно;
- если нужен только сам animated asset, используй `.tgs` model/symbol отдельно.

## Почему preview выглядел обрезанным

Обрезание в локальном preview не означает, что исходный `.tgs` плохой.

Причины:

- preview рендерился как отдельный sticker-слой, а не как итоговая Telegram gift-композиция;
- Telegram сам дорисовывает карточку и фон отдельно;
- некоторые тени, glow и вылеты на краях выглядят нормально в Telegram, но при грубом raster preview могут казаться подрезанными;
- `.gif/.webp` preview не являются source of truth для production.

Поэтому для игрового интерфейса ориентируйся не на preview, а на исходный `.tgs`.

## Как использовать в этом проекте

В проекте уже есть рабочий паттерн загрузки `.tgs`:

- `src/pages/GamesPage.tsx`
- функции `loadTgs()` и `TelegramTgsPlayer`

Нужно переиспользовать тот же подход:

1. загрузить `.tgs` как binary
2. распаковать gzip через `gunzipSync` из `fflate`
3. распарсить JSON
4. отрендерить через `lottie-web` с `renderer: 'svg'`

Базовый принцип:

```tsx
import lottie from 'lottie-web';
import { gunzipSync } from 'fflate';

async function loadTgs(path: string) {
  const res = await fetch(path);
  const buf = new Uint8Array(await res.arrayBuffer());
  return JSON.parse(new TextDecoder().decode(gunzipSync(buf)));
}
```

## Рекомендации по рендеру

- Используй `renderer: 'svg'`
- Используй `preserveAspectRatio: 'xMidYMid meet'`
- Для контейнера задавай фиксированный размер
- Если по краям визуально режутся glow/тени, не кропай asset, а добавляй внешний padding у контейнера
- Не конвертируй `.tgs` в `.gif` для production

Рекомендуемый контейнер:

```tsx
<div
  style={{
    width: 160,
    height: 160,
    padding: 12,
    boxSizing: 'border-box',
    overflow: 'visible',
  }}
/>
```

Если нужен именно "подарок целиком", а не кусок:

- рендери `model` и `symbol` как отдельные слои;
- фон делай вручную на основе `gift.backdrop.colors`;
- не ожидай, что Telegram даст один готовый файл всей NFT-карточки.

## Что использовать для текущего подарка

Для подарка `Clover Pin` сейчас локально скачаны такие исходники:

- `downloads/media/custom_emoji_5231285319172649536.tgs` -> model (`Sell High`)
- `downloads/media/custom_emoji_5582645495462887434.tgs` -> symbol (`Twin Koi`)

Это правильные production-исходники.

Preview-файлы в `downloads/previews/` не использовать как игровые assets.

## Как переносить в игру

Если решено использовать подарок в интерфейсе игры:

1. скопируй нужные `.tgs` из `downloads/media/` в `public/...` или в папку ассетов фронтенда;
2. рендери их через тот же механизм, что уже используется для Telegram dice анимаций;
3. храни `.tgs` как source of truth;
4. `.gif/.webp` не коммить и не использовать как основной runtime-формат.

## Важно

- `downloads/` локальная папка, она не должна участвовать в деплое;
- production-ассеты нужно класть отдельно, осознанно;
- если LLM добавляет новые gift-анимации, он должен предпочитать `.tgs` и существующий стек `fflate + lottie-web`.
