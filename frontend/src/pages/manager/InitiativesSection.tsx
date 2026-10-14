/**
 * Manager initiatives (backlog task 16).
 *
 * Lists every initiative with its options and running ballot counts, and lets a
 * manager create a new one. The draft rules and the request body are built by
 * {@link ./initiativeScope}, so this component only owns the form state and
 * renders the eligibility filters it is handed.
 *
 * The scope is a filter over communities, buildings, unit types, and tags. Its
 * keys combine with AND and leaving them all empty means "every unit", which the
 * screen states explicitly so a manager cannot accidentally target the whole
 * portfolio when they meant one building.
 */

import { useCallback, useMemo, useState, type FormEvent } from "react";

import { useAsync } from "../../hooks/useAsync";
import { governanceApi, propertyApi } from "../../services";
import {
  UNIT_TYPES,
  type Building,
  type Community,
  type Tag,
  type UnitType,
} from "../../types/property";
import type { Initiative, InitiativeOption } from "../../types/governance";
import {
  emptyDraft,
  isEveryUnit,
  isInitiativeValid,
  toCreatePayload,
  validateInitiative,
  type InitiativeDraft,
  type ScopeSelection,
} from "./initiativeScope";
import { unitTypeLabel } from "../format";
import {
  AsyncSection,
  Notice,
  SectionCard,
  StatusBadge,
} from "../components";
import { TagChecklist, toggleId } from "./TagChecklist";

/** Today as an ISO `YYYY-MM-DD` string. */
function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Ballot tally per option for one initiative. */
function OptionTally({ options }: { options: InitiativeOption[] }) {
  return (
    <ul className="mt-3 flex flex-col gap-1" data-testid="initiative-options">
      {options.map((option) => (
        <li
          key={option.id}
          className="flex items-center justify-between rounded bg-slate-50 px-3 py-1.5 text-sm dark:bg-slate-900/40"
        >
          <span className="text-slate-700 dark:text-slate-300">
            {option.label}
          </span>
          <span
            className="font-medium text-slate-900 dark:text-slate-100"
            data-testid={`option-votes-${option.id}`}
          >
            {option.votes}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Read-only summary of an initiative's eligible scope. */
function ScopeSummary({ scope }: { scope: Initiative["scope"] }) {
  const parts: string[] = [];
  if (scope.community_ids.length > 0) {
    parts.push(`communities ${scope.community_ids.join(", ")}`);
  }
  if (scope.building_ids.length > 0) {
    parts.push(`buildings ${scope.building_ids.join(", ")}`);
  }
  if (scope.unit_types.length > 0) {
    parts.push(scope.unit_types.map(unitTypeLabel).join(", "));
  }
  if (scope.tag_ids.length > 0) {
    parts.push(`tags ${scope.tag_ids.join(", ")}`);
  }
  return (
    <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
      Eligible: {parts.length === 0 ? "every unit" : parts.join(" · ")}
    </p>
  );
}

/** The create-initiative form. */
function NewInitiativeForm({ onCreated }: { onCreated: () => void }) {
  const [draft, setDraft] = useState<InitiativeDraft>(() =>
    emptyDraft(todayIso()),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCommunities = useCallback(() => propertyApi.listCommunities(), []);
  const communities = useAsync<Community[]>(loadCommunities);
  const loadBuildings = useCallback(() => propertyApi.listBuildings(), []);
  const buildings = useAsync<Building[]>(loadBuildings);
  const loadTags = useCallback(() => propertyApi.listTags(), []);
  const tags = useAsync<Tag[]>(loadTags);

  const problems = useMemo(() => validateInitiative(draft), [draft]);

  function patch(update: Partial<InitiativeDraft>) {
    setDraft((current) => ({ ...current, ...update }));
  }

  function patchScope(update: Partial<ScopeSelection>) {
    setDraft((current) => ({
      ...current,
      scope: { ...current.scope, ...update },
    }));
  }

  function setOption(index: number, value: string) {
    setDraft((current) => {
      const optionLabels = [...current.optionLabels];
      optionLabels[index] = value;
      return { ...current, optionLabels };
    });
  }

  function addOption() {
    setDraft((current) => ({
      ...current,
      optionLabels: [...current.optionLabels, ""],
    }));
  }

  function removeOption(index: number) {
    setDraft((current) => ({
      ...current,
      optionLabels: current.optionLabels.filter((_, i) => i !== index),
    }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || !isInitiativeValid(draft)) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await governanceApi.createInitiative(toCreatePayload(draft));
      setDraft(emptyDraft(todayIso()));
      onCreated();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to create initiative.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      className="mb-6 flex flex-col gap-3 rounded-md border border-slate-200 p-4 dark:border-slate-700"
      onSubmit={handleSubmit}
    >
      <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
        New initiative
      </h3>
      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
        Title
        <input
          type="text"
          aria-label="Initiative title"
          value={draft.title}
          maxLength={200}
          onChange={(event) => patch({ title: event.target.value })}
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
        Description
        <textarea
          aria-label="Initiative description"
          rows={3}
          value={draft.description}
          maxLength={4000}
          onChange={(event) => patch({ description: event.target.value })}
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
        />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          Opens
          <input
            type="date"
            aria-label="Opens at"
            value={draft.opensAt}
            onChange={(event) => patch({ opensAt: event.target.value })}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          Closes
          <input
            type="date"
            aria-label="Closes at"
            value={draft.closesAt}
            onChange={(event) => patch({ closesAt: event.target.value })}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          />
        </label>
      </div>

      <fieldset>
        <legend className="text-sm font-medium text-slate-700 dark:text-slate-300">
          Options
        </legend>
        <div className="mt-1 flex flex-col gap-2">
          {draft.optionLabels.map((label, index) => (
            <div key={index} className="flex items-center gap-2">
              <input
                type="text"
                aria-label={`Option ${index + 1}`}
                value={label}
                maxLength={200}
                onChange={(event) => setOption(index, event.target.value)}
                className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
              />
              {draft.optionLabels.length > 2 && (
                <button
                  type="button"
                  onClick={() => removeOption(index)}
                  className="text-xs font-medium text-red-700 underline dark:text-red-300"
                >
                  Remove
                </button>
              )}
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={addOption}
          className="mt-2 text-xs font-medium text-slate-600 underline hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100"
        >
          Add option
        </button>
      </fieldset>

      <fieldset className="rounded-md border border-slate-200 p-3 dark:border-slate-700">
        <legend className="px-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          Eligible units
        </legend>
        <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
          {isEveryUnit(draft.scope)
            ? "No filters — every unit is eligible to vote."
            : "Only units matching all of the filters below may vote."}
        </p>
        <div className="flex flex-col gap-3">
          <div>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Communities
            </span>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
              {(communities.data ?? []).map((community) => (
                <label
                  key={community.id}
                  className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300"
                >
                  <input
                    type="checkbox"
                    checked={draft.scope.communityIds.includes(community.id)}
                    onChange={() =>
                      patchScope({
                        communityIds: toggleId(
                          draft.scope.communityIds,
                          community.id,
                        ),
                      })
                    }
                  />
                  {community.name}
                </label>
              ))}
            </div>
          </div>

          <div>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Buildings
            </span>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
              {(buildings.data ?? []).map((building) => (
                <label
                  key={building.id}
                  className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300"
                >
                  <input
                    type="checkbox"
                    checked={draft.scope.buildingIds.includes(building.id)}
                    onChange={() =>
                      patchScope({
                        buildingIds: toggleId(
                          draft.scope.buildingIds,
                          building.id,
                        ),
                      })
                    }
                  />
                  {building.name}
                </label>
              ))}
            </div>
          </div>

          <div>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Unit types
            </span>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
              {UNIT_TYPES.map((type: UnitType) => (
                <label
                  key={type}
                  className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300"
                >
                  <input
                    type="checkbox"
                    checked={draft.scope.unitTypes.includes(type)}
                    onChange={() =>
                      patchScope({
                        unitTypes: toggleId(
                          draft.scope.unitTypes,
                          type,
                        ),
                      })
                    }
                  />
                  {unitTypeLabel(type)}
                </label>
              ))}
            </div>
          </div>

          <TagChecklist
            tags={tags.data ?? []}
            selected={draft.scope.tagIds}
            onToggle={(tagId) =>
              patchScope({ tagIds: toggleId(draft.scope.tagIds, tagId) })
            }
          />
        </div>
      </fieldset>

      {problems.length > 0 && (
        <Notice tone="red">
          <ul className="list-disc pl-5">
            {problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        </Notice>
      )}
      {error && <Notice tone="red">{error}</Notice>}

      <div>
        <button
          type="submit"
          disabled={saving || problems.length > 0}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
        >
          {saving ? "Creating…" : "Create initiative"}
        </button>
      </div>
    </form>
  );
}

export function InitiativesSection() {
  const loadInitiatives = useCallback(() => governanceApi.listInitiatives(), []);
  const initiatives = useAsync<Initiative[]>(loadInitiatives);

  return (
    <SectionCard
      title="Initiatives"
      description="Community votes and their ballot counts. Create one with options and an eligible unit scope."
    >
      <NewInitiativeForm onCreated={initiatives.reload} />

      <AsyncSection
        state={initiatives}
        emptyMessage="No initiatives have been created yet."
        render={(rows) => (
          <ul className="flex flex-col gap-4" data-testid="initiative-list">
            {rows.map((initiative) => (
              <li
                key={initiative.id}
                className="rounded-md border border-slate-200 p-4 dark:border-slate-700"
                data-testid={`initiative-${initiative.id}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-slate-900 dark:text-slate-100">
                      {initiative.title}
                    </p>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      {initiative.opens_at} – {initiative.closes_at}
                    </p>
                    <ScopeSummary scope={initiative.scope} />
                  </div>
                  <StatusBadge
                    label={initiative.is_open ? "Open" : "Closed"}
                    tone={initiative.is_open ? "green" : "slate"}
                  />
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">
                  {initiative.description}
                </p>
                <OptionTally options={initiative.options} />
              </li>
            ))}
          </ul>
        )}
      />
    </SectionCard>
  );
}

export default InitiativesSection;
