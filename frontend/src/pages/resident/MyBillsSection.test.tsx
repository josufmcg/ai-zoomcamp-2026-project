/**
 * Resident bills section tests (backlog task 15).
 *
 * Covers the status filter end to end at the component level: the tabs render
 * the per-status counts, clicking a tab shows only matching bills, and the
 * computed `overdue` status is selectable exactly like the stored ones.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { jsonResponse, makeSession, renderWithProviders } from "../../test/helpers";
import { MyBillsSection } from "./MyBillsSection";

const BILLS = [
  {
    id: 1,
    unit_id: 10,
    unit_identifier: "A-101",
    unit_type: "apartment",
    amount: "120.00",
    description: "Monthly fee",
    issue_date: "2026-01-01",
    due_date: "2026-02-01",
    status: "pending",
  },
  {
    id: 2,
    unit_id: 10,
    unit_identifier: "A-101",
    unit_type: "apartment",
    amount: "80.00",
    description: "Water",
    issue_date: "2026-01-01",
    due_date: "2026-01-05",
    status: "overdue",
  },
  {
    id: 3,
    unit_id: 11,
    unit_identifier: "G-1",
    unit_type: "garage",
    amount: "40.00",
    description: "Garage",
    issue_date: "2026-01-01",
    due_date: "2026-02-01",
    status: "paid",
  },
];

/** Mock a single `GET /bills` returning the fixture. */
function mockBills(bills: unknown = BILLS) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/bills")) {
        return jsonResponse(bills);
      }
      throw new Error(`Unexpected request to ${url}`);
    });
}

describe("MyBillsSection", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the per-status counts", async () => {
    mockBills();
    renderWithProviders(<MyBillsSection />, makeSession("resident"), "/resident");

    await waitFor(() =>
      expect(screen.getByTestId("bill-count-all")).toHaveTextContent("(3)"),
    );
    expect(screen.getByTestId("bill-count-pending")).toHaveTextContent("(1)");
    expect(screen.getByTestId("bill-count-overdue")).toHaveTextContent("(1)");
    expect(screen.getByTestId("bill-count-paid")).toHaveTextContent("(1)");
  });

  it("shows every bill by default", async () => {
    mockBills();
    renderWithProviders(<MyBillsSection />, makeSession("resident"), "/resident");

    await waitFor(() => expect(screen.getByTestId("bill-1")).toBeInTheDocument());
    expect(screen.getByTestId("bill-2")).toBeInTheDocument();
    expect(screen.getByTestId("bill-3")).toBeInTheDocument();
  });

  it("filters to the computed overdue status when its tab is clicked", async () => {
    const user = userEvent.setup();
    mockBills();
    renderWithProviders(<MyBillsSection />, makeSession("resident"), "/resident");

    await waitFor(() => expect(screen.getByTestId("bill-1")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /Overdue/ }));

    expect(screen.getByTestId("bill-2")).toBeInTheDocument();
    expect(screen.queryByTestId("bill-1")).not.toBeInTheDocument();
    expect(screen.queryByTestId("bill-3")).not.toBeInTheDocument();
    expect(screen.getByTestId("bill-status-2")).toHaveTextContent("Overdue");
  });

  it("shows an empty message when a filter matches nothing", async () => {
    const user = userEvent.setup();
    mockBills([BILLS[0]]);
    renderWithProviders(<MyBillsSection />, makeSession("resident"), "/resident");

    await waitFor(() => expect(screen.getByTestId("bill-1")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /Paid/ }));

    expect(screen.getByText(/No paid bills/i)).toBeInTheDocument();
  });

  it("surfaces a load failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ detail: "Unauthorized" }, { status: 401 }),
    );
    renderWithProviders(<MyBillsSection />, makeSession("resident"), "/resident");

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Unauthorized"),
    );
  });
});
