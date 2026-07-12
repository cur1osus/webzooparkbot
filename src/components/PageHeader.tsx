// The shared identity strip that opens every top-level section (Shop, Lab, Games, More):
// the section's emoji in a tinted rounded square, a display title, and an optional
// one-line description. No background glow — a soft gradient here bleeds past the header
// and gets clipped by the scroll container / tab boxes below, and that hard edge reads as
// a stray line. The only accent is the icon square itself.

export function PageHeader({
  emoji,
  title,
  subtitle,
  accent = 'var(--c-blue-rgb)',
}: {
  emoji: string;
  title: string;
  subtitle?: string;
  // An `r, g, b` triple as a CSS var, e.g. 'var(--c-green-rgb)'. Tints the icon square.
  accent?: string;
}) {
  return (
    <div className="px-[14px]" style={{ paddingTop: 16, paddingBottom: 16 }}>
      <div className="flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-xl grid place-items-center text-[20px] shrink-0"
          style={{ background: `rgba(${accent},0.15)`, border: `1px solid rgba(${accent},0.28)` }}
        >
          {emoji}
        </div>
        <p className="font-display m-0 text-[20px] tracking-tight">{title}</p>
      </div>
      {subtitle && (
        <p
          className="m-0 mt-[6px] text-[13px]"
          style={{ color: 'var(--tg-theme-hint-color)', paddingLeft: 52 }}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}
