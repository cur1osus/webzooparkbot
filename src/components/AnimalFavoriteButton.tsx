type AnimalFavoriteButtonProps = {
  isFavorite: boolean;
  busy?: boolean;
  onToggle: () => void;
  className?: string;
};

/** The same 44px touch target is used in the zoo grid and the breeding picker. */
export function AnimalFavoriteButton({ isFavorite, busy = false, onToggle, className = '' }: AnimalFavoriteButtonProps) {
  return (
    <button
      type="button"
      aria-label={isFavorite ? 'Убрать из избранного' : 'Добавить в избранное'}
      aria-pressed={isFavorite}
      disabled={busy}
      onClick={event => {
        event.stopPropagation();
        onToggle();
      }}
      className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl border-none text-[21px] leading-none transition-transform active:scale-90 disabled:opacity-50 ${className}`}
      style={{
        color: isFavorite ? 'var(--c-gold)' : 'var(--tg-theme-hint-color)',
        background: isFavorite ? 'color-mix(in srgb, var(--c-gold) 15%, transparent)' : 'color-mix(in srgb, var(--tg-theme-hint-color) 8%, transparent)',
        border: `1px solid ${isFavorite ? 'color-mix(in srgb, var(--c-gold) 45%, transparent)' : 'transparent'}`,
      }}
    >
      <span aria-hidden="true">★</span>
    </button>
  );
}
