/**
 * Authentication provider (backlog task 14).
 *
 * Restores the stored session on first render so a page refresh keeps the user
 * signed in, and exposes `signIn` / `signOut` to the rest of the app. The token
 * itself is always attached to requests by the shared API client; the provider
 * only decides *whether* the UI treats the user as signed in.
 *
 * The restored session is trusted as-is. A token that the server has since
 * invalidated surfaces as an `ApiError` with status 401 on the next API call,
 * which later screens handle by signing the user out.
 */

import { useCallback, useMemo, useState, type ReactNode } from "react";

import { login } from "../services";
import { clearSession, readSession, saveSession } from "../services/session";
import { AuthContext, type AuthContextValue } from "./AuthContext";
import type { AuthSession, User, UserRole } from "../types/auth";

/** Props for {@link AuthProvider}. */
export interface AuthProviderProps {
  children: ReactNode;
  /** Test seam: seed an initial session instead of reading local storage. */
  initialSession?: AuthSession | null;
}

export function AuthProvider({ children, initialSession }: AuthProviderProps) {
  const [session, setSession] = useState<AuthSession | null>(() =>
    initialSession !== undefined ? initialSession : readSession(),
  );

  const signIn = useCallback(
    async (email: string, password: string): Promise<User> => {
      const next = await login(email, password);
      saveSession(next.token, next.user);
      setSession(next);
      return next.user;
    },
    [],
  );

  const signOut = useCallback(() => {
    clearSession();
    setSession(null);
  }, []);

  const value = useMemo<AuthContextValue>(() => {
    const user = session?.user ?? null;
    return {
      user,
      token: session?.token ?? null,
      isAuthenticated: user !== null,
      signIn,
      signOut,
      hasRole: (...roles: UserRole[]) =>
        user !== null && roles.includes(user.role),
    };
  }, [session, signIn, signOut]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
