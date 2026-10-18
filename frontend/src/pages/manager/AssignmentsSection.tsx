/**
 * Manager resident assignments (backlog task 16).
 *
 * Assignments link a resident to a unit. The section lists every assignment in
 * the manager's scope with a remove action, and a form to assign an active
 * resident to one of the manager's units. Residents come from `GET /residents`
 * (a manager-accessible directory, never the administrator-only user list) and
 * units from `GET /units`, which the backend already scopes to the manager's
 * communities.
 */

import { useCallback, useMemo, useState, type FormEvent } from "react";

import { useAsync } from "../../hooks/useAsync";
import { useI18n } from "../../i18n/I18nContext";
import { assignmentApi, propertyApi } from "../../services";
import type { Assignment } from "../../types/assignment";
import type { OwnershipType, Unit } from "../../types/property";
import { ownershipLabel, unitTypeLabel } from "../format";
import {
  AsyncSection,
  Notice,
  SectionCard,
  StatusBadge,
} from "../components";

/** The two ways a resident can hold a unit. */
const OWNERSHIP_TYPES: readonly OwnershipType[] = ["owner", "tenant"];

/** One assignment row with a remove action. */
function AssignmentRow({
  assignment,
  onRemoved,
}: {
  assignment: Assignment;
  onRemoved: () => void;
}) {
  const { t } = useI18n();
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function remove() {
    setRemoving(true);
    setError(null);
    try {
      await assignmentApi.deleteAssignment(assignment.id);
      onRemoved();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to remove assignment.",
      );
    } finally {
      setRemoving(false);
    }
  }

  return (
    <li
      className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 px-4 py-3 dark:border-slate-700"
      data-testid={`assignment-${assignment.id}`}
    >
      <div>
        <p className="font-medium text-slate-900 dark:text-slate-100">
          {assignment.user.email}
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          {assignment.unit.identifier} ({t(unitTypeLabel(assignment.unit.unit_type))})
        </p>
        {error && (
          <div className="mt-1">
            <Notice tone="red">{error}</Notice>
          </div>
        )}
      </div>
      <div className="flex items-center gap-3">
        <StatusBadge
          label={ownershipLabel(assignment.ownership_type)}
          tone={assignment.ownership_type === "owner" ? "green" : "blue"}
        />
        <button
          type="button"
          onClick={remove}
          disabled={removing}
          className="rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-900/30"
        >
          {removing ? t("Removing…") : t("Remove")}
        </button>
      </div>
    </li>
  );
}

export function AssignmentsSection() {
  const { t } = useI18n();
  const loadAssignments = useCallback(() => assignmentApi.listAssignments(), []);
  const assignments = useAsync<Assignment[]>(loadAssignments);
  const loadResidents = useCallback(
    () => assignmentApi.listResidents(true),
    [],
  );
  const residents = useAsync(loadResidents);
  const loadUnits = useCallback(() => propertyApi.listUnits(), []);
  const units = useAsync<Unit[]>(loadUnits);

  const [userId, setUserId] = useState("");
  const [unitId, setUnitId] = useState("");
  const [ownershipType, setOwnershipType] =
    useState<OwnershipType>("owner");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const residentOptions = useMemo(() => residents.data ?? [], [residents.data]);
  const unitOptions = useMemo(() => units.data ?? [], [units.data]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) {
      return;
    }
    const parsedUser = Number(userId);
    const parsedUnit = Number(unitId);
    if (!parsedUser || !parsedUnit) {
      setError(t("Choose a resident and a property."));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await assignmentApi.createAssignment({
        user_id: parsedUser,
        unit_id: parsedUnit,
        ownership_type: ownershipType,
      });
      setUserId("");
      setUnitId("");
      setOwnershipType("owner");
      assignments.reload();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to assign the property.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard
      title={t("Resident assignments")}
      description={t("Link a resident to one of your properties, or remove an existing assignment.")}
    >
      <form
        className="mb-5 grid gap-3 rounded-md border border-slate-200 p-4 sm:grid-cols-3 dark:border-slate-700"
        onSubmit={handleSubmit}
      >
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          {t("Resident")}
          <select
            aria-label={t("Resident")}
            value={userId}
            onChange={(event) => setUserId(event.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          >
            <option value="">{t("Select a resident…")}</option>
            {residentOptions.map((resident) => (
              <option key={resident.id} value={resident.id}>
                {resident.email}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          {t("Property")}
          <select
            aria-label={t("Property")}
            value={unitId}
            onChange={(event) => setUnitId(event.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          >
            <option value="">{t("Select a property…")}</option>
            {unitOptions.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.identifier} ({t(unitTypeLabel(unit.unit_type))})
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          {t("Ownership")}
          <select
            aria-label={t("Ownership")}
            value={ownershipType}
            onChange={(event) =>
              setOwnershipType(event.target.value as OwnershipType)
            }
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          >
            {OWNERSHIP_TYPES.map((type) => (
              <option key={type} value={type}>
                {t(ownershipLabel(type))}
              </option>
            ))}
          </select>
        </label>
        {error && (
          <div className="sm:col-span-3">
            <Notice tone="red">{error}</Notice>
          </div>
        )}
        <div className="sm:col-span-3">
          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
          >
            {saving ? t("Assigning…") : t("Assign resident")}
          </button>
        </div>
      </form>

      <AsyncSection
        state={assignments}
        emptyMessage="No residents are linked to properties yet."
        render={(rows) => (
          <ul className="flex flex-col gap-3" data-testid="assignment-list">
            {rows.map((assignment) => (
              <AssignmentRow
                key={assignment.id}
                assignment={assignment}
                onRemoved={assignments.reload}
              />
            ))}
          </ul>
        )}
      />
    </SectionCard>
  );
}

export default AssignmentsSection;
