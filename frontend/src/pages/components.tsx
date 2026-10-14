/** Shared presentational pieces of the application shell (backlog task 14). */

import type { ReactNode } from "react";

/** Centered card used by the login, forbidden, and not-found screens. */
export function Card({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
        {title}
      </h1>
      {subtitle && (
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          {subtitle}
        </p>
      )}
      <div className="mt-5">{children}</div>
    </section>
  );
}

/** Full-height centered layout used by the screens shown without the shell. */
export function CenteredPanel({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-slate-50 p-8 dark:bg-slate-900">
      {children}
    </main>
  );
}

/** Placeholder body for a route that a later backlog task fills in. */
export function PlaceholderSection({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <section
      className="rounded-xl border border-dashed border-slate-300 bg-white/60 p-6 dark:border-slate-600 dark:bg-slate-800/60"
      data-testid="placeholder"
    >
      <h2 className="text-lg font-medium text-slate-900 dark:text-slate-100">
        {title}
      </h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
        {description}
      </p>
    </section>
  );
}
