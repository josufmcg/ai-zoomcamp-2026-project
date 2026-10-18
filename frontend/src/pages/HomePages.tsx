/**
 * Shared landing and error screens (backlog task 14).
 *
 * The resident, manager, and administrator home screens live in their own
 * modules (`ResidentHomePage.tsx`, `ManagerHomePage.tsx`, `AdminHomePage.tsx`);
 * this file keeps the role-independent overview plus the forbidden and
 * not-found screens.
 */

import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { homePathForRole } from "../auth/navigation";
import { Card, CenteredPanel } from "./components";
import { PageHeading } from "./components";

function OverviewSection() {
  const { user } = useAuth();
  if (!user) {
    return null;
  }

  const tasksByRole = {
    resident: "Manage your properties, bills, maintenance reports, and community votes.",
    manager: "Manage properties, resident assignments, bills, maintenance reports, and community initiatives.",
    administrator: "Your screens manage user accounts and show the global property tree.",
  } as const;

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
        Welcome, {user.email}
      </h2>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
        You are signed in as <strong>{user.role}</strong>. {tasksByRole[user.role]}
      </p>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
        Start at your home screen: <Link className="underline" to={homePathForRole(user.role)}>
          {homePathForRole(user.role)}
        </Link>
        .
      </p>
    </section>
  );
}

export function OverviewPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeading title="Overview" icon="overview" />
      <OverviewSection />
    </div>
  );
}

export function ForbiddenPage() {
  const { user } = useAuth();

  return (
    <CenteredPanel>
      <Card
        title="Not allowed"
        subtitle="Your role does not include this screen."
      >
        <p className="text-sm text-slate-600 dark:text-slate-400">
          {user
            ? `Signed in as ${user.email} (${user.role}).`
            : "You are not signed in."}
        </p>
        <Link
          className="mt-4 inline-block rounded-md bg-rose-800 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-700 dark:bg-rose-700 dark:hover:bg-rose-600"
          to={user ? homePathForRole(user.role) : "/login"}
        >
          Back to my home screen
        </Link>
      </Card>
    </CenteredPanel>
  );
}

export function NotFoundPage() {
  return (
    <CenteredPanel>
      <Card title="Page not found" subtitle="This route does not exist.">
        <Link className="underline" to="/overview">
          Go to the overview
        </Link>
      </Card>
    </CenteredPanel>
  );
}
