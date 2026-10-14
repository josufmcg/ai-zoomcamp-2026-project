/**
 * Authentication calls against the EFINGES API (backlog task 14).
 *
 * `POST /auth/token` is the one endpoint that reads an OAuth2 form body
 * (`username` is the email) instead of JSON, so the request goes through the
 * shared client's `form` option. The returned JWT is then used to read the
 * profile, which is what the UI actually needs to pick the right screens.
 */

import { api } from "./apiClient";
import type { AuthSession, User } from "../types/auth";

/** Response body of `POST /auth/token`. */
interface TokenResponse {
  access_token: string;
  token_type?: string;
}

/**
 * Exchange credentials for a JWT and the matching profile.
 *
 * Nothing is persisted here: the caller decides when the session becomes
 * current, which keeps this function pure and easy to test.
 *
 * @throws {ApiError} when the credentials are rejected (401) or `/auth/me`
 * fails.
 */
export async function login(email: string, password: string): Promise<AuthSession> {
  const tokenResponse = await api.post<TokenResponse>(
    "/auth/token",
    undefined,
    {
      form: { username: email, password },
      skipAuth: true,
    },
  );

  const token = tokenResponse?.access_token;
  if (typeof token !== "string" || !token) {
    throw new Error("The server did not return an access token.");
  }

  // `/auth/me` needs the fresh token, which is not stored yet, so it is passed
  // explicitly instead of relying on the client's automatic Bearer header.
  const user = await api.get<User>("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });

  return { token, user };
}
