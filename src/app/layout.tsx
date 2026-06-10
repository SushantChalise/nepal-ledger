import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
import { SiteNav } from '@/components/layout/SiteNav';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

// Note: route pages set their own absolute <title> (e.g. "Pulse — Nepal
// Ledger"), so a template would double the branding. This default applies only
// to pages without their own title (currently Home, Districts).
export const metadata: Metadata = {
  title: 'Nepal Ledger',
  description: "Nepal Ledger tracks whether Nepal's money becomes wealth.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <a
          href="#content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-zinc-900 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
        >
          Skip to content
        </a>
        <SiteNav />
        {/* Each route page renders its own <main> landmark; this wrapper is the
            skip-link target and is intentionally not a <main> to avoid a
            duplicate landmark. */}
        <div id="content" tabIndex={-1} className="flex flex-1 flex-col focus:outline-none">
          {children}
        </div>
      </body>
    </html>
  );
}
