import Link from "next/link";

export default function Nav() {
  return (
    <header className="sticky top-0 z-20 border-b border-soft bg-cream/85 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-2xl bg-teal text-lg font-extrabold text-white shadow-soft">
            R
          </span>
          <span className="text-lg font-extrabold tracking-tight">Resumate</span>
        </Link>
        <div className="flex items-center gap-2">
          <Link
            href="/dashboard"
            className="rounded-full px-4 py-2 text-sm font-semibold text-smoke transition hover:bg-white hover:text-ink"
          >
            Dashboard
          </Link>
          <Link
            href="/submit"
            className="rounded-full bg-teal px-5 py-2 text-sm font-bold text-white shadow-soft transition hover:bg-teal-hover"
          >
            New review
          </Link>
        </div>
      </nav>
    </header>
  );
}
