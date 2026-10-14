/**
 * Session persistence for the frontend (backlog task 14).
 *
 * The JWT is the credential and lives in local storage under the key owned by
 * the API client (`efinges.token`), because that is the only header the client
 * attaches. The user profile is stored next to it so a page refresh can rebuild
 * the session without a round trip.
 *
 * A session is only valid when both halves are present: if the stored profile is
 * missing or malformed the token is discarded, so a half-written session can
 * never leave the UI signed in without knowing its role.
 */

import { isUser, type AuthSession, type User } from "../types/auth";
import { clearToken, setToken, TOKEN_STORAGE_KEY } from "./apiClient";

/** Local storage key holding the serialized user profile. */
export const USER_STORAGE_KEY = "efinges.user";

/** Read the stored session, or `null` when the user is signed out. */
export function readSession(): AuthSession | null {
  let token: string | null = null;
  let rawUser: string | null = null;
  try {
    token = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    rawUser = window.localStorage.getItem(USER_STORAGE_KEY);
  } catch {
    // Storage can be unavailable (private mode, SSR); treat as signed out.
    return null;
  }

  if (!token || !rawUser) {
    return null;
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(rawUser);
  } catch {
    clearSession();
    return null;
  }

  if (!isUser(parsed)) {
    clearSession();
    return null;
  }

  return { token, user: parsed };
}

/** Persist the token and profile so later requests are authenticated. */
export function saveSession(token: string, user: User): void {
  setToken(token);
  try {
    window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  } catch {
    // Ignore storage failures; the provider still holds the session in memory.
  }
}

/** Remove the token and profile, signing the user out. */
export function clearSession(): void {
  clearToken();
  try {
    window.localStorage.removeItem(USER_STORAGE_KEY);
  } catch {
    // Nothing to do if storage is unavailable.
  }
}
