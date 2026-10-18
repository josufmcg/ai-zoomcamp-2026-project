/**
 * Manager property tree tests (backlog task 16).
 *
 * Covers rendering the tree and the two creation flows a manager uses most:
 * adding a building to a community and a unit to a building. Both send the
 * payload the API expects and refresh the tree.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { jsonResponse, makeSession, renderWithProviders } from "../../test/helpers";
import { PropertyTreeSection } from "./PropertyTreeSection";

const COMMUNITIES = [{ id: 1, name: "Riverside" }];
const BUILDINGS = [
  { id: 5, community_id: 1, name: "Block A", tags: [{ id: 9, name: "Downtown" }] },
];
const UNITS = [
  { id: 10, building_id: 5, identifier: "A-101", unit_type: "apartment", tags: [] },
];
const TAGS = [{ id: 9, name: "Downtown" }];

/** Mock the property endpoints and capture writes. */
function mockApi() {
  const buildings: Array<Record<string, unknown>> = [];
  const units: Array<Record<string, unknown>> = [];
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();

      if (url.endsWith("/buildings") && method === "POST") {
        const body = JSON.parse(String(init?.body));
        buildings.push(body);
        return jsonResponse({ id: 6, ...body, tags: [] }, { status: 201 });
      }
      if (url.endsWith("/units") && method === "POST") {
        const body = JSON.parse(String(init?.body));
        units.push(body);
        return jsonResponse({ id: 11, ...body, tags: [] }, { status: 201 });
      }
      if (url.includes("/buildings")) {
        return jsonResponse(BUILDINGS);
      }
      if (url.includes("/units")) {
        return jsonResponse(UNITS);
      }
      if (url.includes("/communities")) {
        return jsonResponse(COMMUNITIES);
      }
      if (url.includes("/tags")) {
        return jsonResponse(TAGS);
      }
      throw new Error(`Unexpected request to ${method} ${url}`);
    });
  return { fetchMock, buildings, units };
}

describe("PropertyTreeSection", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders communities with their buildings and units", async () => {
    mockApi();
    renderWithProviders(
      <PropertyTreeSection />,
      makeSession("manager"),
      "/manager",
    );

    await waitFor(() => expect(screen.getByTestId("community-1")).toBeInTheDocument());
    expect(screen.getByTestId("community-1")).toHaveTextContent("Riverside");
    expect(screen.getByTestId("building-5")).toHaveTextContent("Block A");
    expect(screen.getByTestId("unit-10")).toHaveTextContent("A-101");
  });

  it("creates a building in the chosen community", async () => {
    const user = userEvent.setup();
    const { buildings } = mockApi();
    renderWithProviders(
      <PropertyTreeSection />,
      makeSession("manager"),
      "/manager",
    );

    await waitFor(() => expect(screen.getByTestId("community-1")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Add building" }));
    await user.type(screen.getByLabelText("Building name"), "Block B");
    await user.click(screen.getByRole("button", { name: "Create building" }));

    await waitFor(() => expect(buildings).toHaveLength(1));
    expect(buildings[0]).toMatchObject({
      community_id: 1,
      name: "Block B",
      tag_ids: [],
    });
  });

  it("creates a unit in the chosen building", async () => {
    const user = userEvent.setup();
    const { units } = mockApi();
    renderWithProviders(
      <PropertyTreeSection />,
      makeSession("manager"),
      "/manager",
    );

    await waitFor(() => expect(screen.getByTestId("building-5")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Add property" }));
    await user.type(screen.getByLabelText("Property identifier"), "G-01");
    await user.selectOptions(screen.getByLabelText("Property type"), "garage");
    await user.click(screen.getByRole("button", { name: "Create property" }));

    await waitFor(() => expect(units).toHaveLength(1));
    expect(units[0]).toMatchObject({
      building_id: 5,
      identifier: "G-01",
      unit_type: "garage",
      tag_ids: [],
    });
  });
});
