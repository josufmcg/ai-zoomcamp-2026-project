/**
 * Manager initiatives section tests (backlog task 16).
 *
 * Covers the initiative scope form: validation gates the submit button, the
 * eligibility filters toggle, and submitting sends the scope the manager built.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { jsonResponse, makeSession, renderWithProviders } from "../../test/helpers";
import { InitiativesSection } from "./InitiativesSection";

const COMMUNITIES = [{ id: 1, name: "Riverside" }];
const BUILDINGS = [{ id: 5, community_id: 1, name: "Block A", tags: [] }];
const TAGS = [{ id: 9, name: "Downtown" }];

/** Mock the read endpoints and capture the create-initiative request body. */
function mockApi() {
  const created: unknown[] = [];
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();

      if (url.endsWith("/initiatives") && method === "POST") {
        created.push(JSON.parse(String(init?.body)));
        return jsonResponse({ id: 1 }, { status: 201 });
      }
      if (url.includes("/initiatives")) {
        return jsonResponse([]);
      }
      if (url.includes("/communities")) {
        return jsonResponse(COMMUNITIES);
      }
      if (url.includes("/buildings")) {
        return jsonResponse(BUILDINGS);
      }
      if (url.includes("/tags")) {
        return jsonResponse(TAGS);
      }
      throw new Error(`Unexpected request to ${method} ${url}`);
    });
  return { fetchMock, created };
}

describe("InitiativesSection", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("disables submission until the draft is valid", async () => {
    const user = userEvent.setup();
    mockApi();
    renderWithProviders(
      <InitiativesSection />,
      makeSession("manager"),
      "/manager",
    );

    const submit = screen.getByRole("button", { name: "Create initiative" });
    expect(submit).toBeDisabled();

    await user.type(screen.getByLabelText("Initiative title"), "Bike racks");
    await user.type(
      screen.getByLabelText("Initiative description"),
      "Should we install two bike racks?",
    );
    await user.type(screen.getByLabelText("Option 1"), "Yes");
    await user.type(screen.getByLabelText("Option 2"), "No");

    await waitFor(() => expect(submit).toBeEnabled());
  });

  it("states that an empty scope means every unit", async () => {
    mockApi();
    renderWithProviders(
      <InitiativesSection />,
      makeSession("manager"),
      "/manager",
    );

    // Wait for the filter sources to load so no state update lands after the
    // assertion.
    await screen.findByLabelText("Riverside");
    expect(
      screen.getByText(/No filters — every unit is eligible to vote/i),
    ).toBeInTheDocument();
  });

  it("submits the selected scope filters with the initiative", async () => {
    const user = userEvent.setup();
    const { created } = mockApi();
    renderWithProviders(
      <InitiativesSection />,
      makeSession("manager"),
      "/manager",
    );

    // Wait for the filter sources to load before interacting with them.
    await waitFor(() => expect(screen.getByLabelText("Garage")).toBeInTheDocument());

    await user.type(screen.getByLabelText("Initiative title"), "Bike racks");
    await user.type(
      screen.getByLabelText("Initiative description"),
      "Should we install two bike racks?",
    );
    await user.type(screen.getByLabelText("Option 1"), "Yes");
    await user.type(screen.getByLabelText("Option 2"), "No");
    await user.click(screen.getByLabelText("Garage"));
    await user.click(screen.getByRole("button", { name: "Create initiative" }));

    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0]).toMatchObject({
      title: "Bike racks",
      options: [{ label: "Yes" }, { label: "No" }],
      scope: {
        community_ids: [],
        building_ids: [],
        unit_types: ["garage"],
        tag_ids: [],
      },
    });
  });
});
