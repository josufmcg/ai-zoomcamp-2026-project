/**
 * Landing screens for the three roles (backlog task 14).
 *
 * Each placeholder names the backlog task that fills it in, so the shell can be
 * exercised end to end before the feature work exists. They are deliberately
 * thin: tasks 15 to 17 replace the bodies, not the routes.
 */

import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { homePathForRole } from "../auth/navigation";
import { Card, CenteredPanel, PlaceholderSection } from "./components";

function OverviewSection() {
  const { user } = useAuth();
  if (!user) {
    return null;
  }

  const tasksByRole = {
    resident: "Task 15 adds units, bills, incidences, and open initiatives.",
    manager: "Task 16 adds properties, assignments, bills, incidences, and initiatives.",
    administrator: "Task 17 adds user management and the global property overview.",
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
      <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
        Overview
      </h1>
      <OverviewSection />
    </div>
  );
}

export function ManagerHomePage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
        My properties
      </h1>
      <PlaceholderSection
        title="Manager screens"
        description="Backlog task 16: the assigned property tree with tags, resident assignments, bill issuing, incidence handling, and initiative creation."
      />
    </div>
  );
}

export function AdminHomePage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
        Users
      </h1>
      <PlaceholderSection
        title="Administrator screens"
        description="Backlog task 17: user management (create, change roles, deactivate) and a read-only global property overview."
      />
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
          className="mt-4 inline-block rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
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
