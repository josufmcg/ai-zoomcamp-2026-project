/**
 * Small display formatters shared by the screens (backlog task 15).
 *
 * Kept in one place so a unit type, ownership flag, or date renders the same
 * way everywhere and the tests can assert on a stable string.
 */

import type { UserRole } from "../types/auth";
import type { OwnershipType, UnitType } from "../types/property";
import type { Language } from "../i18n/I18nContext";

function localeFor(language: Language): string {
  return language === "es" ? "es-ES" : "en-US";
}

/** Human-readable label for a user role (`"administrator"` → `"Administrator"`). */
export function roleLabel(role: UserRole): string {
  switch (role) {
    case "administrator":
      return "Administrator";
    case "manager":
      return "Manager";
    case "resident":
      return "Resident";
  }
}

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
export function formatDate(isoDate: string, language: Language = "en"): string {
  const date = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return isoDate;
  }
  return date.toLocaleDateString(localeFor(language), {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Format an ISO date-time as a short, locale-aware date and time. */
export function formatDateTime(
  isoDateTime: string,
  language: Language = "en",
): string {
  const date = new Date(isoDateTime);
  if (Number.isNaN(date.getTime())) {
    return isoDateTime;
  }
  return date.toLocaleString(localeFor(language), {
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
export function formatAmount(
  amount: string,
  currency = "USD",
  language: Language = "en",
): string {
  const value = Number(amount);
  if (!Number.isFinite(value)) {
    return amount;
  }
  return new Intl.NumberFormat(localeFor(language), {
    style: "currency",
    currency,
  }).format(value);
}
