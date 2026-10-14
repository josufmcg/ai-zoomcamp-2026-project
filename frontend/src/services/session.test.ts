/** Tests for session persistence (backlog task 14). */

import { afterEach, describe, expect, it, vi } from "vitest";

import { getToken, TOKEN_STORAGE_KEY } from "./apiClient";
import {
  clearSession,
  readSession,
  saveSession,
  USER_STORAGE_KEY,
} from "./session";
import { makeSession, makeUser } from "../test/helpers";

describe("session storage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("saves both halves of the session and reads them back", () => {
    const session = makeSession("manager", { id: 4, email: "m@efinges.test" });

    saveSession(session.token, session.user);

    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBe("test-token");
    expect(readSession()).toEqual(session);
  });

  it("returns null when signed out", () => {
    expect(readSession()).toBeNull();
  });

  it("discards a stored token that has no profile", () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, "orphan-token");

    expect(readSession()).toBeNull();
  });

  it("discards a malformed profile and clears the token", () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, "jwt");
    window.localStorage.setItem(USER_STORAGE_KEY, "{not json");

    expect(readSession()).toBeNull();
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
  });

  it("discards a profile that does not match the API contract", () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, "jwt");
    window.localStorage.setItem(
      USER_STORAGE_KEY,
      JSON.stringify({ id: 1, email: "a@b.test", role: "superuser", is_active: true }),
    );

    expect(readSession()).toBeNull();
    expect(window.localStorage.getItem(USER_STORAGE_KEY)).toBeNull();
  });

  it("clears both keys on sign out", () => {
    saveSession("jwt", makeUser("resident"));

    clearSession();

    expect(readSession()).toBeNull();
    expect(getToken()).toBeNull();
    expect(window.localStorage.getItem(USER_STORAGE_KEY)).toBeNull();
  });

  it("degrades gracefully when storage is unavailable", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("storage disabled");
    });

    expect(readSession()).toBeNull();
  });
});
