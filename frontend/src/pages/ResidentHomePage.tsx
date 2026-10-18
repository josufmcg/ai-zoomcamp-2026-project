/**
 * Resident properties page (backlog task 15).
 *
 * Bills, incidences, and initiatives have their own routes so each growing list
 * can be browsed independently.
 */

import { MyUnitsSection } from "./resident/MyUnitsSection";
import { PageHeading } from "./components";

export function ResidentHomePage() {
  return (
    <div className="flex flex-col gap-6">
      <header>
        <PageHeading title="My properties" icon="units" />
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Apartments, garages, and storage properties linked to you.
        </p>
      </header>

      <MyUnitsSection />
    </div>
  );
}

export default ResidentHomePage;
