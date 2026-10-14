/**
 * Property hierarchy types shared by the frontend (backlog task 15).
 *
 * These mirror the backend contract in `openapi.yaml`: `UnitType` and
 * `OwnershipType` are the exact enums the API issues, `Tag` matches `TagRead`,
 * and `MyUnit` matches the `MyUnitRead` schema returned by `GET /auth/me/units`.
 */

/** The kinds of unit a building can contain (backend `UnitType`). */
export type UnitType = "apartment" | "garage" | "storage";

/** Every valid unit type, in the order the backend enum declares them. */
export const UNIT_TYPES: readonly UnitType[] = [
  "apartment",
  "garage",
  "storage",
];

/** How a resident holds a unit (backend `OwnershipType`). */
export type OwnershipType = "owner" | "tenant";

/** A free-text label attached to a building or a unit (backend `TagRead`). */
export interface Tag {
  id: number;
  name: string;
}

/** A community (backend `CommunityRead`). */
export interface Community {
  id: number;
  name: string;
}

/** A building inside one community (backend `BuildingRead`). */
export interface Building {
  id: number;
  community_id: number;
  name: string;
  tags: Tag[];
}

/** A unit in the property tree (backend `UnitRead`). */
export interface Unit {
  id: number;
  building_id: number;
  identifier: string;
  unit_type: UnitType;
  tags: Tag[];
}

/** One of the signed-in resident's units (backend `MyUnitRead`). */
export interface MyUnit extends Unit {
  ownership_type: OwnershipType;
}

/** Narrow an unknown value to a {@link UnitType}. */
export function isUnitType(value: unknown): value is UnitType {
  return typeof value === "string" && UNIT_TYPES.some((type) => type === value);
}

/** Narrow an unknown value to a {@link Community} that came from the API. */
export function isCommunity(value: unknown): value is Community {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "number" && typeof candidate.name === "string"
  );
}

/** Narrow an unknown value to a {@link Building} that came from the API. */
export function isBuilding(value: unknown): value is Building {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "number" &&
    typeof candidate.community_id === "number" &&
    typeof candidate.name === "string"
  );
}

/** Narrow an unknown value to a {@link MyUnit} that came from the API. */
export function isMyUnit(value: unknown): value is MyUnit {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "number" &&
    typeof candidate.building_id === "number" &&
    typeof candidate.identifier === "string" &&
    isUnitType(candidate.unit_type)
  );
}
