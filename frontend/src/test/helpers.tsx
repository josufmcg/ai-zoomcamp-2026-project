/** Shared helpers for the frontend test suite (backlog task 14). */

import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";

import App from "../App";
import { AuthProvider } from "../auth/AuthProvider";
import { I18nProvider } from "../i18n/I18nProvider";
import type { AuthSession, User, UserRole } from "../types/auth";

/** Build a `Response`-like object for a mocked `fetch`. */
export function jsonResponse(
  body: unknown,
  init: { status?: number } = {},
): Response {
  const status = init.status ?? 200;
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === null ? "" : JSON.stringify(body)),
  } as unknown as Response;
}

/** Build a user profile matching the backend `UserRead` schema. */
export function makeUser(role: UserRole, overrides: Partial<User> = {}): User {
  return {
    id: overrides.id ?? 1,
    email: overrides.email ?? `${role}@efinges.test`,
    role,
    is_active: overrides.is_active ?? true,
  };
}

/** Build a session for the given role. */
export function makeSession(
  role: UserRole,
  overrides: Partial<User> = {},
): AuthSession {
  return { token: "test-token", user: makeUser(role, overrides) };
}

/** Render an element inside a memory router and a seeded auth provider. */
export function renderWithProviders(
  ui: ReactElement,
  session: AuthSession | null,
  route = "/",
) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <I18nProvider>
        <AuthProvider initialSession={session}>{ui}</AuthProvider>
      </I18nProvider>
    </MemoryRouter>,
  );
}

/** Render the whole application at `route` with a seeded session. */
export function renderApp(session: AuthSession | null, route = "/") {
  return renderWithProviders(<App />, session, route);
}
