import type { ReactNode } from "react";

import { GlobalOverviewSection } from "./admin/GlobalOverviewSection";
import { AssignmentsSection } from "./manager/AssignmentsSection";
import { InitiativesSection } from "./manager/InitiativesSection";
import { ManagerBillsSection } from "./manager/ManagerBillsSection";
import { ManagerIncidencesSection } from "./manager/ManagerIncidencesSection";
import { MyBillsSection } from "./resident/MyBillsSection";
import { MyIncidencesSection } from "./resident/MyIncidencesSection";
import { OpenInitiativesSection } from "./resident/OpenInitiativesSection";
import { PageHeading } from "./components";
import type { NavIconName } from "../auth/navigation";

function SectionPage({
  title,
  icon,
  description,
  children,
}: {
  title: string;
  icon: NavIconName;
  description: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-6">
      <header>
        <PageHeading title={title} icon={icon} />
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          {description}
        </p>
      </header>
      {children}
    </div>
  );
}

export function ResidentBillsPage() {
  return (
    <SectionPage
      title="Bills"
      icon="bills"
      description="Review bills issued for the properties linked to you."
    >
      <MyBillsSection />
    </SectionPage>
  );
}

export function ResidentIncidencesPage() {
  return (
    <SectionPage
      title="Maintenance"
      icon="incidences"
      description="Report maintenance issues and follow their progress."
    >
      <MyIncidencesSection />
    </SectionPage>
  );
}

export function ResidentInitiativesPage() {
  return (
    <SectionPage
      title="Community voting"
      icon="initiatives"
      description="Review community initiatives and cast your eligible votes."
    >
      <OpenInitiativesSection />
    </SectionPage>
  );
}

export function ManagerAssignmentsPage() {
  return (
    <SectionPage
      title="Assignments"
      icon="assignments"
      description="Link residents to properties and manage existing assignments."
    >
      <AssignmentsSection />
    </SectionPage>
  );
}

export function ManagerBillsPage() {
  return (
    <SectionPage
      title="Bill management"
      icon="bills"
      description="Issue bills for your properties and keep payment statuses up to date."
    >
      <ManagerBillsSection />
    </SectionPage>
  );
}

export function ManagerIncidencesPage() {
  return (
    <SectionPage
      title="Maintenance"
      icon="incidences"
      description="Review maintenance reports, reply, and update their status."
    >
      <ManagerIncidencesSection />
    </SectionPage>
  );
}

export function ManagerInitiativesPage() {
  return (
    <SectionPage
      title="Community initiatives"
      icon="initiatives"
      description="Create community initiatives and review their ballots."
    >
      <InitiativesSection />
    </SectionPage>
  );
}

export function AdminPropertiesPage() {
  return (
    <SectionPage
      title="Global overview"
      icon="properties"
      description="Browse all communities, buildings, and properties across the firm."
    >
      <GlobalOverviewSection />
    </SectionPage>
  );
}
