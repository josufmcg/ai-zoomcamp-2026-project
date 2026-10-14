/**
 * Manager property tree (backlog task 16).
 *
 * Shows every community the manager may read with its buildings and units, all
 * loaded through the shared API client. A manager can add a building to a
 * community, add a unit to a building, and change the tags of either; every
 * mutation refreshes the affected lists so the screen always reflects what the
 * backend stored rather than an optimistic guess.
 *
 * The tree is assembled in memory from three flat lists (`/communities`,
 * `/buildings`, `/units`), because the manager may be assigned to several
 * communities and a single grouping pass is cheaper than a request per
 * community.
 */

import { useCallback, useMemo, useState, type FormEvent } from "react";

import { useAsync } from "../../hooks/useAsync";
import { propertyApi } from "../../services";
import {
  UNIT_TYPES,
  type Building,
  type Community,
  type Tag,
  type Unit,
  type UnitType,
} from "../../types/property";
import { unitTypeLabel } from "../format";
import {
  AsyncSection,
  Notice,
  SectionCard,
  StatusBadge,
  TagList,
} from "../components";
import { TagChecklist, TagEditor } from "./TagChecklist";
import { toggleId } from "./tagSelection";

/** Inline form that creates a building in one community. */
function NewBuildingForm({
  communityId,
  tags,
  onCreated,
}: {
  communityId: number;
  tags: readonly { id: number; name: string }[];
  onCreated: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [tagIds, setTagIds] = useState<number[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || !name.trim()) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await propertyApi.createBuilding({
        community_id: communityId,
        name: name.trim(),
        tag_ids: tagIds,
      });
      setName("");
      setTagIds([]);
      setOpen(false);
      onCreated();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to add building.");
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-sm font-medium text-slate-600 underline hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100"
      >
        Add building
      </button>
    );
  }

  return (
    <form
      className="mt-2 flex flex-col gap-2 rounded-md border border-slate-200 p-3 dark:border-slate-700"
      onSubmit={handleSubmit}
    >
      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
        Building name
        <input
          type="text"
          aria-label="Building name"
          value={name}
          maxLength={200}
          onChange={(event) => setName(event.target.value)}
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
        />
      </label>
      <TagChecklist
        tags={tags}
        selected={tagIds}
        onToggle={(tagId) => setTagIds((current) => toggleId(current, tagId))}
      />
      {error && <Notice tone="red">{error}</Notice>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving || !name.trim()}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
        >
          {saving ? "Adding…" : "Create building"}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

/** Inline form that creates a unit in one building. */
function NewUnitForm({
  buildingId,
  tags,
  onCreated,
}: {
  buildingId: number;
  tags: readonly { id: number; name: string }[];
  onCreated: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [identifier, setIdentifier] = useState("");
  const [unitType, setUnitType] = useState<UnitType>("apartment");
  const [tagIds, setTagIds] = useState<number[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || !identifier.trim()) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await propertyApi.createUnit({
        building_id: buildingId,
        identifier: identifier.trim(),
        unit_type: unitType,
        tag_ids: tagIds,
      });
      setIdentifier("");
      setUnitType("apartment");
      setTagIds([]);
      setOpen(false);
      onCreated();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to add unit.");
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-xs font-medium text-slate-600 underline hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100"
      >
        Add unit
      </button>
    );
  }

  return (
    <form
      className="mt-2 flex flex-col gap-2 rounded-md border border-slate-200 p-3 dark:border-slate-700"
      onSubmit={handleSubmit}
    >
      <div className="grid gap-2 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          Identifier
          <input
            type="text"
            aria-label="Unit identifier"
            value={identifier}
            maxLength={100}
            onChange={(event) => setIdentifier(event.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          Type
          <select
            aria-label="Unit type"
            value={unitType}
            onChange={(event) => setUnitType(event.target.value as UnitType)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          >
            {UNIT_TYPES.map((type) => (
              <option key={type} value={type}>
                {unitTypeLabel(type)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <TagChecklist
        tags={tags}
        selected={tagIds}
        onToggle={(tagId) => setTagIds((current) => toggleId(current, tagId))}
      />
      {error && <Notice tone="red">{error}</Notice>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving || !identifier.trim()}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
        >
          {saving ? "Adding…" : "Create unit"}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

/** Tag-management form used once at the top of the section. */
function NewTagForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || !name.trim()) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await propertyApi.createTag(name.trim());
      setName("");
      onCreated();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to create tag.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="flex flex-wrap items-end gap-2" onSubmit={handleSubmit}>
      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
        New tag
        <input
          type="text"
          aria-label="New tag"
          value={name}
          maxLength={100}
          onChange={(event) => setName(event.target.value)}
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
        />
      </label>
      <button
        type="submit"
        disabled={saving || !name.trim()}
        className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
      >
        {saving ? "Creating…" : "Create tag"}
      </button>
      {error && <Notice tone="red">{error}</Notice>}
    </form>
  );
}

/** One unit row with its tags and a tag editor. */
function UnitRow({
  unit,
  allTags,
  onChanged,
}: {
  unit: Unit;
  allTags: readonly { id: number; name: string }[];
  onChanged: () => void;
}) {
  return (
    <li
      className="rounded-md border border-slate-200 px-3 py-2 dark:border-slate-700"
      data-testid={`unit-${unit.id}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
          {unit.identifier}
        </span>
        <StatusBadge label={unitTypeLabel(unit.unit_type)} tone="blue" />
      </div>
      <TagList tags={unit.tags} />
      <TagEditor
        tags={allTags}
        selectedTagIds={unit.tags.map((tag) => tag.id)}
        onSave={async (tagIds) => {
          await propertyApi.updateUnit(unit.id, { tag_ids: tagIds });
          onChanged();
        }}
        label={unit.identifier}
      />
    </li>
  );
}

export function PropertyTreeSection() {
  const loadCommunities = useCallback(() => propertyApi.listCommunities(), []);
  const communities = useAsync<Community[]>(loadCommunities);
  const loadBuildings = useCallback(() => propertyApi.listBuildings(), []);
  const buildings = useAsync<Building[]>(loadBuildings);
  const loadUnits = useCallback(() => propertyApi.listUnits(), []);
  const units = useAsync<Unit[]>(loadUnits);
  const loadTags = useCallback(() => propertyApi.listTags(), []);
  const tags = useAsync<Tag[]>(loadTags);

  const reloadBuildings = useCallback(() => {
    buildings.reload();
    units.reload();
  }, [buildings, units]);

  const reloadUnits = useCallback(() => units.reload(), [units]);

  const tagsById = useMemo(() => tags.data ?? [], [tags.data]);

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
      title="Property tree"
      description="Your communities, buildings, and units. Add to the tree and label rows with tags."
    >
      <div className="mb-5 border-b border-slate-200 pb-5 dark:border-slate-700">
        <h3 className="mb-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
          Tags
        </h3>
        <NewTagForm onCreated={tags.reload} />
        {tagsById.length > 0 && (
          <div className="mt-3">
            <TagList tags={tagsById} />
          </div>
        )}
      </div>

      <AsyncSection
        state={communities}
        emptyMessage="You are not assigned to any community yet."
        render={(rows) => (
          <ul className="flex flex-col gap-6" data-testid="community-list">
            {rows.map((community) => (
              <li key={community.id} data-testid={`community-${community.id}`}>
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                  {community.name}
                </h3>
                <ul className="mt-2 flex flex-col gap-3" data-testid="building-list">
                  {(buildingsByCommunity.get(community.id) ?? []).map((building) => (
                    <li
                      key={building.id}
                      className="rounded-md border border-slate-200 p-3 dark:border-slate-700"
                      data-testid={`building-${building.id}`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-medium text-slate-900 dark:text-slate-100">
                          {building.name}
                        </span>
                      </div>
                      <TagList tags={building.tags} />
                      <TagEditor
                        tags={tagsById}
                        selectedTagIds={building.tags.map((tag) => tag.id)}
                        onSave={async (tagIds) => {
                          await propertyApi.updateBuilding(building.id, {
                            tag_ids: tagIds,
                          });
                          reloadBuildings();
                        }}
                        label={building.name}
                      />

                      <ul className="mt-3 flex flex-col gap-2" data-testid="unit-list">
                        {(unitsByBuilding.get(building.id) ?? []).map((unit) => (
                          <UnitRow
                            key={unit.id}
                            unit={unit}
                            allTags={tagsById}
                            onChanged={reloadUnits}
                          />
                        ))}
                      </ul>
                      <div className="mt-2">
                        <NewUnitForm
                          buildingId={building.id}
                          tags={tagsById}
                          onCreated={reloadUnits}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
                <div className="mt-2">
                  <NewBuildingForm
                    communityId={community.id}
                    tags={tagsById}
                    onCreated={reloadBuildings}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      />
    </SectionCard>
  );
}

export default PropertyTreeSection;
