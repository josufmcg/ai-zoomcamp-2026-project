/**
 * Bill types shared by the frontend (backlog task 15).
 *
 * `Bill` mirrors the backend `BillRead` schema. `status` is the *display*
 * status: the stored `pending`/`paid` value, or `overdue` when a pending bill
 * is past its due date. The backend computes it at serialization time and never
 * rewrites the stored status, so the frontend must never derive it from dates
 * itself — it renders what the API reported.
 */

import type { UnitType } from "./property";

/** The status a client sees: the stored status, or `overdue` (backend `BillDisplayStatus`). */
export type BillDisplayStatus = "pending" | "paid" | "overdue";

/** Every display status, in the order the backend enum declares them. */
export const BILL_DISPLAY_STATUSES: readonly BillDisplayStatus[] = [
  "pending",
  "paid",
  "overdue",
];

/** A bill for one unit (backend `BillRead`). */
export interface Bill {
  id: number;
  unit_id: number;
  unit_identifier: string;
  unit_type: UnitType;
  /** Money as a decimal string, e.g. `"125.50"`; never a float. */
  amount: string;
  description: string;
  /** ISO date `YYYY-MM-DD`. */
  issue_date: string;
  /** ISO date `YYYY-MM-DD`. */
  due_date: string;
  status: BillDisplayStatus;
}

/** Narrow an unknown value to a {@link BillDisplayStatus}. */
export function isBillDisplayStatus(
  value: unknown,
): value is BillDisplayStatus {
  return (
    typeof value === "string" &&
    BILL_DISPLAY_STATUSES.some((status) => status === value)
  );
}
