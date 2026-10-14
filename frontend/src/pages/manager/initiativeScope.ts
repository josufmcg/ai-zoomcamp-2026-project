/**
 * Initiative draft rules for the manager screens (backlog task 16).
 *
 * A manager builds an initiative on screen: a title, a description, an open and
 * a close date, two or more options, and an eligibility scope. The backend
 * enforces every one of those rules, but the manager screen should catch a
 * mistake before it becomes a 422, so this module validates the draft and turns
 * it into the exact request body `POST /initiatives` expects.
 *
 * The scope is a filter over communities, buildings, unit types, and tags; its
 * keys combine with AND and an entirely empty scope means "every unit", which
 * is why {@link buildScope} always returns all four keys as arrays.
 *
 * Everything here is a pure function, so the rules are unit tested without
 * rendering the form.
 */

import type { UnitType } from "../../types/property";
import type { InitiativeScope } from "../../types/governance";
import type { InitiativeCreate } from "../../services/governance";

/** The scope checkboxes the manager form keeps while editing. */
export interface ScopeSelection {
  communityIds: number[];
  buildingIds: number[];
  unitTypes: UnitType[];
  tagIds: number[];
}

/** An empty scope: no filter, which the backend reads as "every unit". */
export function emptyScope(): ScopeSelection {
  return { communityIds: [], buildingIds: [], unitTypes: [], tagIds: [] };
}

/** The initiative fields the manager edits as an in-progress draft. */
export interface InitiativeDraft {
  title: string;
  description: string;
  opensAt: string;
  closesAt: string;
  /** One entry per option row; blanks are ignored when building the payload. */
  optionLabels: string[];
  scope: ScopeSelection;
}

/** A draft with sensible defaults: today opens, two blank options, all units. */
export function emptyDraft(today: string): InitiativeDraft {
  return {
    title: "",
    description: "",
    opensAt: today,
    closesAt: today,
    optionLabels: ["", ""],
    scope: emptyScope(),
  };
}

/** Turn the on-screen scope selection into the request's scope object. */
export function buildScope(selection: ScopeSelection): InitiativeScope {
  return {
    community_ids: [...selection.communityIds],
    building_ids: [...selection.buildingIds],
    unit_types: [...selection.unitTypes],
    tag_ids: [...selection.tagIds],
  };
}

/** True when an empty scope would apply, i.e. every unit may vote. */
export function isEveryUnit(selection: ScopeSelection): boolean {
  return (
    selection.communityIds.length === 0 &&
    selection.buildingIds.length === 0 &&
    selection.unitTypes.length === 0 &&
    selection.tagIds.length === 0
  );
}

/** The option labels with blanks removed and surrounding space trimmed. */
export function cleanOptions(labels: string[]): string[] {
  return labels.map((label) => label.trim()).filter((label) => label.length > 0);
}

/**
 * Validate a draft, returning a list of human-readable problems.
 *
 * An empty list means the draft is ready to submit. The rules mirror the
 * backend's `InitiativeCreate` validator so a valid draft can never be rejected
 * for a reason the form could have caught.
 */
export function validateInitiative(draft: InitiativeDraft): string[] {
  const errors: string[] = [];

  if (!draft.title.trim()) {
    errors.push("Title is required.");
  }
  if (!draft.description.trim()) {
    errors.push("Description is required.");
  }
  if (!draft.opensAt) {
    errors.push("An open date is required.");
  }
  if (!draft.closesAt) {
    errors.push("A close date is required.");
  }
  if (draft.opensAt && draft.closesAt && draft.closesAt < draft.opensAt) {
    errors.push("The close date must not be before the open date.");
  }

  const options = cleanOptions(draft.optionLabels);
  if (options.length < 2) {
    errors.push("Provide at least two options.");
  }
  const lowered = options.map((label) => label.toLowerCase());
  if (new Set(lowered).size !== lowered.length) {
    errors.push("Option labels must be unique.");
  }

  return errors;
}

/** True when {@link validateInitiative} found no problems. */
export function isInitiativeValid(draft: InitiativeDraft): boolean {
  return validateInitiative(draft).length === 0;
}

/**
 * Turn a valid draft into the `POST /initiatives` request body.
 *
 * Blank options are dropped, so a manager may leave a spare row empty without
 * sending it. Callers should validate first; this does not re-check the rules.
 */
export function toCreatePayload(draft: InitiativeDraft): InitiativeCreate {
  return {
    title: draft.title.trim(),
    description: draft.description.trim(),
    opens_at: draft.opensAt,
    closes_at: draft.closesAt,
    options: cleanOptions(draft.optionLabels).map((label) => ({ label })),
    scope: buildScope(draft.scope),
  };
}
