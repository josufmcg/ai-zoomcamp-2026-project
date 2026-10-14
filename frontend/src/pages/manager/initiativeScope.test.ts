/** Initiative draft and scope tests (backlog task 16). */

import { describe, expect, it } from "vitest";

import {
  buildScope,
  cleanOptions,
  emptyDraft,
  emptyScope,
  isEveryUnit,
  isInitiativeValid,
  toCreatePayload,
  validateInitiative,
  type InitiativeDraft,
} from "./initiativeScope";

/** A valid draft that individual tests override to make it invalid. */
function validDraft(overrides: Partial<InitiativeDraft> = {}): InitiativeDraft {
  return {
    ...emptyDraft("2026-01-01"),
    title: "Bike racks",
    description: "Should we install two bike racks in the courtyard?",
    closesAt: "2026-12-31",
    optionLabels: ["Yes", "No"],
    ...overrides,
  };
}

describe("buildScope", () => {
  it("maps every key of the selection onto the request scope", () => {
    expect(
      buildScope({
        communityIds: [1],
        buildingIds: [2, 3],
        unitTypes: ["garage"],
        tagIds: [4],
      }),
    ).toEqual({
      community_ids: [1],
      building_ids: [2, 3],
      unit_types: ["garage"],
      tag_ids: [4],
    });
  });

  it("produces all four keys even when nothing is selected", () => {
    expect(buildScope(emptyScope())).toEqual({
      community_ids: [],
      building_ids: [],
      unit_types: [],
      tag_ids: [],
    });
  });

  it("copies the arrays so later edits do not leak into the payload", () => {
    const selection = emptyScope();
    const scope = buildScope(selection);
    scope.community_ids.push(99);
    expect(selection.communityIds).toEqual([]);
  });
});

describe("isEveryUnit", () => {
  it("is true for an empty scope", () => {
    expect(isEveryUnit(emptyScope())).toBe(true);
  });

  it("is false as soon as one filter is set", () => {
    expect(isEveryUnit({ ...emptyScope(), unitTypes: ["storage"] })).toBe(false);
    expect(isEveryUnit({ ...emptyScope(), communityIds: [1] })).toBe(false);
  });
});

describe("cleanOptions", () => {
  it("drops blank options and trims the rest", () => {
    expect(cleanOptions([" Yes ", "", "No", "   "])).toEqual(["Yes", "No"]);
  });
});

describe("validateInitiative", () => {
  it("accepts a complete draft", () => {
    expect(validateInitiative(validDraft())).toEqual([]);
  });

  it("requires a title and a description", () => {
    expect(validateInitiative(validDraft({ title: "  " }))).toContain(
      "Title is required.",
    );
    expect(validateInitiative(validDraft({ description: "" }))).toContain(
      "Description is required.",
    );
  });

  it("rejects a close date before the open date", () => {
    const errors = validateInitiative(
      validDraft({ opensAt: "2026-06-01", closesAt: "2026-05-01" }),
    );
    expect(errors).toContain("The close date must not be before the open date.");
  });

  it("requires at least two non-blank options", () => {
    expect(validateInitiative(validDraft({ optionLabels: ["Yes", ""] }))).toContain(
      "Provide at least two options.",
    );
  });

  it("rejects duplicate option labels regardless of case and space", () => {
    expect(
      validateInitiative(validDraft({ optionLabels: ["Yes", " yes "] })),
    ).toContain("Option labels must be unique.");
  });
});

describe("isInitiativeValid", () => {
  it("mirrors the error list", () => {
    expect(isInitiativeValid(validDraft())).toBe(true);
    expect(isInitiativeValid(validDraft({ optionLabels: ["Yes"] }))).toBe(false);
  });
});

describe("toCreatePayload", () => {
  it("builds the exact request body, dropping blank options", () => {
    const draft = validDraft({
      optionLabels: [" Yes ", "No", " "],
      scope: {
        communityIds: [7],
        buildingIds: [],
        unitTypes: ["garage"],
        tagIds: [],
      },
    });

    expect(toCreatePayload(draft)).toEqual({
      title: "Bike racks",
      description: "Should we install two bike racks in the courtyard?",
      opens_at: "2026-01-01",
      closes_at: "2026-12-31",
      options: [{ label: "Yes" }, { label: "No" }],
      scope: {
        community_ids: [7],
        building_ids: [],
        unit_types: ["garage"],
        tag_ids: [],
      },
    });
  });
});
