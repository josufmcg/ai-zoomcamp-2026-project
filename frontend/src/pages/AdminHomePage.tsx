/**
 * Administrator home screen (backlog task 17).
 *
 * The single route an administrator reaches from the sidebar. It stacks the two
 * administrator concerns — user management and a read-only view of the whole
 * property tree — as independent sections, each loading its own data through
 * the shared API client so one failing endpoint never blanks the other.
 */

import { GlobalOverviewSection } from "./admin/GlobalOverviewSection";
import { UsersSection } from "./admin/UsersSection";

export function AdminHomePage() {
  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          Users
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Manage accounts and roles, and see every community in the firm.
        </p>
      </header>

      <UsersSection />
      <GlobalOverviewSection />
    </div>
  );
}

export default AdminHomePage;
