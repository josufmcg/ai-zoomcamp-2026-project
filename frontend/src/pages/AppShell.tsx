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
import { useI18n } from "../i18n/I18nContext";

export default function AppShell() {
  const { user, signOut } = useAuth();
  const { language, setLanguage, t } = useI18n();
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
              {t("Residential property management platform")}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-4">
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
            <span>{t("Language")}</span>
            <select
              aria-label={t("Language")}
              value={language}
              onChange={(event) =>
                setLanguage(event.target.value === "es" ? "es" : "en")
              }
              className="rounded-md border border-stone-300 bg-white px-2 py-1.5 dark:border-slate-700 dark:bg-slate-800"
            >
              <option value="en">{t("English")}</option>
              <option value="es">{t("Español")}</option>
            </select>
          </label>
          <div className="text-right text-sm">
            <p className="font-medium text-slate-900 dark:text-slate-100">
              {user.email}
            </p>
            <p
              className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400"
              data-testid="current-role"
            >
              {t(user.role)}
            </p>
          </div>
          <button
            type="button"
            onClick={handleSignOut}
            className="rounded-md border border-stone-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-900 dark:border-slate-700 dark:text-slate-200 dark:hover:border-rose-900 dark:hover:bg-rose-950/40 dark:hover:text-rose-200"
          >
            {t("Sign out")}
          </button>
        </div>
      </header>

      <div className="flex flex-1 flex-col md:flex-row">
        <nav
          aria-label={t("Main navigation")}
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
                  <span>{t(item.label)}</span>
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
