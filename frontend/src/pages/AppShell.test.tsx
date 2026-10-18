/** Role-filtered navigation and logout tests (backlog task 14). */

import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { makeSession, renderApp } from "../test/helpers";
import { navItemsForRole } from "../auth/navigation";
import { getToken, USER_STORAGE_KEY } from "../services";

describe("navigation shell", () => {
  it("shows a resident only the links a resident may use", () => {
    renderApp(makeSession("resident"), "/overview");

    const nav = screen.getByRole("navigation", { name: "Main navigation" });
    expect(nav).toHaveTextContent("Overview");
    expect(nav).toHaveTextContent("My properties");
    expect(nav).toHaveTextContent("My bills");
    expect(nav).toHaveTextContent("My incidences");
    expect(nav).toHaveTextContent("Open initiatives");
    expect(nav.querySelector('a[href="/manager/properties"]')).toBeNull();
    expect(nav).not.toHaveTextContent("Users");
  });

  it("shows a manager only the manager links", () => {
    renderApp(makeSession("manager"), "/overview");

    const nav = screen.getByRole("navigation", { name: "Main navigation" });
    expect(nav).toHaveTextContent("My properties");
    expect(nav).toHaveTextContent("Assignments");
    expect(nav).toHaveTextContent("Bills");
    expect(nav).toHaveTextContent("Incidences");
    expect(nav).toHaveTextContent("Initiatives");
    expect(nav).not.toHaveTextContent("Users");
    expect(nav.querySelector('a[href="/resident/units"]')).toBeNull();
  });

  it("shows an administrator only the administrator links", () => {
    renderApp(makeSession("administrator"), "/overview");

    const nav = screen.getByRole("navigation", { name: "Main navigation" });
    expect(nav).toHaveTextContent("Users");
    expect(nav).toHaveTextContent("Global overview");
    expect(nav.querySelector('a[href="/resident/units"]')).toBeNull();
    expect(nav.querySelector('a[href="/manager/properties"]')).toBeNull();
  });

  it("filters the navigation model exactly as the rendered shell does", () => {
    for (const role of ["resident", "manager", "administrator"] as const) {
      const { unmount } = renderApp(makeSession(role), "/overview");
      const nav = screen.getByRole("navigation", { name: "Main navigation" });
      for (const item of navItemsForRole(role)) {
        expect(nav).toHaveTextContent(item.label);
      }
      expect(nav.querySelectorAll("svg")).toHaveLength(
        navItemsForRole(role).length,
      );
      unmount();
    }
  });

  it("displays the signed-in identity in the header", () => {
    renderApp(
      makeSession("manager", { email: "ana@efinges.test" }),
      "/overview",
    );

    expect(screen.getByText("ana@efinges.test")).toBeInTheDocument();
    expect(screen.getByTestId("current-role")).toHaveTextContent("manager");
    expect(document.querySelector("header svg")).toBeInTheDocument();
  });
});

describe("logout", () => {
  it("clears the stored token and returns to the login form", async () => {
    const user = userEvent.setup();
    const session = makeSession("resident");
    // The provider seeds its state directly, so persist the same session the
    // way a real login would before signing out.
    window.localStorage.setItem("efinges.token", session.token);
    window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(session.user));

    renderApp(session, "/overview");

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(getToken()).toBeNull();
    expect(window.localStorage.getItem(USER_STORAGE_KEY)).toBeNull();
  });
});
