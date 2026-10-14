/**
 * Incidence lifecycle helpers for the manager screens (backlog task 16).
 *
 * The lifecycle is strictly forward and one step at a time: *submitted* →
 * *in progress* → *resolved* → *closed*, with *closed* terminal. The backend
 * owns that rule and rejects anything else with 409, but the manager screen
 * should only offer the move the backend will accept, so this module mirrors
 * the rule to decide which button to show.
 *
 * The mirror lives in {@link INCIDENCE_TRANSITIONS} and nowhere else in the
 * frontend, so there is one place to keep in sync with
 * `backend/app/models/maintenance.py`. It is pure data-in/data-out and unit
 * tested without rendering a component.
 */

import type { IncidenceStatus } from "../../types/maintenance";

/**
 * The allowed forward move from each stage, the frontend mirror of the
 * backend's `INCIDENCE_TRANSITIONS`. `closed` maps to an empty list because it
 * is terminal.
 */
export const INCIDENCE_TRANSITIONS: Readonly<
  Record<IncidenceStatus, readonly IncidenceStatus[]>
> = {
  submitted: ["in progress"],
  "in progress": ["resolved"],
  resolved: ["closed"],
  closed: [],
};

/** The stages an incidence at `status` may move to (empty when terminal). */
export function nextStatuses(status: IncidenceStatus): IncidenceStatus[] {
  return [...INCIDENCE_TRANSITIONS[status]];
}

/** True when an incidence at `from` may move directly to `to`. */
export function canTransition(
  from: IncidenceStatus,
  to: IncidenceStatus,
): boolean {
  return INCIDENCE_TRANSITIONS[from].includes(to);
}

/** True when an incidence at `status` cannot advance any further. */
export function isTerminal(status: IncidenceStatus): boolean {
  return INCIDENCE_TRANSITIONS[status].length === 0;
}

/**
 * Human-readable label for the action that reaches `status`.
 *
 * One step of the lifecycle reads as an instruction ("Mark in progress") rather
 * than the bare status name, so the manager button describes what it does.
 */
export function transitionLabel(status: IncidenceStatus): string {
  return `Mark ${status}`;
}

