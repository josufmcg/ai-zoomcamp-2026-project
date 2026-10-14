/** Login flow tests (backlog task 14). */

import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { jsonResponse, renderApp } from "../test/helpers";
import { getToken, TOKEN_STORAGE_KEY, USER_STORAGE_KEY } from "../services";

const PROFILE = {
  id: 3,
  email: "ana@efinges.test",
  role: "manager",
  is_active: true,
};

/** Mock `fetch` for the login call pair, recording the requests. */
function mockLogin(
  tokenStatus = 200,
  profile: unknown = PROFILE,
) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/auth/token")) {
        return tokenStatus === 200
          ? jsonResponse({ access_token: "jwt-from-login" })
          : jsonResponse({ detail: "Incorrect email or password" }, {
              status: tokenStatus,
            });
      }
      if (url.endsWith("/auth/me")) {
        expect((init?.headers as Record<string, string>).Authorization).toBe(
          "Bearer jwt-from-login",
        );
        return jsonResponse(profile);
      }
      throw new Error(`Unexpected request to ${url}`);
    });
}

/** Fill and submit the login form. */
async function submitLogin(
  user: ReturnType<typeof userEvent.setup>,
  email = "ana@efinges.test",
  password = "s3cret-password",
) {
  await user.type(screen.getByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Password"), password);
  await user.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("login page", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("signs in, stores the session, and lands on the role's home screen", async () => {
    const user = userEvent.setup();
    mockLogin();
    renderApp(null, "/login");

    await submitLogin(user);

    expect(
      await screen.findByRole("heading", { name: "My properties" }),
    ).toBeInTheDocument();
    expect(getToken()).toBe("jwt-from-login");
    expect(
      JSON.parse(window.localStorage.getItem(USER_STORAGE_KEY) ?? "null"),
    ).toEqual(PROFILE);
  });

  it("returns the user to the path the guard turned them away from", async () => {
    const user = userEvent.setup();
    mockLogin();
    renderApp(null, "/admin");

    // The guard redirected to /login, keeping /admin as the requested path.
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    await submitLogin(user);

    // The profile says "manager", so /admin stays forbidden, but the path was
    // requested rather than the role-home fallback.
    expect(
      await screen.findByRole("heading", { name: "Not allowed" }),
    ).toBeInTheDocument();
  });

  it("shows a clear message when the credentials are rejected", async () => {
    const user = userEvent.setup();
    mockLogin(401);
    renderApp(null, "/login");

    await submitLogin(user, "ana@efinges.test", "wrong-password");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Incorrect email or password.",
    );
    expect(getToken()).toBeNull();
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
  });

  it("disables the submit button while the request is in flight", async () => {
    const user = userEvent.setup();
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      await gate;
      const url = String(input);
      return url.endsWith("/auth/token")
        ? jsonResponse({ access_token: "jwt-from-login" })
        : jsonResponse(PROFILE);
    });

    renderApp(null, "/login");
    await submitLogin(user);

    expect(screen.getByRole("button", { name: "Signing in…" })).toBeDisabled();

    release?.();
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "My properties" }),
      ).toBeInTheDocument(),
    );
  });
});
