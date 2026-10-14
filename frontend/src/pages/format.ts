/**
 * Small display formatters shared by the screens (backlog task 15).
 *
 * Kept in one place so a unit type, ownership flag, or date renders the same
 * way everywhere and the tests can assert on a stable string.
 */

import type { OwnershipType, UnitType } from "../types/property";

/** Human-readable label for a unit type (`"storage"` → `"Storage"`). */
export function unitTypeLabel(unitType: UnitType): string {
  switch (unitType) {
    case "apartment":
      return "Apartment";
    case "garage":
      return "Garage";
    case "storage":
      return "Storage";
  }
}

/** Human-readable label for an ownership flag. */
export function ownershipLabel(ownership: OwnershipType): string {
  return ownership === "owner" ? "Owner" : "Tenant";
}

/** Format an ISO date (`YYYY-MM-DD`) as a short, locale-aware date. */
export function formatDate(isoDate: string): string {
  const date = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return isoDate;
  }
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Format an ISO date-time as a short, locale-aware date and time. */
export function formatDateTime(isoDateTime: string): string {
  const date = new Date(isoDateTime);
  if (Number.isNaN(date.getTime())) {
    return isoDateTime;
  }
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format a money string for display.
 *
 * The amount travels as a decimal string and is **not** parsed into a float, so
 * an unparseable value is shown verbatim rather than as `NaN`.
 */
export function formatAmount(amount: string, currency = "USD"): string {
  const value = Number(amount);
  if (!Number.isFinite(value)) {
    return amount;
  }
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
  }).format(value);
}
