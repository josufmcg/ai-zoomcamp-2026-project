/** Incidence lifecycle transition tests (backlog task 16). */

import { describe, expect, it } from "vitest";

import { INCIDENCE_STATUSES, type IncidenceStatus } from "../../types/maintenance";
import {
  canTransition,
  isTerminal,
  nextStatuses,
  transitionLabel,
} from "./incidenceStatus";

describe("nextStatuses", () => {
  it("advances one step at a time through the lifecycle", () => {
    expect(nextStatuses("submitted")).toEqual(["in progress"]);
    expect(nextStatuses("in progress")).toEqual(["resolved"]);
    expect(nextStatuses("resolved")).toEqual(["closed"]);
  });

  it("treats closed as terminal", () => {
    expect(nextStatuses("closed")).toEqual([]);
  });

  it("returns a fresh array so callers cannot mutate the table", () => {
    const first = nextStatuses("submitted");
    first.push("closed");
    expect(nextStatuses("submitted")).toEqual(["in progress"]);
  });
});

describe("canTransition", () => {
  it("allows only the immediate next stage", () => {
    expect(canTransition("submitted", "in progress")).toBe(true);
    expect(canTransition("in progress", "resolved")).toBe(true);
    expect(canTransition("resolved", "closed")).toBe(true);
  });

  it("rejects skipping ahead", () => {
    expect(canTransition("submitted", "resolved")).toBe(false);
    expect(canTransition("submitted", "closed")).toBe(false);
  });

  it("rejects going backwards", () => {
    expect(canTransition("in progress", "submitted")).toBe(false);
    expect(canTransition("closed", "resolved")).toBe(false);
  });

  it("rejects every move out of a terminal incidence", () => {
    for (const status of INCIDENCE_STATUSES) {
      expect(canTransition("closed", status)).toBe(false);
    }
  });
});

describe("isTerminal", () => {
  it("is true only for closed", () => {
    const terminal = INCIDENCE_STATUSES.filter((status) => isTerminal(status));
    expect(terminal).toEqual(["closed"]);
  });
});

describe("transitionLabel", () => {
  it("describes the action rather than the bare status", () => {
    expect(transitionLabel("in progress")).toBe("Mark in progress");
    expect(transitionLabel("resolved")).toBe("Mark resolved");
    expect(transitionLabel("closed")).toBe("Mark closed");
  });
});

describe("the lifecycle table", () => {
  it("covers every declared status", () => {
    for (const status of INCIDENCE_STATUSES) {
      expect(() => nextStatuses(status)).not.toThrow();
    }
  });

  it("only ever points at a declared status", () => {
    for (const status of INCIDENCE_STATUSES) {
      for (const next of nextStatuses(status)) {
        expect(INCIDENCE_STATUSES).toContain(next as IncidenceStatus);
      }
    }
  });
});
