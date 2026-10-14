/**
 * Administrator user-form logic tests (backlog task 17).
 *
 * Covers the create-user validation and the request-body builders, plus the two
 * self-action guards that mirror the backend rules from task 9.
 */

import { describe, expect, it } from "vitest";

import { makeUser } from "../../test/helpers";
import {
  activeTogglePatch,
  deactivateBlockedReason,
  emptyUserDraft,
  roleChangeBlockedReason,
  roleChangePatch,
  toCreatePayload,
  validateUserDraft,
} from "./userForm";

describe("emptyUserDraft", () => {
  it("starts blank and defaults to the resident role", () => {
    expect(emptyUserDraft()).toEqual({
      email: "",
      password: "",
      role: "resident",
    });
  });
});

describe("validateUserDraft", () => {
  it("accepts a draft with a plausible email and long enough password", () => {
    const problems = validateUserDraft({
      email: "nuevo@efinges.test",
      password: "supersecret",
      role: "manager",
    });
    expect(problems).toEqual([]);
  });

  it("reports a missing email", () => {
    expect(
      validateUserDraft({ email: "  ", password: "supersecret", role: "resident" }),
    ).toContain("Enter an email address.");
  });

  it("reports an email without an @ sign", () => {
    expect(
      validateUserDraft({
        email: "not-an-email",
        password: "supersecret",
        role: "resident",
      }),
    ).toContain("Enter a valid email address.");
  });

  it("reports a password shorter than the backend minimum", () => {
    const problems = validateUserDraft({
      email: "ana@efinges.test",
      password: "short",
      role: "resident",
    });
    expect(problems).toEqual(["The password must be at least 8 characters."]);
  });
});

describe("toCreatePayload", () => {
  it("trims the email and forwards the role and password", () => {
    expect(
      toCreatePayload({
        email: "  ana@efinges.test  ",
        password: "supersecret",
        role: "manager",
      }),
    ).toEqual({
      email: "ana@efinges.test",
      password: "supersecret",
      role: "manager",
    });
  });
});

describe("patch builders", () => {
  it("builds a role-only patch", () => {
    expect(roleChangePatch("manager")).toEqual({ role: "manager" });
  });

  it("builds an activation-only patch", () => {
    expect(activeTogglePatch(false)).toEqual({ is_active: false });
  });
});

describe("self-action guards", () => {
  const actorId = 1;
  const self = makeUser("administrator", { id: actorId });
  const other = makeUser("resident", { id: 2 });

  it("blocks an administrator from changing their own role", () => {
    expect(roleChangeBlockedReason(actorId, self, "manager")).toBe(
      "You cannot change your own role.",
    );
  });

  it("allows an administrator to keep their own administrator role", () => {
    expect(roleChangeBlockedReason(actorId, self, "administrator")).toBeNull();
  });

  it("allows changing another user's role", () => {
    expect(roleChangeBlockedReason(actorId, other, "manager")).toBeNull();
  });

  it("blocks an administrator from deactivating their own account", () => {
    expect(deactivateBlockedReason(actorId, self)).toBe(
      "You cannot deactivate your own account.",
    );
  });

  it("allows deactivating another account", () => {
    expect(deactivateBlockedReason(actorId, other)).toBeNull();
  });
});
