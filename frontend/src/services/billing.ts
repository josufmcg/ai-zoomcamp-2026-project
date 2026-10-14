/**
 * Bill calls used by the resident screens (backlog task 15).
 *
 * The list endpoint already scopes the response to the caller's own units and
 * computes the display status, so `listBills` accepts an optional `status`
 * filter (including `overdue`) that the backend applies without changing the
 * stored status.
 */

import { api } from "./apiClient";
import type { Bill, BillDisplayStatus } from "../types/billing";

/** Filters accepted by {@link listBills}. */
export interface ListBillsParams {
  /** Restrict to one of the caller's units. */
  unitId?: number;
  /** Restrict to a display status, including the computed `overdue`. */
  status?: BillDisplayStatus;
}

/** List the bills visible to the caller, optionally filtered. */
export function listBills(params: ListBillsParams = {}): Promise<Bill[]> {
  return api.get<Bill[]>("/bills", {
    query: { unit_id: params.unitId, status: params.status },
  });
}

/** Return one bill the caller may see. */
export function getBill(billId: number): Promise<Bill> {
  return api.get<Bill>(`/bills/${billId}`);
}
