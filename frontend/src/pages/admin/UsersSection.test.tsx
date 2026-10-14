/**
 * Administrator user-management section tests (backlog task 17).
 *
 * Covers the create form, the role change action, the activation toggle, and
 * the self-action guards that stop an administrator from demoting or
 * deactivating their own account.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  jsonResponse,
  makeSession,
  renderWithProviders,
} from "../../test/helpers";
import { UsersSection } from "./UsersSection";

// The seeded administrator's id is 1 (see `makeSession`), so this row is "you".
const ADMIN = { id: 1, email: "admin@efinges.test", role: "administrator", is_active: true };
const RESIDENT = { id: 3, email: "ana@efinges.test", role: "resident", is_active: true };

/** Mock the `/users` endpoints used by the section and capture writes. */
function mockApi(users: unknown[] = [ADMIN, RESIDENT]) {
  const created: Array<Record<string, unknown>> = [];
  const patched: Array<{ id: number; body: Record<string, unknown> }> = [];
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();

      const patchMatch = url.match(/\/users\/(\d+)$/);
      if (patchMatch && method === "PATCH") {
        const id = Number(patchMatch[1]);
        const body = JSON.parse(String(init?.body));
        patched.push({ id, body });
        return jsonResponse({ ...RESIDENT, id, ...body });
      }
      if (url.endsWith("/users") && method === "POST") {
        created.push(JSON.parse(String(init?.body)));
        return jsonResponse(RESIDENT, { status: 201 });
      }
      if (url.includes("/users")) {
        return jsonResponse(users);
      }
      throw new Error(`Unexpected request to ${method} ${url}`);
    });
  return { fetchMock, created, patched };
}

describe("UsersSection", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("lists accounts with their role and status", async () => {
    mockApi();
    renderWithProviders(
      <UsersSection />,
      makeSession("administrator"),
      "/admin",
    );

    await waitFor(() => expect(screen.getByTestId("user-3")).toBeInTheDocument());
    const row = screen.getByTestId("user-3");
    expect(row).toHaveTextContent("ana@efinges.test");
    expect(row).toHaveTextContent("Resident");
    expect(row).toHaveTextContent("Active");
  });

  it("creates a user from the form with the entered role", async () => {
    const user = userEvent.setup();
    const { created } = mockApi([]);
    renderWithProviders(
      <UsersSection />,
      makeSession("administrator"),
      "/admin",
    );

    await waitFor(() =>
      expect(screen.getByText(/No accounts match/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole("button", { name: "Add user" }));
    await user.type(screen.getByLabelText("Email"), "nuevo@efinges.test");
    await user.type(screen.getByLabelText("Password"), "supersecret");
    await user.selectOptions(screen.getByLabelText("New user role"), "manager");
    await user.click(screen.getByRole("button", { name: "Create user" }));

    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0]).toEqual({
      email: "nuevo@efinges.test",
      password: "supersecret",
      role: "manager",
    });
  });

  it("rejects a too-short password before sending", async () => {
    const user = userEvent.setup();
    const { created } = mockApi([]);
    renderWithProviders(
      <UsersSection />,
      makeSession("administrator"),
      "/admin",
    );

    await waitFor(() =>
      expect(screen.getByText(/No accounts match/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole("button", { name: "Add user" }));
    await user.type(screen.getByLabelText("Email"), "nuevo@efinges.test");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.click(screen.getByRole("button", { name: "Create user" }));

    expect(
      await screen.findByText("The password must be at least 8 characters."),
    ).toBeInTheDocument();
    expect(created).toHaveLength(0);
  });

  it("changes another user's role", async () => {
    const user = userEvent.setup();
    const { patched } = mockApi();
    renderWithProviders(
      <UsersSection />,
      makeSession("administrator"),
      "/admin",
    );

    await waitFor(() => expect(screen.getByTestId("user-3")).toBeInTheDocument());
    const row = screen.getByTestId("user-3");
    await user.selectOptions(
      within(row).getByLabelText("Role for ana@efinges.test"),
      "manager",
    );

    await waitFor(() => expect(patched).toEqual([{ id: 3, body: { role: "manager" } }]));
  });

  it("deactivates another account", async () => {
    const user = userEvent.setup();
    const { patched } = mockApi();
    renderWithProviders(
      <UsersSection />,
      makeSession("administrator"),
      "/admin",
    );

    await waitFor(() => expect(screen.getByTestId("user-3")).toBeInTheDocument());
    const row = screen.getByTestId("user-3");
    await user.click(within(row).getByRole("button", { name: "Deactivate" }));

    await waitFor(() =>
      expect(patched).toEqual([{ id: 3, body: { is_active: false } }]),
    );
  });

  it("refuses to demote the signed-in administrator", async () => {
    const user = userEvent.setup();
    const { patched } = mockApi();
    renderWithProviders(
      <UsersSection />,
      makeSession("administrator"),
      "/admin",
    );

    await waitFor(() => expect(screen.getByTestId("user-1")).toBeInTheDocument());
    const row = screen.getByTestId("user-1");
    await user.selectOptions(
      within(row).getByLabelText("Role for admin@efinges.test"),
      "manager",
    );

    expect(
      await screen.findByText("You cannot change your own role."),
    ).toBeInTheDocument();
    expect(patched).toHaveLength(0);
  });

  it("refuses to deactivate the signed-in administrator", async () => {
    const user = userEvent.setup();
    const { patched } = mockApi();
    renderWithProviders(
      <UsersSection />,
      makeSession("administrator"),
      "/admin",
    );

    await waitFor(() => expect(screen.getByTestId("user-1")).toBeInTheDocument());
    const row = screen.getByTestId("user-1");
    await user.click(within(row).getByRole("button", { name: "Deactivate" }));

    expect(
      await screen.findByText("You cannot deactivate your own account."),
    ).toBeInTheDocument();
    expect(patched).toHaveLength(0);
  });
});
