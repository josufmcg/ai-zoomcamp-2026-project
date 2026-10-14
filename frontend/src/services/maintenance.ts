/**
 * Incidence and comment calls used by the resident and manager screens
 * (backlog tasks 15-16).
 *
 * Residents report incidences against their own units, read the thread back,
 * and post comments into it; managers advance the status along the strict
 * lifecycle and comment too. The list endpoint scopes to the caller and embeds
 * each incidence's comment thread, so one request renders the whole screen.
 */

import { api } from "./apiClient";
import type { Comment, Incidence, IncidenceStatus } from "../types/maintenance";

/** Filters accepted by {@link listIncidences}. */
export interface ListIncidencesParams {
  /** Restrict to one unit. */
  unitId?: number;
  /** Restrict to one lifecycle stage. */
  status?: IncidenceStatus;
}

/** Request body for {@link createIncidence}. */
export interface IncidenceCreate {
  unit_id: number;
  title: string;
  description: string;
}

/** List the incidences visible to the caller, optionally filtered. */
export function listIncidences(
  params: ListIncidencesParams = {},
): Promise<Incidence[]> {
  return api.get<Incidence[]>("/incidences", {
    query: { unit_id: params.unitId, status: params.status },
  });
}

/** Report an incidence against one of the caller's own units. */
export function createIncidence(payload: IncidenceCreate): Promise<Incidence> {
  return api.post<Incidence>("/incidences", payload);
}

/** Return one incidence and its comment thread. */
export function getIncidence(incidenceId: number): Promise<Incidence> {
  return api.get<Incidence>(`/incidences/${incidenceId}`);
}

/** Advance an incidence one step along its lifecycle. Manager action. */
export function updateIncidenceStatus(
  incidenceId: number,
  status: IncidenceStatus,
): Promise<Incidence> {
  return api.patch<Incidence>(`/incidences/${incidenceId}/status`, { status });
}

/** Add a comment to an incidence thread. */
export function addComment(
  incidenceId: number,
  body: string,
): Promise<Comment> {
  return api.post<Comment>(`/incidences/${incidenceId}/comments`, { body });
}
