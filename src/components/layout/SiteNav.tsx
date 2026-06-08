'use client';

// ---------------------------------------------------------------------------
// SiteNav — shared primary navigation rendered once by the root layout so all
// route pages get it automatically.
//
// Why 'use client': active-link state uses aria-current="page", which needs the
// live pathname. usePathname() is client-only, and there is no stable server-
// safe header carrying the current path in the Next 16 App Router. The markup
// is tiny and static; the route pages themselves stay Server Components.
// ---------------------------------------------------------------------------

import Link from 'next/link';
import { usePathname } from 'next/navigation';

type NavItem = {
  label: string;
  href: string;
};

// Order: Home first, then the lenses, with Fact Ledger (cross-cutting) last.
const NAV_ITEMS: readonly NavItem[] = [
  { label: 'Home', href: '/' },
  { label: 'Pulse', href: '/pulse' },
  { label: 'Money Map', href: '/money-map' },
  { label: 'Trade', href: '/trade' },
  { label: 'Growth', href: '/growth' },
  { label: 'Foreign Aid', href: '/foreign-aid' },
  { label: 'State Enterprises', href: '/state-enterprises' },
  { label: 'Districts', href: '/districts' },
  { label: 'Tourism Rupee', href: '/tourism-rupee' },
  { label: 'Migration', href: '/migration' },
  { label: 'Fact Ledger', href: '/fact-ledger' },
];

/**
 * True when `href` is the active route. Home ('/') matches only the exact path;
 * every other entry matches its path or any nested child (e.g. /districts also
 * highlights on /districts/kathmandu).
 */
function isActive(pathname: string, href: string): boolean {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}

const linkBase =
  'block rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-zinc-950';
const linkActive = 'bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50';
const linkIdle =
  'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-50';

export function SiteNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Primary"
      className="border-b border-zinc-200 bg-white/95 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/95"
    >
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Link
          href="/"
          className="shrink-0 rounded-md text-base font-bold tracking-tight text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:text-zinc-50 dark:focus-visible:ring-offset-zinc-950"
        >
          Nepal Ledger
        </Link>

        {/* Desktop: horizontal links (≥ 640px). */}
        <ul className="hidden flex-wrap items-center gap-1 sm:flex">
          {NAV_ITEMS.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={active ? 'page' : undefined}
                  className={`${linkBase} ${active ? linkActive : linkIdle}`}
                >
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Mobile: CSS-only disclosure menu (< 640px), no extra client JS. */}
        <details className="relative sm:hidden">
          <summary
            aria-label="Toggle navigation menu"
            className="flex cursor-pointer list-none items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:text-zinc-300 dark:hover:bg-zinc-800 dark:focus-visible:ring-offset-zinc-950 [&::-webkit-details-marker]:hidden"
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              className="h-5 w-5"
            >
              <line x1="4" y1="6" x2="20" y2="6" />
              <line x1="4" y1="12" x2="20" y2="12" />
              <line x1="4" y1="18" x2="20" y2="18" />
            </svg>
            Menu
          </summary>
          <ul className="absolute right-0 z-50 mt-2 w-56 max-w-[calc(100vw-2rem)] rounded-lg border border-zinc-200 bg-white p-1 shadow-lg dark:border-zinc-800 dark:bg-zinc-900">
            {NAV_ITEMS.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={active ? 'page' : undefined}
                    className={`${linkBase} ${active ? linkActive : linkIdle}`}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </details>
      </div>
    </nav>
  );
}
