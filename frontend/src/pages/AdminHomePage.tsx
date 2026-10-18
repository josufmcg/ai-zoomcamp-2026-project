/**
 * Administrator user management page (backlog task 17).
 *
 * The firm-wide property overview has its own route.
 */

import { UsersSection } from "./admin/UsersSection";
import { PageHeading } from "./components";
import { useI18n } from "../i18n/I18nContext";

export function AdminHomePage() {
  const { t } = useI18n();
  return (
    <div className="flex flex-col gap-6">
      <header>
        <PageHeading title="Users" icon="users" />
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          {t("Manage accounts, roles, and access to the platform.")}
        </p>
      </header>

      <UsersSection />
    </div>
  );
}

export default AdminHomePage;
