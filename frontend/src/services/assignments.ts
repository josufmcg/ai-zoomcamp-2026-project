/**
 * Assignment and resident-directory calls used by the manager screens
 * (backlog task 16).
 *
 * Assignments link a resident to a unit. Managers list them to see who holds
 * what, create one to assign a resident, and remove one to free the unit. The
 * resident picker needs the resident *directory*, which `GET /residents`
 * provides to managers without exposing the administrator-only user management
 * endpoints.
 */

import { api } from "./apiClient";
import type { Assignment } from "../types/assignment";
import type { User } from "../types/auth";
import type { OwnershipType } from "../types/property";

/** Filters accepted by {@link listAssignments}. */
export interface ListAssignmentsParams {
  userId?: number;
  unitId?: number;
}

/** Request body for {@link createAssignment}. */
export interface AssignmentCreate {
  user_id: number;
  unit_id: number;
  ownership_type: OwnershipType;
}

/** List resident accounts so a manager can pick whom to assign. */
export function listResidents(isActive?: boolean): Promise<User[]> {
  return api.get<User[]>("/residents", { query: { is_active: isActive } });
}

/** List assignments, optionally filtered by resident or unit. */
export function listAssignments(
  params: ListAssignmentsParams = {},
): Promise<Assignment[]> {
  return api.get<Assignment[]>("/assignments", {
    query: { user_id: params.userId, unit_id: params.unitId },
  });
}

/** Assign one resident to one unit. */
export function createAssignment(
  payload: AssignmentCreate,
): Promise<Assignment> {
  return api.post<Assignment>("/assignments", payload);
}

/** Remove an assignment (the resident loses access to that unit). */
export function deleteAssignment(assignmentId: number): Promise<void> {
  return api.delete<void>(`/assignments/${assignmentId}`);
}
