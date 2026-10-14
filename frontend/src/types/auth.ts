/**
 * Authentication and identity types shared by the frontend (backlog task 14).
 *
 * These mirror the backend contract in `openapi.yaml`: `UserRole` is the exact
 * set of roles the API issues, and `User` matches the `UserRead` schema, which
 * never carries the password hash.
 */

/** The three roles the API defines, as returned by `GET /auth/me`. */
export type UserRole = "administrator" | "manager" | "resident";

/** Every valid role, in the order the backend enum declares them. */
export const USER_ROLES: readonly UserRole[] = [
  "administrator",
  "manager",
  "resident",
];

/** Public profile of a signed-in user (backend `UserRead`). */
export interface User {
  id: number;
  email: string;
  role: UserRole;
  is_active: boolean;
}

/** A signed-in session: the JWT plus the profile it belongs to. */
export interface AuthSession {
  token: string;
  user: User;
}

/** Narrow an unknown value to a {@link UserRole}. */
export function isUserRole(value: unknown): value is UserRole {
  return (
    typeof value === "string" && USER_ROLES.some((role) => role === value)
  );
}

/** Narrow an unknown value to a {@link User} that came from the API. */
export function isUser(value: unknown): value is User {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "number" &&
    typeof candidate.email === "string" &&
    typeof candidate.is_active === "boolean" &&
    isUserRole(candidate.role)
  );
}
