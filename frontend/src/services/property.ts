/**
 * Property calls used by the resident screens (backlog task 15).
 *
 * `GET /auth/me/units` is the resident helper: it returns every unit assigned
 * to the signed-in user, each carrying the ownership flag and its tags. The
 * other resident features (bills, incidences, votes) all key off these units.
 */

import { api } from "./apiClient";
import type { MyUnit } from "../types/property";

/** Return every unit assigned to the signed-in user. */
export function listMyUnits(): Promise<MyUnit[]> {
  return api.get<MyUnit[]>("/auth/me/units");
}
