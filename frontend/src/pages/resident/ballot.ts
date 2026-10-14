/**
 * Per-unit ballot selection for the resident voting form (backlog task 15).
 *
 * Voting is **one ballot per eligible owned unit**: a resident owning three
 * eligible units casts three independent ballots, and the backend rejects a
 * second ballot for the same unit. The frontend therefore builds a *selection*
 * per unit while the resident fills the form, and turns it into one vote
 * request per selected unit on submit.
 *
 * Keeping this logic out of the component makes it testable without rendering
 * a form: {@link pendingBallots} is exactly what the submit handler sends, and
 * it deliberately ignores units that already voted.
 */

import type { EligibleUnit, Vote } from "../../types/governance";

/** Map of unit id to the option id the resident picked for that unit. */
export type BallotSelections = Record<number, number>;

/** The request body `POST /initiatives/{id}/votes` expects, one per unit. */
export interface BallotRequest {
  unit_id: number;
  option_id: number;
}

/**
 * Record (or replace) the option chosen for one unit.
 *
 * Returns a new object so React state updates stay immutable.
 */
export function setBallot(
  selections: BallotSelections,
  unitId: number,
  optionId: number,
): BallotSelections {
  return { ...selections, [unitId]: optionId };
}

/** Remove any choice recorded for one unit. */
export function clearBallot(
  selections: BallotSelections,
  unitId: number,
): BallotSelections {
  const next = { ...selections };
  delete next[unitId];
  return next;
}

/**
 * Turn the current selection into the list of ballots still to be cast.
 *
 * A unit is included only when it is eligible, has no recorded vote yet
 * (`vote_id` is `null`) and the resident selected an option for it, so a unit
 * that already voted can never be sent twice and a unit the resident left
 * blank is simply skipped. The order follows `eligibleUnits`, which the backend
 * returns sorted by unit identifier, so the requests are deterministic.
 */
export function pendingBallots(
  selections: BallotSelections,
  eligibleUnits: EligibleUnit[],
): BallotRequest[] {
  return eligibleUnits
    .filter((unit) => unit.vote_id === null && selections[unit.unit_id] !== undefined)
    .map((unit) => ({
      unit_id: unit.unit_id,
      option_id: selections[unit.unit_id],
    }));
}

/** The eligible units that may still receive a ballot. */
export function votableUnits(eligibleUnits: EligibleUnit[]): EligibleUnit[] {
  return eligibleUnits.filter((unit) => unit.vote_id === null);
}

/** True when at least one ballot is ready to submit. */
export function hasPendingBallots(
  selections: BallotSelections,
  eligibleUnits: EligibleUnit[],
): boolean {
  return pendingBallots(selections, eligibleUnits).length > 0;
}

/**
 * Cast every pending ballot for one initiative, one request per unit.
 *
 * `cast` is injected so this stays independent of the API client and can be
 * unit tested; the component passes {@link Vote} casting straight through it.
 */
export async function submitBallots(
  selections: BallotSelections,
  eligibleUnits: EligibleUnit[],
  cast: (ballot: BallotRequest) => Promise<Vote>,
): Promise<Vote[]> {
  const ballots = pendingBallots(selections, eligibleUnits);
  const cast_: Vote[] = [];
  for (const ballot of ballots) {
    cast_.push(await cast(ballot));
  }
  return cast_;
}
