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

/** One of the signed-in resident's units (backend `MyUnitRead`). */
export interface MyUnit {
  id: number;
  building_id: number;
  identifier: string;
  unit_type: UnitType;
  ownership_type: OwnershipType;
  tags: Tag[];
}

/** Narrow an unknown value to a {@link UnitType}. */
export function isUnitType(value: unknown): value is UnitType {
  return typeof value === "string" && UNIT_TYPES.some((type) => type === value);
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
