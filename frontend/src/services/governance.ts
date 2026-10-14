/**
 * Initiative and voting calls used by the resident screens (backlog task 15).
 *
 * The resident voting form is built from three calls: list the open
 * initiatives, ask which of the caller's units are eligible for one, and cast
 * one ballot per eligible unit. `castVote` sends exactly one unit/option pair;
 * the caller issues it once per unit because voting is one ballot per unit.
 */

import { api } from "./apiClient";
import type { EligibleUnit, Initiative, Vote, VoteResult } from "../types/governance";

/** Filters accepted by {@link listInitiatives}. */
export interface ListInitiativesParams {
  /** Restrict to the initiatives that are currently open for voting. */
  isOpen?: boolean;
}

/** List initiatives, optionally limited to the ones open today. */
export function listInitiatives(
  params: ListInitiativesParams = {},
): Promise<Initiative[]> {
  return api.get<Initiative[]>("/initiatives", {
    query: { is_open: params.isOpen },
  });
}

/** Return one initiative with its options and running ballot counts. */
export function getInitiative(initiativeId: number): Promise<Initiative> {
  return api.get<Initiative>(`/initiatives/${initiativeId}`);
}

/**
 * Return the caller's units that may vote in an initiative, each with the
 * ballot already cast (if any) so the form can show it as voted.
 */
export function listEligibleUnits(initiativeId: number): Promise<EligibleUnit[]> {
  return api.get<EligibleUnit[]>(`/initiatives/${initiativeId}/eligible-units`);
}

/** Cast one ballot for one eligible unit. */
export function castVote(
  initiativeId: number,
  unitId: number,
  optionId: number,
): Promise<Vote> {
  return api.post<Vote>(`/initiatives/${initiativeId}/votes`, {
    unit_id: unitId,
    option_id: optionId,
  });
}

/** Return the ballot aggregation for one initiative. */
export function getResults(initiativeId: number): Promise<VoteResult> {
  return api.get<VoteResult>(`/initiatives/${initiativeId}/results`);
}
