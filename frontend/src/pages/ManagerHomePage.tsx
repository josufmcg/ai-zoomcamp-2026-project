/**
 * Manager home screen (backlog task 16).
 *
 * The single route a manager reaches from the sidebar. It stacks the five
 * manager concerns — the property tree, resident assignments, bills,
 * incidences, and initiatives — as independent sections, each of which loads its
 * own data through the shared API client and renders its own loading, error, and
 * empty state. Keeping them separate means one slow or failing endpoint never
 * blanks the rest of the screen.
 */

import { AssignmentsSection } from "./manager/AssignmentsSection";
import { InitiativesSection } from "./manager/InitiativesSection";
import { ManagerBillsSection } from "./manager/ManagerBillsSection";
import { ManagerIncidencesSection } from "./manager/ManagerIncidencesSection";
import { PropertyTreeSection } from "./manager/PropertyTreeSection";

export function ManagerHomePage() {
  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          My properties
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Your property tree, resident assignments, bills, incidences, and
          community initiatives.
        </p>
      </header>

      <PropertyTreeSection />
      <AssignmentsSection />
      <ManagerBillsSection />
      <ManagerIncidencesSection />
      <InitiativesSection />
    </div>
  );
}

export default ManagerHomePage;
