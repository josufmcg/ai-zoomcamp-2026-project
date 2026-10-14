/** Tests for the authentication service (backlog task 14). */

import { afterEach, describe, expect, it, vi } from "vitest";

import { login } from "./auth";
import { ApiError } from "./apiClient";
import { jsonResponse } from "../test/helpers";

const PROFILE = {
  id: 7,
  email: "resident@efinges.test",
  role: "resident",
  is_active: true,
};

/** Route mocked responses by path and record every request. */
function mockApi(handlers: Record<string, () => Response>) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input) => {
      const url = String(input);
      for (const [path, handler] of Object.entries(handlers)) {
        if (url.endsWith(path)) {
          return handler();
        }
      }
      throw new Error(`Unexpected request to ${url}`);
    });
}

describe("login", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends the credentials as an OAuth2 form body", async () => {
    const fetchMock = mockApi({
      "/auth/token": () => jsonResponse({ access_token: "jwt-123" }),
      "/auth/me": () => jsonResponse(PROFILE),
    });

    await login("resident@efinges.test", "s3cret-password");

    const init = fetchMock.mock.calls[0][1];
    const headers = init?.headers as Record<string, string>;
    expect(headers["Content-Type"]).toBe("application/x-www-form-urlencoded");
    expect(init?.body).toBe(
      new URLSearchParams({
        username: "resident@efinges.test",
        password: "s3cret-password",
      }).toString(),
    );
  });

  it("reads the profile with the freshly issued token and returns the session", async () => {
    const fetchMock = mockApi({
      "/auth/token": () => jsonResponse({ access_token: "jwt-123" }),
      "/auth/me": () => jsonResponse(PROFILE),
    });

    const session = await login("resident@efinges.test", "s3cret-password");

    expect(session).toEqual({ token: "jwt-123", user: PROFILE });
    const meInit = fetchMock.mock.calls[1][1];
    const meHeaders = meInit?.headers as Record<string, string>;
    expect(meHeaders.Authorization).toBe("Bearer jwt-123");
  });

  it("does not persist anything by itself", async () => {
    mockApi({
      "/auth/token": () => jsonResponse({ access_token: "jwt-123" }),
      "/auth/me": () => jsonResponse(PROFILE),
    });

    await login("resident@efinges.test", "s3cret-password");

    expect(window.localStorage.length).toBe(0);
  });

  it("surfaces a rejected login as an ApiError with status 401", async () => {
    mockApi({
      "/auth/token": () =>
        jsonResponse({ detail: "Incorrect email or password" }, { status: 401 }),
    });

    await expect(login("resident@efinges.test", "wrong")).rejects.toBeInstanceOf(
      ApiError,
    );
    await expect(login("resident@efinges.test", "wrong")).rejects.toMatchObject({
      status: 401,
      message: "Incorrect email or password",
    });
  });

  it("rejects a response that carries no access token", async () => {
    mockApi({
      "/auth/token": () => jsonResponse({ token_type: "bearer" }),
    });

    await expect(login("resident@efinges.test", "pw")).rejects.toThrow(
      /did not return an access token/,
    );
  });
});
