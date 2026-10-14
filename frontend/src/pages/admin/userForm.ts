/**
 * Pure form logic for the administrator user screen (backlog task 17).
 *
 * The screen has two shapes of write: creating an account from a small form,
 * and editing one account's role or activation state. Both are reduced here to
 * plain functions over plain data so they can be tested without rendering, and
 * so the two components stay thin. The rules mirror the backend (task 9):
 * passwords are at least eight characters, and an administrator cannot demote
 * or deactivate their own account.
 */

import { USER_ROLES, type User, type UserRole } from "../../types/auth";
import type { UserCreate, UserUpdate } from "../../services/users";

/** Minimum password length, matching the backend `UserCreate` constraint. */
export const MIN_PASSWORD_LENGTH = 8;

/** The editable fields of the create-user form. */
export interface UserDraft {
  email: string;
  password: string;
  role: UserRole;
}

/** A fresh, empty create-user form defaulting to the resident role. */
export function emptyUserDraft(): UserDraft {
  return { email: "", password: "", role: "resident" };
}

/**
 * Check a draft against the client-side rules.
 *
 * Returns a list of human-readable problems; an empty list means the draft is
 * good enough to send. The backend validates again, so this is a fast feedback
 * loop rather than the source of truth.
 */
export function validateUserDraft(draft: UserDraft): string[] {
  const errors: string[] = [];
  const email = draft.email.trim();

  if (!email) {
    errors.push("Enter an email address.");
  } else if (!email.includes("@")) {
    errors.push("Enter a valid email address.");
  }

  if (draft.password.length < MIN_PASSWORD_LENGTH) {
    errors.push(
      `The password must be at least ${MIN_PASSWORD_LENGTH} characters.`,
    );
  }

  if (!USER_ROLES.includes(draft.role)) {
    errors.push("Choose a valid role.");
  }

  return errors;
}

/** Turn a validated draft into the `POST /users` request body. */
export function toCreatePayload(draft: UserDraft): UserCreate {
  return {
    email: draft.email.trim(),
    password: draft.password,
    role: draft.role,
  };
}

/** Build the `PATCH /users/{id}` body that changes only the role. */
export function roleChangePatch(role: UserRole): UserUpdate {
  return { role };
}

/** Build the `PATCH /users/{id}` body that changes only the activation flag. */
export function activeTogglePatch(isActive: boolean): UserUpdate {
  return { is_active: isActive };
}

/**
 * Explain why an administrator may not change the given user's role, or `null`.
 *
 * An administrator who demoted themselves would lock the firm out of user
 * management, so the action is refused — the backend refuses it too.
 */
export function roleChangeBlockedReason(
  actorId: number,
  target: User,
  role: UserRole,
): string | null {
  if (actorId === target.id && role !== "administrator") {
    return "You cannot change your own role.";
  }
  return null;
}

/**
 * Explain why an administrator may not deactivate a user, or `null`.
 *
 * Deactivating the signed-in administrator would end the session's ability to
 * manage accounts, so it is refused here and on the backend.
 */
export function deactivateBlockedReason(
  actorId: number,
  target: User,
): string | null {
  if (actorId === target.id) {
    return "You cannot deactivate your own account.";
  }
  return null;
}
