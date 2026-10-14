/**
 * Bill status filter for the resident screens (backlog task 15).
 *
 * The status shown on a bill — including ``overdue`` — is computed by the
 * backend from the due date, so this module only ever *selects* rows by the
 * status the API already reported. It never derives a status from dates, which
 * would risk disagreeing with the server about what "overdue" means.
 *
 * The filter is a pure function so it can be unit tested without a component.
 */

import type { Bill, BillDisplayStatus } from "../../types/billing";
import { BILL_DISPLAY_STATUSES } from "../../types/billing";

/** Any filter the resident bill list offers: every bill, or one status. */
export type BillFilter = "all" | BillDisplayStatus;

/** The filters in display order, with "All" first. */
export const BILL_FILTERS: readonly BillFilter[] = [
  "all",
  ...BILL_DISPLAY_STATUSES,
];

/** Human-readable label for a filter. */
export function billFilterLabel(filter: BillFilter): string {
  switch (filter) {
    case "all":
      return "All";
    case "pending":
      return "Pending";
    case "paid":
      return "Paid";
    case "overdue":
      return "Overdue";
  }
}

/** Narrow an unknown value to a {@link BillFilter}. */
export function isBillFilter(value: unknown): value is BillFilter {
  return (
    typeof value === "string" &&
    BILL_FILTERS.some((filter) => filter === value)
  );
}

/**
 * Return the bills that match `filter`.
 *
 * `"all"` returns the list untouched (but as a new array, so callers can sort
 * or slice it without mutating the source). Any other filter keeps only the
 * bills whose `status` equals it, which is what makes the computed `overdue`
 * status selectable exactly like the stored `pending` and `paid` ones.
 */
export function filterBills(bills: Bill[], filter: BillFilter): Bill[] {
  if (filter === "all") {
    return [...bills];
  }
  return bills.filter((bill) => bill.status === filter);
}

/** Count the bills per filter, for the "All (3) / Overdue (1)" tab labels. */
export function countBillsByFilter(
  bills: Bill[],
): Record<BillFilter, number> {
  const counts = {
    all: bills.length,
    pending: 0,
    paid: 0,
    overdue: 0,
  } satisfies Record<BillFilter, number>;
  for (const bill of bills) {
    counts[bill.status] += 1;
  }
  return counts;
}
