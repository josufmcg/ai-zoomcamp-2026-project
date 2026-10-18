/**
 * Application shell (backlog task 14).
 *
 * Renders the signed-in chrome: a header with the current identity, a sidebar
 * of role-filtered links, and the routed content. It assumes a signed-in user
 * because every route that uses it is wrapped in `RequireAuth`.
 */

import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { navItemsForRole } from "../auth/navigation";
import { BuildingMark, SectionIcon } from "../components/Icons";

export default function AppShell() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  // The shell is only reached through RequireAuth, so a missing user means the
  // app is misconfigured rather than the visitor being anonymous.
  if (!user) {
    return null;
  }

  const items = navItemsForRole(user.role);

  function handleSignOut() {
    signOut();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen flex-col bg-stone-50 dark:bg-slate-950">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-stone-200 bg-white px-6 py-4 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-3">
          <BuildingMark className="h-10 w-10 shrink-0 text-rose-800" />
          <div>
            <p className="text-lg font-bold tracking-tight text-slate-900 dark:text-slate-100">
              EFINGES
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Residential property management platform
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right text-sm">
            <p className="font-medium text-slate-900 dark:text-slate-100">
              {user.email}
            </p>
            <p
              className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400"
              data-testid="current-role"
            >
              {user.role}
            </p>
          </div>
          <button
            type="button"
            onClick={handleSignOut}
            className="rounded-md border border-stone-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-900 dark:border-slate-700 dark:text-slate-200 dark:hover:border-rose-900 dark:hover:bg-rose-950/40 dark:hover:text-rose-200"
          >
            Sign out
          </button>
        </div>
      </header>

      <div className="flex flex-1 flex-col md:flex-row">
        <nav
          aria-label="Main navigation"
          className="border-b border-stone-200 bg-white px-4 py-4 md:w-56 md:border-b-0 md:border-r dark:border-slate-800 dark:bg-slate-900"
        >
          <ul className="flex flex-wrap gap-2 md:flex-col">
            {items.map((item) => (
              <li key={`${item.to}-${item.label}`}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition ${
                      isActive
                        ? "bg-rose-800 text-white shadow-sm dark:bg-rose-900"
                        : "text-slate-700 hover:bg-rose-50 hover:text-rose-900 dark:text-slate-200 dark:hover:bg-slate-800 dark:hover:text-rose-200"
                    }`
                  }
                >
                  <SectionIcon
                    name={item.icon}
                    className="h-5 w-5 shrink-0"
                  />
                  <span>{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
