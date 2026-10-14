/**
 * Initiative and voting calls used by the resident and manager screens
 * (backlog tasks 15-16).
 *
 * Residents list the open initiatives, ask which of their units are eligible,
 * and cast one ballot per eligible unit. Managers create initiatives, so this
 * module also wraps `POST /initiatives`, whose scope is the eligibility filter
 * the manager builds on screen.
 */

import { api } from "./apiClient";
import type {
  EligibleUnit,
  Initiative,
  InitiativeScope,
  Vote,
  VoteResult,
} from "../types/governance";

/** Filters accepted by {@link listInitiatives}. */
export interface ListInitiativesParams {
  /** Restrict to the initiatives that are currently open for voting. */
  isOpen?: boolean;
}

/** Request body for {@link createInitiative}. */
export interface InitiativeCreate {
  title: string;
  description: string;
  opens_at: string;
  closes_at: string;
  options: { label: string }[];
  scope: InitiativeScope;
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

/** Create an initiative with its options and eligible scope. Manager only. */
export function createInitiative(
  payload: InitiativeCreate,
): Promise<Initiative> {
  return api.post<Initiative>("/initiatives", payload);
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
