/**
 * Shared presentational pieces of the application (backlog tasks 14 and 15).
 *
 * Task 14 added the shell-level pieces (card, centered panel, placeholder).
 * Task 15 adds the small building blocks the role screens share: a titled
 * section, status badges, loading/empty/error notices, and an `AsyncSection`
 * that renders the three states of a `useAsync` call so no screen repeats the
 * same branching markup.
 */

import type { ReactNode } from "react";

import type { AsyncState } from "../hooks/useAsync";

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

/** Titled, bordered section used by every feature screen. */
export function SectionCard({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            {title}
          </h2>
          {description && (
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              {description}
            </p>
          )}
        </div>
        {actions && <div className="flex gap-2">{actions}</div>}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

/** A soft-coloured pill used to render a status at a glance. */
export function StatusBadge({
  label,
  tone = "slate",
}: {
  label: string;
  tone?: "slate" | "amber" | "green" | "red" | "blue";
}) {
  const tones = {
    slate:
      "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200",
    amber:
      "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200",
    green:
      "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200",
    red: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200",
    blue: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200",
  } as const;

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}
      data-testid="status-badge"
    >
      {label}
    </span>
  );
}

/** Neutral notice for a loading, empty, or informational state. */
export function Notice({
  children,
  tone = "slate",
}: {
  children: ReactNode;
  tone?: "slate" | "red";
}) {
  const tones = {
    slate:
      "border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-300",
    red: "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/30 dark:text-red-200",
  } as const;

  return (
    <div
      className={`rounded-md border px-3 py-2 text-sm ${tones[tone]}`}
      role={tone === "red" ? "alert" : undefined}
    >
      {children}
    </div>
  );
}

/**
 * Render the three states of a {@link AsyncState}: loading, error, and the
 * loaded value. `render` receives the non-null data, so consumers never repeat
 * the null check.
 */
export function AsyncSection<T>({
  state,
  render,
  emptyMessage,
  isEmpty,
}: {
  state: AsyncState<T>;
  render: (data: T) => ReactNode;
  /** Message shown when the loaded value counts as empty. */
  emptyMessage?: string;
  /** Override the emptiness test for value types where `[]` is not the only case. */
  isEmpty?: (data: T) => boolean;
}) {
  if (state.loading) {
    return <Notice>Loading…</Notice>;
  }
  if (state.error) {
    return <Notice tone="red">{state.error.message}</Notice>;
  }
  if (state.data === null) {
    return <Notice>No data.</Notice>;
  }
  const empty = isEmpty ? isEmpty(state.data) : isEmptyArray(state.data);
  if (empty && emptyMessage) {
    return <Notice>{emptyMessage}</Notice>;
  }
  return <>{render(state.data)}</>;
}

/** Default emptiness test: true for an empty array, false for anything else. */
function isEmptyArray(value: unknown): boolean {
  return Array.isArray(value) && value.length === 0;
}

/** Inline list of a unit's or building's free-text tags. */
export function TagList({ tags }: { tags: readonly { id: number; name: string }[] }) {
  if (tags.length === 0) {
    return null;
  }
  return (
    <ul className="mt-1 flex flex-wrap gap-1" data-testid="tag-list">
      {tags.map((tag) => (
        <li
          key={tag.id}
          className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300"
        >
          #{tag.name}
        </li>
      ))}
    </ul>
  );
}
