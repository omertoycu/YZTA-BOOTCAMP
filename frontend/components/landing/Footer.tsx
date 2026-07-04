export function Footer() {
  return (
    <footer className="border-t border-surface-variant px-6 py-10 md:px-12">
      <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 sm:flex-row">
        <span className="text-title-md font-black tracking-tight text-primary">PortföyAI</span>
        <p className="text-body-sm text-text-muted">© {new Date().getFullYear()} PortföyAI. Tüm hakları saklıdır.</p>
      </div>
    </footer>
  );
}
