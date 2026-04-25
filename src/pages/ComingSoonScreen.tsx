export function ComingSoonScreen() {
  return (
    <div className="min-h-dvh flex items-center justify-center px-6 max-w-[480px] mx-auto">
      <div className="w-full text-center bg-tg-secondary rounded-[20px] py-8 px-6 border" style={{ borderColor: 'var(--surface-overlay-border)' }}>
        <div className="text-[64px] mb-4">🚧</div>
        <p className="m-0 mb-2 text-[22px] font-extrabold">Игра в разработке</p>
        <p className="m-0 text-sm text-tg-hint leading-relaxed">
          Скоро откроемся для всех!<br />Следи за обновлениями.
        </p>
      </div>
    </div>
  );
}
