import { useState } from 'react';
import type { Animal } from '@/types';

// Generated collectible art lives at /animals/<species_code>.png (transparent PNG).
// If a species has no art yet — or the file fails to load — we fall back to its emoji,
// so the UI never shows a broken image and new species work before their art exists.

const artUrl = (code: string) => `/animals/${code}.png`;

export function AnimalArt({
  animal,
  size,
  className,
}: {
  animal: Pick<Animal, 'species_code' | 'species_emoji' | 'species_name'>;
  size: number;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <span
        className={className}
        style={{ fontSize: Math.round(size * 0.82), lineHeight: 1 }}
        aria-hidden
      >
        {animal.species_emoji}
      </span>
    );
  }

  return (
    <img
      src={artUrl(animal.species_code)}
      alt={animal.species_name}
      width={size}
      height={size}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
      className={className}
      style={{ width: size, height: size, objectFit: 'contain', display: 'block' }}
    />
  );
}
