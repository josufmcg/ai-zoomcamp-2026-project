/**
 * Resident home screen (backlog task 15).
 *
 * The single route a resident reaches from the sidebar. It stacks the four
 * resident concerns — units, bills, incidences, and open initiatives — as
 * independent sections, each of which loads its own data through the shared API
 * client and renders its own loading/error/empty state. Keeping them separate
 * means one slow or failing endpoint never blanks the rest of the screen.
 */

import { MyUnitsSection } from "./resident/MyUnitsSection";
import { MyBillsSection } from "./resident/MyBillsSection";
import { MyIncidencesSection } from "./resident/MyIncidencesSection";
import { OpenInitiativesSection } from "./resident/OpenInitiativesSection";

export function ResidentHomePage() {
  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          My units
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Your properties, bills, maintenance incidences, and community votes.
        </p>
      </header>

      <MyUnitsSection />
      <MyBillsSection />
      <MyIncidencesSection />
      <OpenInitiativesSection />
    </div>
  );
}

export default ResidentHomePage;
