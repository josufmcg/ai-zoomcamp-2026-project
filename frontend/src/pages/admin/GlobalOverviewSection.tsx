/**
 * Administrator global property overview (backlog task 17).
 *
 * A read-only view of the whole property tree: every community with its
 * buildings and units. The administrator is unrestricted by `app/access.py`, so
 * `GET /communities`, `GET /buildings`, and `GET /units` return the entire firm
 * rather than one manager's scope. No mutations are offered here: the property
 * tree is the manager's to maintain, and this screen exists so an administrator
 * can see the firm as a whole.
 *
 * The tree is assembled in memory from the three flat lists, the same way the
 * manager's `PropertyTreeSection` does it.
 */

import { useCallback, useMemo } from "react";

import { useAsync } from "../../hooks/useAsync";
import { propertyApi } from "../../services";
import type { Building, Community, Unit } from "../../types/property";
import { unitTypeLabel } from "../format";
import { AsyncSection, SectionCard, StatusBadge, TagList } from "../components";

/** One unit as a compact inline row. */
function UnitLine({ unit }: { unit: Unit }) {
  return (
    <li
      className="flex flex-wrap items-center gap-2 py-1"
      data-testid={`overview-unit-${unit.id}`}
    >
      <span className="text-sm text-slate-900 dark:text-slate-100">
        {unit.identifier}
      </span>
      <StatusBadge label={unitTypeLabel(unit.unit_type)} tone="blue" />
      <TagList tags={unit.tags} />
    </li>
  );
}

/** One building with its units, or a short note when it has none. */
function BuildingItem({
  building,
  units,
}: {
  building: Building;
  units: readonly Unit[];
}) {
  return (
    <li
      className="rounded-md border border-slate-200 p-3 dark:border-slate-700"
      data-testid={`overview-building-${building.id}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
          {building.name}
        </span>
        <TagList tags={building.tags} />
      </div>
      <ul className="mt-1 border-t border-slate-100 pt-1 dark:border-slate-700/60">
        {units.map((unit) => (
          <UnitLine key={unit.id} unit={unit} />
        ))}
        {units.length === 0 && (
          <li className="py-1 text-sm text-slate-500 dark:text-slate-400">
            No properties.
          </li>
        )}
      </ul>
    </li>
  );
}

export function GlobalOverviewSection() {
  const loadCommunities = useCallback(() => propertyApi.listCommunities(), []);
  const communities = useAsync<Community[]>(loadCommunities);
  const loadBuildings = useCallback(() => propertyApi.listBuildings(), []);
  const buildings = useAsync<Building[]>(loadBuildings);
  const loadUnits = useCallback(() => propertyApi.listUnits(), []);
  const units = useAsync<Unit[]>(loadUnits);

  const buildingsByCommunity = useMemo(() => {
    const grouped = new Map<number, Building[]>();
    for (const building of buildings.data ?? []) {
      const list = grouped.get(building.community_id) ?? [];
      list.push(building);
      grouped.set(building.community_id, list);
    }
    return grouped;
  }, [buildings.data]);

  const unitsByBuilding = useMemo(() => {
    const grouped = new Map<number, Unit[]>();
    for (const unit of units.data ?? []) {
      const list = grouped.get(unit.building_id) ?? [];
      list.push(unit);
      grouped.set(unit.building_id, list);
    }
    return grouped;
  }, [units.data]);

  return (
    <SectionCard
      title="Global property overview"
      description="Every community, building, and property in the firm. Read-only."
    >
      <AsyncSection
        state={communities}
        emptyMessage="No communities have been created yet."
        render={(rows) => (
          <ul className="flex flex-col gap-6" data-testid="overview-community-list">
            {rows.map((community) => {
              const communityBuildings =
                buildingsByCommunity.get(community.id) ?? [];
              return (
                <li
                  key={community.id}
                  data-testid={`overview-community-${community.id}`}
                >
                  <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                    {community.name}
                  </h3>
                  <ul className="mt-2 flex flex-col gap-3">
                    {communityBuildings.map((building) => (
                      <BuildingItem
                        key={building.id}
                        building={building}
                        units={unitsByBuilding.get(building.id) ?? []}
                      />
                    ))}
                    {communityBuildings.length === 0 && (
                      <li className="text-sm text-slate-500 dark:text-slate-400">
                        No buildings.
                      </li>
                    )}
                  </ul>
                </li>
              );
            })}
          </ul>
        )}
      />
    </SectionCard>
  );
}

export default GlobalOverviewSection;
