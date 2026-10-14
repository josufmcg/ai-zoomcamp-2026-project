/** Bill status filter tests (backlog task 15). */

import { describe, expect, it } from "vitest";

import type { Bill } from "../../types/billing";
import {
  BILL_FILTERS,
  billFilterLabel,
  countBillsByFilter,
  filterBills,
  isBillFilter,
} from "./billFilter";

/** Build a minimal bill with the fields the filter reads. */
function makeBill(
  id: number,
  status: Bill["status"],
  overrides: Partial<Bill> = {},
): Bill {
  return {
    id,
    unit_id: overrides.unit_id ?? 1,
    unit_identifier: overrides.unit_identifier ?? "A-101",
    unit_type: overrides.unit_type ?? "apartment",
    amount: overrides.amount ?? "100.00",
    description: overrides.description ?? `Bill ${id}`,
    issue_date: overrides.issue_date ?? "2026-01-01",
    due_date: overrides.due_date ?? "2026-02-01",
    status,
  };
}

// One bill per display status, including the backend-computed `overdue`.
const BILLS: Bill[] = [
  makeBill(1, "pending"),
  makeBill(2, "paid"),
  makeBill(3, "overdue"),
  makeBill(4, "pending"),
];

describe("filterBills", () => {
  it("returns every bill for the all filter", () => {
    expect(filterBills(BILLS, "all")).toEqual(BILLS);
  });

  it("returns a new array for the all filter so callers can resort it", () => {
    const result = filterBills(BILLS, "all");
    expect(result).not.toBe(BILLS);
  });

  it("keeps only pending bills", () => {
    expect(filterBills(BILLS, "pending").map((bill) => bill.id)).toEqual([1, 4]);
  });

  it("keeps only paid bills", () => {
    expect(filterBills(BILLS, "paid").map((bill) => bill.id)).toEqual([2]);
  });

  it("selects the computed overdue status like any other", () => {
    // The frontend never derives `overdue` from dates; it filters on the value
    // the API reported, so a pending bill past its due date is selected here.
    expect(filterBills(BILLS, "overdue").map((bill) => bill.id)).toEqual([3]);
  });

  it("returns an empty list when nothing matches", () => {
    expect(filterBills([makeBill(1, "pending")], "overdue")).toEqual([]);
  });
});

describe("countBillsByFilter", () => {
  it("counts each status and the total", () => {
    expect(countBillsByFilter(BILLS)).toEqual({
      all: 4,
      pending: 2,
      paid: 1,
      overdue: 1,
    });
  });

  it("reports zeroes for an empty list", () => {
    expect(countBillsByFilter([])).toEqual({
      all: 0,
      pending: 0,
      paid: 0,
      overdue: 0,
    });
  });
});

describe("bill filter metadata", () => {
  it("offers every display status plus all", () => {
    expect(BILL_FILTERS).toEqual(["all", "pending", "paid", "overdue"]);
  });

  it("labels each filter", () => {
    expect(billFilterLabel("overdue")).toBe("Overdue");
    expect(billFilterLabel("all")).toBe("All");
  });

  it("narrows known filters and rejects unknown ones", () => {
    expect(isBillFilter("overdue")).toBe(true);
    expect(isBillFilter("cancelled")).toBe(false);
    expect(isBillFilter(7)).toBe(false);
  });
});
