/**
 * Property calls used by the resident and manager screens (backlog tasks 15-16).
 *
 * The manager screens maintain the whole property tree and its tags, so this
 * module wraps every community, building, unit, and tag endpoint. The resident
 * helper `GET /auth/me/units` lives here too: it returns the same unit shape
 * with an extra ownership flag, so the two roles share one module.
 *
 * Tag attachment is separate from tag creation: the create/update requests
 * carry `tag_ids` of tags that already exist, so a manager creates a tag once
 * and then attaches it to many buildings or units.
 */

import { api } from "./apiClient";
import type {
  Building,
  Community,
  MyUnit,
  Tag,
  Unit,
  UnitType,
} from "../types/property";

/** Optional filters accepted by {@link listUnits}. */
export interface ListUnitsParams {
  buildingId?: number;
  communityId?: number;
  tagId?: number;
}

/** Request body for {@link createBuilding}. */
export interface BuildingCreate {
  community_id: number;
  name: string;
  tag_ids?: number[];
}

/** Request body for {@link updateBuilding}. */
export interface BuildingUpdate {
  name?: string;
  tag_ids?: number[];
}

/** Request body for {@link createUnit}. */
export interface UnitCreate {
  building_id: number;
  identifier: string;
  unit_type: UnitType;
  tag_ids?: number[];
}

/** Request body for {@link updateUnit}. */
export interface UnitUpdate {
  identifier?: string;
  unit_type?: UnitType;
  tag_ids?: number[];
}

/** Return every unit assigned to the signed-in user. */
export function listMyUnits(): Promise<MyUnit[]> {
  return api.get<MyUnit[]>("/auth/me/units");
}

/** List the communities the caller may read. */
export function listCommunities(): Promise<Community[]> {
  return api.get<Community[]>("/communities");
}

/** List the buildings the caller may read, optionally within one community. */
export function listBuildings(communityId?: number): Promise<Building[]> {
  return api.get<Building[]>("/buildings", {
    query: { community_id: communityId },
  });
}

/** List the units the caller may read, optionally filtered. */
export function listUnits(params: ListUnitsParams = {}): Promise<Unit[]> {
  return api.get<Unit[]>("/units", {
    query: {
      building_id: params.buildingId,
      community_id: params.communityId,
      tag_id: params.tagId,
    },
  });
}

/** List every tag. Tags are shared, so any signed-in user may read them. */
export function listTags(): Promise<Tag[]> {
  return api.get<Tag[]>("/tags");
}

/** Create a building inside a community the caller may write to. */
export function createBuilding(payload: BuildingCreate): Promise<Building> {
  return api.post<Building>("/buildings", payload);
}

/** Rename a building or replace its tags. */
export function updateBuilding(
  buildingId: number,
  payload: BuildingUpdate,
): Promise<Building> {
  return api.patch<Building>(`/buildings/${buildingId}`, payload);
}

/** Delete a building, cascading to its units and their records. */
export function deleteBuilding(buildingId: number): Promise<void> {
  return api.delete<void>(`/buildings/${buildingId}`);
}

/** Create a unit inside a building the caller may write to. */
export function createUnit(payload: UnitCreate): Promise<Unit> {
  return api.post<Unit>("/units", payload);
}

/** Change a unit's identifier, type, or tags. */
export function updateUnit(unitId: number, payload: UnitUpdate): Promise<Unit> {
  return api.patch<Unit>(`/units/${unitId}`, payload);
}

/** Delete a unit, cascading to its assignments, bills, and incidences. */
export function deleteUnit(unitId: number): Promise<void> {
  return api.delete<void>(`/units/${unitId}`);
}

/** Create a tag. Managers and administrators only. */
export function createTag(name: string): Promise<Tag> {
  return api.post<Tag>("/tags", { name });
}

/** Delete a tag, detaching it from every building and unit. */
export function deleteTag(tagId: number): Promise<void> {
  return api.delete<void>(`/tags/${tagId}`);
}
