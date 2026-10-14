/** Route guarding tests (backlog task 14). */

import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";

import { makeSession, renderApp } from "./test/helpers";
import type { UserRole } from "./types/auth";

/** Render the app at `route` as `role` and return the render result. */
function renderAs(role: UserRole, route: string) {
  return renderApp(makeSession(role), route);
}

describe("route guarding", () => {
  it("redirects a signed-out visitor to the login form", () => {
    renderApp(null, "/overview");

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByTestId("current-role")).not.toBeInTheDocument();
  });

  it("redirects a signed-out visitor away from a role route", () => {
    renderApp(null, "/admin");

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("renders the shell for a signed-in user", () => {
    renderAs("resident", "/overview");

    expect(screen.getByTestId("current-role")).toHaveTextContent("resident");
  });

  it("blocks a role from another role's route and explains why", () => {
    renderAs("resident", "/admin");

    expect(screen.getByRole("heading", { name: "Not allowed" })).toBeInTheDocument();
  });

  it("allows a resident onto the resident route", () => {
    renderAs("resident", "/resident");

    expect(screen.getByRole("heading", { name: "My units" })).toBeInTheDocument();
  });

  it("allows a manager onto the manager route", () => {
    renderAs("manager", "/manager");

    expect(screen.getByRole("heading", { name: "My properties" })).toBeInTheDocument();
  });

  it("allows an administrator onto the administrator route", () => {
    renderAs("administrator", "/admin");

    expect(screen.getByRole("heading", { name: "Users" })).toBeInTheDocument();
  });

  it("sends an already signed-in user from /login to their home screen", () => {
    renderAs("manager", "/login");

    expect(screen.getByRole("heading", { name: "My properties" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign in" })).not.toBeInTheDocument();
  });

  it("sends / to the home screen of the signed-in role", () => {
    renderAs("administrator", "/");

    expect(screen.getByRole("heading", { name: "Users" })).toBeInTheDocument();
  });

  it("keeps /forbidden reachable for a signed-in user", () => {
    renderAs("resident", "/forbidden");

    expect(screen.getByRole("heading", { name: "Not allowed" })).toBeInTheDocument();
  });

  it("shows a not-found page for an unknown route", () => {
    renderAs("resident", "/does-not-exist");

    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });
});
