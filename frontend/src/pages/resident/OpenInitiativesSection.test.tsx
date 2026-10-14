/**
 * Resident initiatives section tests (backlog task 15).
 *
 * Covers the per-unit ballot submission at the component level: the form shows
 * one row per eligible unit, a unit that already voted is shown as voted, and
 * submitting sends exactly one vote request per selected unit and none for the
 * unit that already voted.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { jsonResponse, makeSession, renderWithProviders } from "../../test/helpers";
import { OpenInitiativesSection } from "./OpenInitiativesSection";

const INITIATIVE = {
  id: 1,
  title: "Bike racks in the courtyard",
  description: "Should we install two bike racks?",
  opens_at: "2026-01-01",
  closes_at: "2026-12-31",
  is_open: true,
  scope: {
    community_ids: [],
    building_ids: [],
    unit_types: [],
    tag_ids: [],
  },
  created_by_id: 2,
  options: [
    { id: 11, label: "Yes", position: 0, votes: 0 },
    { id: 12, label: "No", position: 1, votes: 0 },
  ],
};

// Unit 12 already voted (vote_id set), so it must never receive a second ballot.
const ELIGIBLE = [
  {
    unit_id: 10,
    unit_identifier: "A-101",
    unit_type: "apartment",
    vote_id: null,
    option_id: null,
  },
  {
    unit_id: 11,
    unit_identifier: "G-1",
    unit_type: "garage",
    vote_id: null,
    option_id: null,
  },
  {
    unit_id: 12,
    unit_identifier: "S-1",
    unit_type: "storage",
    vote_id: 99,
    option_id: 11,
  },
];

/** Mock the initiative list, the eligible units, and the vote endpoint. */
function mockApi() {
  const voteBodies: Array<{ unit_id: number; option_id: number }> = [];
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();

      if (url.endsWith("/initiatives/1/eligible-units")) {
        return jsonResponse(ELIGIBLE);
      }
      if (url.endsWith("/initiatives/1/votes") && method === "POST") {
        const body = JSON.parse(String(init?.body));
        voteBodies.push(body);
        return jsonResponse(
          {
            id: 100 + voteBodies.length,
            initiative_id: 1,
            option_id: body.option_id,
            option_label: "Yes",
            unit_id: body.unit_id,
            unit_identifier: `U-${body.unit_id}`,
          },
          { status: 201 },
        );
      }
      if (url.includes("/initiatives")) {
        return jsonResponse([INITIATIVE]);
      }
      throw new Error(`Unexpected request to ${method} ${url}`);
    });
  return { fetchMock, voteBodies };
}

describe("OpenInitiativesSection", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("lists an open initiative with one row per eligible unit", async () => {
    mockApi();
    renderWithProviders(
      <OpenInitiativesSection />,
      makeSession("resident"),
      "/resident",
    );

    await waitFor(() =>
      expect(screen.getByTestId("initiative-1")).toBeInTheDocument(),
    );
    await waitFor(() => expect(screen.getByTestId("unit-10")).toBeInTheDocument());
    expect(screen.getByTestId("unit-11")).toBeInTheDocument();
    expect(screen.getByTestId("unit-12")).toBeInTheDocument();
  });

  it("shows a unit that already voted as voted, without a picker", async () => {
    mockApi();
    renderWithProviders(
      <OpenInitiativesSection />,
      makeSession("resident"),
      "/resident",
    );

    await waitFor(() => expect(screen.getByTestId("unit-12")).toBeInTheDocument());

    expect(screen.getByTestId("unit-12")).toHaveTextContent("Voted: Yes");
    expect(screen.queryByLabelText("Option for S-1")).not.toBeInTheDocument();
  });

  it("submits one ballot per selected unit and skips the voted unit", async () => {
    const user = userEvent.setup();
    const { voteBodies } = mockApi();
    renderWithProviders(
      <OpenInitiativesSection />,
      makeSession("resident"),
      "/resident",
    );

    await waitFor(() => expect(screen.getByTestId("unit-10")).toBeInTheDocument());

    await user.selectOptions(screen.getByLabelText("Option for A-101"), "11");
    await user.selectOptions(screen.getByLabelText("Option for G-1"), "12");

    await user.click(screen.getByRole("button", { name: /Cast 2 ballots/ }));

    await waitFor(() => expect(voteBodies).toHaveLength(2));
    expect(voteBodies).toEqual([
      { unit_id: 10, option_id: 11 },
      { unit_id: 11, option_id: 12 },
    ]);
  });

  it("disables submission until a unit is selected", async () => {
    const user = userEvent.setup();
    mockApi();
    renderWithProviders(
      <OpenInitiativesSection />,
      makeSession("resident"),
      "/resident",
    );

    await waitFor(() => expect(screen.getByTestId("unit-10")).toBeInTheDocument());

    const submit = screen.getByRole("button", { name: /Cast/ });
    expect(submit).toBeDisabled();

    await user.selectOptions(screen.getByLabelText("Option for A-101"), "11");
    expect(submit).toBeEnabled();
  });
});
