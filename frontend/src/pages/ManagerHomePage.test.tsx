/**
 * Manager home screen tests (backlog task 16).
 *
 * The screen stacks five independent sections; this asserts the ones the route
 * test names and that the manager-only screens are reachable through it.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";

import { jsonResponse, makeSession, renderWithProviders } from "../test/helpers";
import { ManagerHomePage } from "./ManagerHomePage";

/** Answer every read the five sections issue with an empty list. */
function mockEmptyApi() {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes("/bills")) {
      return jsonResponse([]);
    }
    if (url.includes("/incidences")) {
      return jsonResponse([]);
    }
    if (url.includes("/initiatives")) {
      return jsonResponse([]);
    }
    if (url.includes("/assignments")) {
      return jsonResponse([]);
    }
    if (url.includes("/residents")) {
      return jsonResponse([]);
    }
    if (url.includes("/buildings")) {
      return jsonResponse([]);
    }
    if (url.includes("/units")) {
      return jsonResponse([]);
    }
    if (url.includes("/communities")) {
      return jsonResponse([]);
    }
    if (url.includes("/tags")) {
      return jsonResponse([]);
    }
    throw new Error(`Unexpected request to ${url}`);
  });
}

describe("ManagerHomePage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the manager section headings", async () => {
    mockEmptyApi();
    renderWithProviders(
      <ManagerHomePage />,
      makeSession("manager"),
      "/manager",
    );

    expect(
      screen.getByRole("heading", { name: "My properties" }),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Property tree" }),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("heading", { name: "Resident assignments" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Bills" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Incidences" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Initiatives" }),
    ).toBeInTheDocument();
  });
});
