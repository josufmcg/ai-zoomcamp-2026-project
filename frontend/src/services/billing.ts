/**
 * Bill calls used by the resident and manager screens (backlog tasks 15-16).
 *
 * The list endpoint already scopes the response to the caller's own units (a
 * resident) or the communities they manage (a manager) and computes the
 * display status, so `listBills` accepts an optional `status` filter
 * (including `overdue`) that the backend applies without changing the stored
 * status. Managers additionally issue bills and mark them paid.
 */

import { api } from "./apiClient";
import type { Bill, BillDisplayStatus } from "../types/billing";

/** Filters accepted by {@link listBills}. */
export interface ListBillsParams {
  /** Restrict to one unit. */
  unitId?: number;
  /** Restrict to a display status, including the computed `overdue`. */
  status?: BillDisplayStatus;
}

/** Request body for {@link createBill}. */
export interface BillCreate {
  unit_id: number;
  amount: string;
  description: string;
  issue_date?: string;
  due_date: string;
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

/** Issue a manual bill for a unit the caller manages. */
export function createBill(payload: BillCreate): Promise<Bill> {
  return api.post<Bill>("/bills", payload);
}

/** Mark a bill paid. Manager action; the transition is one-way. */
export function payBill(billId: number): Promise<Bill> {
  return api.post<Bill>(`/bills/${billId}/pay`);
}
