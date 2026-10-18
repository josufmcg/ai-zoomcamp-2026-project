/**
 * Manager bills section tests (backlog task 16).
 *
 * Covers issuing a manual bill for a managed unit and marking a bill paid: the
 * issue form sends the fields the API expects, and the pay button is only
 * offered while the bill is unpaid.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { jsonResponse, makeSession, renderWithProviders } from "../../test/helpers";
import { ManagerBillsSection } from "./ManagerBillsSection";

const UNITS = [
  { id: 10, building_id: 5, identifier: "A-101", unit_type: "apartment", tags: [] },
];
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
    amount: "40.00",
    description: "Garage",
    issue_date: "2026-01-01",
    due_date: "2026-01-05",
    status: "paid",
  },
];

/** Mock the bill endpoints and capture writes. */
function mockApi() {
  const created: Array<Record<string, unknown>> = [];
  const paid: number[] = [];
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();

      const payMatch = url.match(/\/bills\/(\d+)\/pay$/);
      if (payMatch && method === "POST") {
        paid.push(Number(payMatch[1]));
        return jsonResponse({ ...BILLS[0], status: "paid" });
      }
      if (url.includes("/bills") && method === "POST") {
        created.push(JSON.parse(String(init?.body)));
        return jsonResponse(BILLS[0], { status: 201 });
      }
      if (url.includes("/bills")) {
        return jsonResponse(BILLS);
      }
      if (url.includes("/units")) {
        return jsonResponse(UNITS);
      }
      throw new Error(`Unexpected request to ${method} ${url}`);
    });
  return { fetchMock, created, paid };
}

describe("ManagerBillsSection", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("only offers the pay action for an unpaid bill", async () => {
    mockApi();
    renderWithProviders(
      <ManagerBillsSection />,
      makeSession("manager"),
      "/manager",
    );

    await waitFor(() => expect(screen.getByTestId("bill-1")).toBeInTheDocument());

    // The pending bill can be paid; the paid one cannot.
    expect(screen.getAllByRole("button", { name: "Mark paid" })).toHaveLength(1);
    expect(screen.getByTestId("bill-2")).toBeInTheDocument();
  });

  it("issues a bill for the chosen unit", async () => {
    const user = userEvent.setup();
    const { created } = mockApi();
    renderWithProviders(
      <ManagerBillsSection />,
      makeSession("manager"),
      "/manager",
    );

    await waitFor(() =>
      expect(screen.getByLabelText("Bill property")).toHaveTextContent("A-101"),
    );

    await user.selectOptions(screen.getByLabelText("Bill property"), "10");
    await user.type(screen.getByLabelText("Amount"), "99.90");
    await user.type(screen.getByLabelText("Bill description"), "Water");
    await user.type(screen.getByLabelText("Due date"), "2026-03-01");
    await user.click(screen.getByRole("button", { name: "Issue bill" }));

    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0]).toMatchObject({
      unit_id: 10,
      amount: "99.90",
      description: "Water",
      due_date: "2026-03-01",
    });
  });

  it("marks a bill paid", async () => {
    const user = userEvent.setup();
    const { paid } = mockApi();
    renderWithProviders(
      <ManagerBillsSection />,
      makeSession("manager"),
      "/manager",
    );

    await waitFor(() => expect(screen.getByTestId("bill-1")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Mark paid" }));

    await waitFor(() => expect(paid).toEqual([1]));
  });
});
