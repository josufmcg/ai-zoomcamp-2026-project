/**
 * Authentication context for the frontend (backlog task 14).
 *
 * The context is created in its own module, separate from the provider
 * component, so tests and non-component code can import `useAuth` without
 * pulling in the whole app shell.
 */

import { createContext, useContext } from "react";

import type { User, UserRole } from "../types/auth";

/** The value every consumer of {@link useAuth} receives. */
export interface AuthContextValue {
  /** The signed-in user, or `null` when signed out. */
  user: User | null;
  /** The signed-in user's JWT, or `null` when signed out. */
  token: string | null;
  /** Convenience flag equivalent to `user !== null`. */
  isAuthenticated: boolean;
  /**
   * Exchange credentials for a session, persist it, and make it current.
   *
   * @throws {ApiError} when the credentials are rejected or the profile cannot
   * be read. Nothing is persisted when it throws.
   */
  signIn: (email: string, password: string) => Promise<User>;
  /** Clear the stored session and sign the user out. */
  signOut: () => void;
  /** True when the signed-in user holds one of the given roles. */
  hasRole: (...roles: UserRole[]) => boolean;
}

/** Context handle. `null` means "no provider above this component". */
export const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Read the current authentication context.
 *
 * @throws {Error} when called outside an `AuthProvider`, which is always a
 * programming mistake rather than a runtime condition worth handling.
 */
export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside an <AuthProvider>.");
  }
  return value;
}
