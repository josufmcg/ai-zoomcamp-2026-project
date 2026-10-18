/**
 * Administrator global property overview tests (backlog task 17).
 *
 * The section is read-only, so the test covers the assembled tree: a community
 * with two buildings, one carrying a unit and a tag, and the empty notes for a
 * community and a building with nothing under them.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";

import { jsonResponse, makeSession, renderWithProviders } from "../../test/helpers";
import { GlobalOverviewSection } from "./GlobalOverviewSection";

const COMMUNITIES = [
  { id: 1, name: "Residencial Norte" },
  { id: 2, name: "Residencial Sur" },
];
const BUILDINGS = [
  { id: 5, community_id: 1, name: "Torre A", tags: [{ id: 1, name: "priority" }] },
  { id: 6, community_id: 1, name: "Torre B", tags: [] },
];
const UNITS = [
  {
    id: 10,
    building_id: 5,
    identifier: "A-101",
    unit_type: "apartment",
    tags: [],
  },
];

/** Mock the three property endpoints the section reads. */
function mockApi() {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/communities")) {
        return jsonResponse(COMMUNITIES);
      }
      if (url.includes("/buildings")) {
        return jsonResponse(BUILDINGS);
      }
      if (url.includes("/units")) {
        return jsonResponse(UNITS);
      }
      throw new Error(`Unexpected request to ${url}`);
    });
  return { fetchMock };
}

describe("GlobalOverviewSection", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("assembles communities, buildings, and units", async () => {
    mockApi();
    renderWithProviders(
      <GlobalOverviewSection />,
      makeSession("administrator"),
      "/admin",
    );

    await waitFor(() =>
      expect(screen.getByTestId("overview-community-1")).toBeInTheDocument(),
    );

    const north = screen.getByTestId("overview-community-1");
    expect(north).toHaveTextContent("Residencial Norte");
    expect(screen.getByTestId("overview-building-5")).toHaveTextContent("Torre A");
    expect(screen.getByTestId("overview-unit-10")).toHaveTextContent("A-101");
    expect(screen.getByTestId("overview-building-5")).toHaveTextContent("#priority");
  });

  it("shows a note for a building with no units", async () => {
    mockApi();
    renderWithProviders(
      <GlobalOverviewSection />,
      makeSession("administrator"),
      "/admin",
    );

    await waitFor(() =>
      expect(screen.getByTestId("overview-building-6")).toBeInTheDocument(),
    );

    expect(screen.getByTestId("overview-building-6")).toHaveTextContent("No properties.");
  });

  it("shows a note for a community with no buildings", async () => {
    mockApi();
    renderWithProviders(
      <GlobalOverviewSection />,
      makeSession("administrator"),
      "/admin",
    );

    await waitFor(() =>
      expect(screen.getByTestId("overview-community-2")).toBeInTheDocument(),
    );

    expect(screen.getByTestId("overview-community-2")).toHaveTextContent(
      "No buildings.",
    );
  });
});
