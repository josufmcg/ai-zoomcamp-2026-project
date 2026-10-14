/**
 * "My units" resident section (backlog task 15).
 *
 * Lists the units assigned to the signed-in resident via `GET /auth/me/units`,
 * showing the ownership flag and the tags so the resident can tell an owned
 * apartment from a rented garage at a glance. A resident can hold several units,
 * so the response is always a list.
 */

import { useCallback } from "react";

import { useAsync } from "../../hooks/useAsync";
import { propertyApi } from "../../services";
import { ownershipLabel, unitTypeLabel } from "../format";
import { AsyncSection, SectionCard, StatusBadge, TagList } from "../components";

export function MyUnitsSection() {
  const loadUnits = useCallback(() => propertyApi.listMyUnits(), []);
  const units = useAsync(loadUnits);

  return (
    <SectionCard
      title="Assigned units"
      description="The apartments, garages, and storage units assigned to you."
    >
      <AsyncSection
        state={units}
        emptyMessage="You have no units assigned yet. Ask your manager to assign one."
        render={(rows) => (
          <ul className="flex flex-col gap-3" data-testid="my-units">
            {rows.map((unit) => (
              <li
                key={unit.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 px-4 py-3 dark:border-slate-700"
              >
                <div>
                  <p className="font-medium text-slate-900 dark:text-slate-100">
                    {unit.identifier}
                  </p>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    {unitTypeLabel(unit.unit_type)}
                    {" · "}
                    {ownershipLabel(unit.ownership_type)}
                  </p>
                  <TagList tags={unit.tags} />
                </div>
                <StatusBadge
                  label={ownershipLabel(unit.ownership_type)}
                  tone={unit.ownership_type === "owner" ? "green" : "blue"}
                />
              </li>
            ))}
          </ul>
        )}
      />
    </SectionCard>
  );
}
