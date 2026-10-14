/**
 * Manager incidence section tests (backlog task 16).
 *
 * Covers the lifecycle transition controls: only the immediate next stage is
 * offered, a closed incidence offers none, the button sends the right status,
 * and a reply posts into the thread.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { jsonResponse, makeSession, renderWithProviders } from "../../test/helpers";
import { ManagerIncidencesSection } from "./ManagerIncidencesSection";

const SUBMITTED = {
  id: 1,
  unit_id: 10,
  unit_identifier: "A-101",
  created_by_id: 2,
  created_by_email: "ana@efinges.test",
  title: "Leaking tap",
  description: "The kitchen tap drips constantly.",
  status: "submitted",
  created_at: "2026-01-02T10:00:00Z",
  comments: [
    {
      id: 100,
      incidence_id: 1,
      author_id: 2,
      author_email: "ana@efinges.test",
      body: "It started yesterday.",
      created_at: "2026-01-02T10:05:00Z",
    },
  ],
};

const CLOSED = {
  ...SUBMITTED,
  id: 2,
  title: "Broken gate",
  status: "closed",
  comments: [],
};

/** Mock the incidence endpoints used by the section. */
function mockApi(incidences: unknown[] = [SUBMITTED, CLOSED]) {
  const statusBodies: Array<{ id: number; status: string }> = [];
  const commentBodies: Array<{ id: number; body: string }> = [];
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();

      const statusMatch = url.match(/\/incidences\/(\d+)\/status$/);
      if (statusMatch && method === "PATCH") {
        const body = JSON.parse(String(init?.body));
        statusBodies.push({ id: Number(statusMatch[1]), status: body.status });
        return jsonResponse({ ...SUBMITTED, status: body.status });
      }

      const commentMatch = url.match(/\/incidences\/(\d+)\/comments$/);
      if (commentMatch && method === "POST") {
        const body = JSON.parse(String(init?.body));
        commentBodies.push({ id: Number(commentMatch[1]), body: body.body });
        return jsonResponse(
          {
            id: 200,
            incidence_id: Number(commentMatch[1]),
            author_id: 1,
            author_email: "manager@efinges.test",
            body: body.body,
            created_at: "2026-01-03T09:00:00Z",
          },
          { status: 201 },
        );
      }

      if (url.includes("/incidences")) {
        // Honor the status filter the section sends as a query parameter.
        const statusMatch = url.match(/[?&]status=([^&]+)/);
        if (statusMatch) {
          const status = decodeURIComponent(statusMatch[1]);
          return jsonResponse(
            (incidences as Array<{ status?: string }>).filter(
              (row) => row.status === status,
            ),
          );
        }
        return jsonResponse(incidences);
      }
      throw new Error(`Unexpected request to ${method} ${url}`);
    });
  return { fetchMock, statusBodies, commentBodies };
}

describe("ManagerIncidencesSection", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("offers only the next lifecycle stage for an open incidence", async () => {
    mockApi();
    renderWithProviders(
      <ManagerIncidencesSection />,
      makeSession("manager"),
      "/manager",
    );

    await waitFor(() => expect(screen.getByTestId("incidence-1")).toBeInTheDocument());

    expect(
      screen.getByRole("button", { name: "Mark in progress" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Mark resolved" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Mark closed" }),
    ).not.toBeInTheDocument();
  });

  it("offers no transition for a closed incidence", async () => {
    mockApi();
    renderWithProviders(
      <ManagerIncidencesSection />,
      makeSession("manager"),
      "/manager",
    );

    await waitFor(() => expect(screen.getByTestId("incidence-2")).toBeInTheDocument());

    expect(screen.queryByTestId("advance-2")).not.toBeInTheDocument();
  });

  it("sends the next status when the transition button is used", async () => {
    const user = userEvent.setup();
    const { statusBodies } = mockApi();
    renderWithProviders(
      <ManagerIncidencesSection />,
      makeSession("manager"),
      "/manager",
    );

    await waitFor(() => expect(screen.getByTestId("advance-1")).toBeInTheDocument());
    await user.click(screen.getByTestId("advance-1"));

    await waitFor(() => expect(statusBodies).toEqual([{ id: 1, status: "in progress" }]));
  });

  it("posts a reply into the incidence thread", async () => {
    const user = userEvent.setup();
    const { commentBodies } = mockApi();
    renderWithProviders(
      <ManagerIncidencesSection />,
      makeSession("manager"),
      "/manager",
    );

    await waitFor(() => expect(screen.getByTestId("incidence-1")).toBeInTheDocument());

    const card = screen.getByTestId("incidence-1");
    await user.type(screen.getByLabelText("Comment on Leaking tap"), "A plumber is coming.");
    await user.click(within(card).getByRole("button", { name: "Reply" }));

    await waitFor(() =>
      expect(commentBodies).toEqual([{ id: 1, body: "A plumber is coming." }]),
    );
  });

  it("filters the list by lifecycle stage", async () => {
    const user = userEvent.setup();
    mockApi([SUBMITTED]);
    renderWithProviders(
      <ManagerIncidencesSection />,
      makeSession("manager"),
      "/manager",
    );

    await waitFor(() => expect(screen.getByTestId("incidence-1")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "resolved" }));

    await waitFor(() =>
      expect(screen.getByText(/No incidences are resolved/i)).toBeInTheDocument(),
    );
  });
});
