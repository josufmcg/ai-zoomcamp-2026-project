/**
 * Administrator home screen tests (backlog task 17).
 *
 * The screen stacks two independent sections; this asserts the page heading the
 * route test names and that both administrator sections render.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";

import { jsonResponse, makeSession, renderWithProviders } from "../test/helpers";
import { AdminHomePage } from "./AdminHomePage";

/** Answer every read the two sections issue with an empty list. */
function mockEmptyApi() {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes("/users")) {
      return jsonResponse([]);
    }
    if (url.includes("/communities")) {
      return jsonResponse([]);
    }
    if (url.includes("/buildings")) {
      return jsonResponse([]);
    }
    if (url.includes("/units")) {
      return jsonResponse([]);
    }
    throw new Error(`Unexpected request to ${url}`);
  });
}

describe("AdminHomePage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the administrator section headings", async () => {
    mockEmptyApi();
    renderWithProviders(
      <AdminHomePage />,
      makeSession("administrator"),
      "/admin",
    );

    expect(screen.getByRole("heading", { name: "Users" })).toBeInTheDocument();
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "User accounts" }),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("heading", { name: "Global property overview" }),
    ).toBeInTheDocument();
  });
});
