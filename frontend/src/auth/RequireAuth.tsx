/**
 * Route guarding (backlog task 14).
 *
 * `RequireAuth` wraps a route element and enforces two rules:
 *
 * 1. a signed-out visitor is redirected to `/login`, with the path they asked
 *    for preserved in `location.state.from` so a successful login can return
 *    them there;
 * 2. a signed-in user whose role is not listed in `roles` is redirected to
 *    `/forbidden`.
 *
 * This is a usability guard, never a security boundary: the backend re-checks
 * the role on every request and returns 403 regardless of what the UI shows.
 */

import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "./AuthContext";
import type { UserRole } from "../types/auth";

/** Props for {@link RequireAuth}. */
export interface RequireAuthProps {
  children: ReactNode;
  /** Roles allowed to view the wrapped route. Omit to allow any role. */
  roles?: readonly UserRole[];
}

export function RequireAuth({ children, roles }: RequireAuthProps) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (roles && roles.length > 0 && !roles.includes(user.role)) {
    return <Navigate to="/forbidden" replace />;
  }

  return <>{children}</>;
}

export default RequireAuth;
