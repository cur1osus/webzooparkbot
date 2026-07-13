export function TextWave({ text }: { text: string }) {
  return (
    <span className="wave">
      {[...text].map((ch, i) => (
        <span key={`${i}-${ch}`} style={{ animationDelay: `${-i * 0.09}s` }}>
          {ch}
        </span>
      ))}
    </span>
  );
}
