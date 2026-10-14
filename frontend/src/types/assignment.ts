/**
 * Assignment types shared by the frontend (backlog task 16).
 *
 * An assignment links one resident to one unit with an ownership flag. It
 * mirrors the backend `AssignmentRead` schema, which embeds the full user and
 * unit objects so a manager table renders without a second request. The
 * embedded `User` is the same `UserRead` shape used everywhere else, so it
 * never carries the password hash.
 */

import type { User } from "./auth";
import type { OwnershipType, Unit } from "./property";

/** One resident assigned to one unit (backend `AssignmentRead`). */
export interface Assignment {
  id: number;
  user_id: number;
  unit_id: number;
  ownership_type: OwnershipType;
  user: User;
  unit: Unit;
}

/** Narrow an unknown value to an {@link Assignment} that came from the API. */
export function isAssignment(value: unknown): value is Assignment {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  const user = candidate.user as Record<string, unknown> | undefined;
  const unit = candidate.unit as Record<string, unknown> | undefined;
  return (
    typeof candidate.id === "number" &&
    typeof candidate.user_id === "number" &&
    typeof candidate.unit_id === "number" &&
    (candidate.ownership_type === "owner" ||
      candidate.ownership_type === "tenant") &&
    !!user &&
    typeof user.email === "string" &&
    !!unit &&
    typeof unit.identifier === "string"
  );
}
