/**
 * Administrator user-management calls used by the admin screen (backlog task 17).
 *
 * These wrap the administrator-only `/users` endpoints. Responses are always
 * the public `UserRead` shape, which never carries the password hash, so the
 * type here is the same `User` the rest of the app already uses.
 */

import { api } from "./apiClient";
import type { User, UserRole } from "../types/auth";

/** Filters accepted by {@link listUsers}. */
export interface ListUsersParams {
  role?: UserRole;
  isActive?: boolean;
}

/** Request body for {@link createUser}. */
export interface UserCreate {
  email: string;
  password: string;
  role: UserRole;
}

/**
 * Request body for {@link updateUser}.
 *
 * Every field is optional: a patch can change only the role, only the
 * activation flag, or only the password. An omitted field is left unchanged.
 */
export interface UserUpdate {
  role?: UserRole;
  is_active?: boolean;
  password?: string;
}

/** List accounts, optionally filtered by role or activation state. */
export function listUsers(params: ListUsersParams = {}): Promise<User[]> {
  return api.get<User[]>("/users", {
    query: { role: params.role, is_active: params.isActive },
  });
}

/** Create an account. The backend answers 409 when the email already exists. */
export function createUser(payload: UserCreate): Promise<User> {
  return api.post<User>("/users", payload);
}

/** Change a user's role, activation state, or password. */
export function updateUser(
  userId: number,
  payload: UserUpdate,
): Promise<User> {
  return api.patch<User>(`/users/${userId}`, payload);
}
