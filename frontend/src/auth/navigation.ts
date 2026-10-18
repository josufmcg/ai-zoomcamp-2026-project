/**
 * Role-filtered navigation model (backlog task 14).
 *
 * The link list is data, not markup, so the same definition drives the sidebar
 * and any test that asserts which links a role sees. Tasks 15 to 17 add the
 * screens behind the resident, manager, and administrator routes; this task
 * establishes the shell, the routes, and the role filtering.
 */

import type { UserRole } from "../types/auth";

/** Icon used to identify a section in the navigation. */
export type NavIconName =
  | "overview"
  | "units"
  | "properties"
  | "users"
  | "assignments"
  | "bills"
  | "incidences"
  | "initiatives";

/** Every role, used for links that all signed-in users can see. */
export const ALL_ROLES: readonly UserRole[] = [
  "administrator",
  "manager",
  "resident",
];

/** One entry in the navigation shell. */
export interface NavItem {
  /** Visible label. */
  label: string;
  /** Route the link points at, absolute. */
  to: string;
  /** Icon used alongside the visible label. */
  icon: NavIconName;
  /** Roles that see the link and may open the route. */
  roles: readonly UserRole[];
}

/**
 * The full navigation model, in display order.
 *
 * `/overview` is shared by all three roles because each role arrives with a
 * different question (backlog tasks 15 to 17). The role-specific entries are
 * the entry points to those tasks' screens.
 */
export const NAV_ITEMS: readonly NavItem[] = [
  { label: "Overview", to: "/overview", icon: "overview", roles: ALL_ROLES },
  {
    label: "My properties",
    to: "/resident/units",
    icon: "units",
    roles: ["resident"],
  },
  { label: "My bills", to: "/resident/bills", icon: "bills", roles: ["resident"] },
  {
    label: "My incidences",
    to: "/resident/incidences",
    icon: "incidences",
    roles: ["resident"],
  },
  {
    label: "Open initiatives",
    to: "/resident/initiatives",
    icon: "initiatives",
    roles: ["resident"],
  },
  {
    label: "My properties",
    to: "/manager/properties",
    icon: "properties",
    roles: ["manager"],
  },
  {
    label: "Assignments",
    to: "/manager/assignments",
    icon: "assignments",
    roles: ["manager"],
  },
  { label: "Bills", to: "/manager/bills", icon: "bills", roles: ["manager"] },
  {
    label: "Incidences",
    to: "/manager/incidences",
    icon: "incidences",
    roles: ["manager"],
  },
  {
    label: "Initiatives",
    to: "/manager/initiatives",
    icon: "initiatives",
    roles: ["manager"],
  },
  { label: "Users", to: "/admin/users", icon: "users", roles: ["administrator"] },
  {
    label: "Global overview",
    to: "/admin/properties",
    icon: "properties",
    roles: ["administrator"],
  },
];

/** Return the navigation entries visible to `role`. */
export function navItemsForRole(role: UserRole): NavItem[] {
  return NAV_ITEMS.filter((item) => item.roles.includes(role));
}

/** Return the landing route for `role` after a successful login. */
export function homePathForRole(role: UserRole): string {
  switch (role) {
    case "administrator":
      return "/admin/users";
    case "manager":
      return "/manager/properties";
    case "resident":
      return "/resident/units";
  }
}

/** Location state the guard leaves behind when it redirects to `/login`. */
export interface LoginLocationState {
  from?: string;
}

/**
 * Decide where a just-signed-in user should land.
 *
 * Whoever was turned away by `RequireAuth` finds the path they asked for in
 * `location.state.from`, so they resume there instead of being dropped on the
 * generic home screen. The path is only honoured when it is a real absolute
 * path that is not the login form itself, which would otherwise loop.
 */
export function postLoginPath(state: unknown, role: UserRole): string {
  const from = (state as LoginLocationState | null)?.from;
  if (
    typeof from === "string" &&
    from.startsWith("/") &&
    !from.startsWith("//") &&
    !from.startsWith("/login")
  ) {
    return from;
  }
  return homePathForRole(role);
}
