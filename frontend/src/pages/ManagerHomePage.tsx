/**
 * Manager property tree page (backlog task 16).
 *
 * Assignments, bills, incidences, and initiatives have their own routes so
 * each operational area can grow independently.
 */

import { PropertyTreeSection } from "./manager/PropertyTreeSection";
import { PageHeading } from "./components";

export function ManagerHomePage() {
  return (
    <div className="flex flex-col gap-6">
      <header>
        <PageHeading title="My properties" icon="properties" />
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Manage the communities, buildings, and properties in your portfolio.
        </p>
      </header>

      <PropertyTreeSection />
    </div>
  );
}

export default ManagerHomePage;
