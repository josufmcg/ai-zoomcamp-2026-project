/** Per-unit ballot logic tests (backlog task 15). */

import { describe, expect, it, vi } from "vitest";

import type { EligibleUnit, Vote } from "../../types/governance";
import {
  clearBallot,
  hasPendingBallots,
  pendingBallots,
  setBallot,
  submitBallots,
  votableUnits,
  type BallotSelections,
} from "./ballot";

/** Build an eligible unit, optionally already voted. */
function unit(
  unitId: number,
  overrides: Partial<EligibleUnit> = {},
): EligibleUnit {
  return {
    unit_id: unitId,
    unit_identifier: overrides.unit_identifier ?? `U-${unitId}`,
    unit_type: overrides.unit_type ?? "apartment",
    vote_id: overrides.vote_id ?? null,
    option_id: overrides.option_id ?? null,
  };
}

/** Build a vote response for a submitted ballot. */
function vote(unitId: number, optionId: number): Vote {
  return {
    id: unitId,
    initiative_id: 1,
    option_id: optionId,
    option_label: `Option ${optionId}`,
    unit_id: unitId,
    unit_identifier: `U-${unitId}`,
  };
}

describe("setBallot / clearBallot", () => {
  it("records a choice for a unit without mutating the source", () => {
    const before: BallotSelections = {};
    const after = setBallot(before, 5, 22);

    expect(after).toEqual({ 5: 22 });
    expect(before).toEqual({});
    expect(after).not.toBe(before);
  });

  it("replaces an existing choice for the same unit", () => {
    expect(setBallot({ 5: 22 }, 5, 33)).toEqual({ 5: 33 });
  });

  it("removes a choice and leaves the others", () => {
    expect(clearBallot({ 5: 22, 6: 33 }, 5)).toEqual({ 6: 33 });
  });
});

describe("pendingBallots", () => {
  it("builds one request per selected unit, in eligible order", () => {
    const units = [unit(1), unit(2), unit(3)];
    const selections = { 3: 30, 1: 10 };

    expect(pendingBallots(selections, units)).toEqual([
      { unit_id: 1, option_id: 10 },
      { unit_id: 3, option_id: 30 },
    ]);
  });

  it("skips a unit the resident left unselected", () => {
    const units = [unit(1), unit(2)];
    expect(pendingBallots({ 1: 10 }, units)).toEqual([
      { unit_id: 1, option_id: 10 },
    ]);
  });

  it("never sends a second ballot for a unit that already voted", () => {
    const units = [
      unit(1, { vote_id: 99, option_id: 10 }),
      unit(2),
    ];
    // Unit 1 has a recorded vote, so even a selection for it is ignored.
    expect(pendingBallots({ 1: 20, 2: 30 }, units)).toEqual([
      { unit_id: 2, option_id: 30 },
    ]);
  });

  it("returns nothing when no unit is selected", () => {
    expect(pendingBallots({}, [unit(1), unit(2)])).toEqual([]);
  });
});

describe("votableUnits", () => {
  it("keeps only units without a recorded vote", () => {
    const units = [unit(1), unit(2, { vote_id: 7 }), unit(3)];
    expect(votableUnits(units).map((u) => u.unit_id)).toEqual([1, 3]);
  });
});

describe("hasPendingBallots", () => {
  it("is true when at least one unit is selected", () => {
    expect(hasPendingBallots({ 1: 10 }, [unit(1)])).toBe(true);
  });

  it("is false when the only selected unit already voted", () => {
    expect(
      hasPendingBallots({ 1: 10 }, [unit(1, { vote_id: 5 })]),
    ).toBe(false);
  });
});

describe("submitBallots", () => {
  it("casts one request per pending unit and returns the votes", async () => {
    const units = [unit(1), unit(2), unit(3, { vote_id: 9, option_id: 30 })];
    const cast = vi.fn(async (ballot: { unit_id: number; option_id: number }) =>
      vote(ballot.unit_id, ballot.option_id),
    );

    const votes = await submitBallots({ 1: 10, 2: 20 }, units, cast);

    expect(cast).toHaveBeenCalledTimes(2);
    expect(cast).toHaveBeenNthCalledWith(1, { unit_id: 1, option_id: 10 });
    expect(cast).toHaveBeenNthCalledWith(2, { unit_id: 2, option_id: 20 });
    expect(votes).toEqual([vote(1, 10), vote(2, 20)]);
  });

  it("does not call the API when nothing is pending", async () => {
    const cast = vi.fn();
    await submitBallots({}, [unit(1)], cast);
    expect(cast).not.toHaveBeenCalled();
  });
});
