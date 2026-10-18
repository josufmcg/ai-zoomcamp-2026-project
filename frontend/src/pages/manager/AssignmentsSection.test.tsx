/**
 * Manager assignments section tests (backlog task 16).
 *
 * Covers the resident directory picker and the assign/remove actions: the form
 * sends the selected resident, unit, and ownership flag, and the remove button
 * deletes the assignment.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { jsonResponse, makeSession, renderWithProviders } from "../../test/helpers";
import { AssignmentsSection } from "./AssignmentsSection";

const RESIDENTS = [
  { id: 3, email: "ana@efinges.test", role: "resident", is_active: true },
];
const UNITS = [
  { id: 10, building_id: 5, identifier: "A-101", unit_type: "apartment", tags: [] },
];
const ASSIGNMENTS = [
  {
    id: 20,
    user_id: 3,
    unit_id: 10,
    ownership_type: "owner",
    user: { id: 3, email: "ana@efinges.test", role: "resident", is_active: true },
    unit: { id: 10, building_id: 5, identifier: "A-101", unit_type: "apartment", tags: [] },
  },
];

/** Mock the endpoints the section uses and capture writes. */
function mockApi(assignments: unknown[] = ASSIGNMENTS) {
  const created: Array<Record<string, unknown>> = [];
  const deleted: number[] = [];
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();

      if (url.includes("/assignments") && method === "POST") {
        created.push(JSON.parse(String(init?.body)));
        return jsonResponse(ASSIGNMENTS[0], { status: 201 });
      }
      if (url.includes("/assignments/") && method === "DELETE") {
        deleted.push(Number(url.split("/").pop()));
        return jsonResponse(null, { status: 204 });
      }
      if (url.includes("/assignments")) {
        return jsonResponse(assignments);
      }
      if (url.includes("/residents")) {
        return jsonResponse(RESIDENTS);
      }
      if (url.includes("/units")) {
        return jsonResponse(UNITS);
      }
      throw new Error(`Unexpected request to ${method} ${url}`);
    });
  return { fetchMock, created, deleted };
}

describe("AssignmentsSection", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("lists an assignment with the resident and unit", async () => {
    mockApi();
    renderWithProviders(
      <AssignmentsSection />,
      makeSession("manager"),
      "/manager",
    );

    await waitFor(() => expect(screen.getByTestId("assignment-20")).toBeInTheDocument());
    expect(screen.getByTestId("assignment-20")).toHaveTextContent("ana@efinges.test");
    expect(screen.getByTestId("assignment-20")).toHaveTextContent("A-101");
    expect(screen.getByTestId("assignment-20")).toHaveTextContent("Owner");
  });

  it("assigns the selected resident and unit", async () => {
    const user = userEvent.setup();
    const { created } = mockApi([]);
    renderWithProviders(
      <AssignmentsSection />,
      makeSession("manager"),
      "/manager",
    );

    await waitFor(() =>
      expect(screen.getByLabelText("Resident")).toHaveTextContent("ana@efinges.test"),
    );

    await user.selectOptions(screen.getByLabelText("Resident"), "3");
    await user.selectOptions(screen.getByLabelText("Property"), "10");
    await user.selectOptions(screen.getByLabelText("Ownership"), "tenant");
    await user.click(screen.getByRole("button", { name: "Assign resident" }));

    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0]).toEqual({
      user_id: 3,
      unit_id: 10,
      ownership_type: "tenant",
    });
  });

  it("removes an assignment", async () => {
    const user = userEvent.setup();
    const { deleted } = mockApi();
    renderWithProviders(
      <AssignmentsSection />,
      makeSession("manager"),
      "/manager",
    );

    await waitFor(() => expect(screen.getByTestId("assignment-20")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Remove" }));

    await waitFor(() => expect(deleted).toEqual([20]));
  });
});
