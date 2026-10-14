/**
 * Initiative and voting types shared by the frontend (backlog task 15).
 *
 * `Initiative` mirrors `InitiativeRead` (whose `is_open` flag the backend
 * computes so the UI never has to duplicate the date rule), `EligibleUnit`
 * mirrors `EligibleUnitRead`, and `VoteResult` mirrors the aggregation
 * response. `InitiativeScope` is the eligibility filter object.
 */

import type { UnitType } from "./property";

/**
 * Eligibility filter over communities, buildings, unit types, and tags
 * (backend `InitiativeScope`). All keys are optional and combine with AND; an
 * entirely empty scope means "every unit".
 */
export interface InitiativeScope {
  community_ids: number[];
  building_ids: number[];
  unit_types: UnitType[];
  tag_ids: number[];
}

/** One choice in an initiative, with its running ballot count (backend `InitiativeOptionRead`). */
export interface InitiativeOption {
  id: number;
  label: string;
  position: number;
  votes: number;
}

/** A community vote (backend `InitiativeRead`). */
export interface Initiative {
  id: number;
  title: string;
  description: string;
  /** ISO date `YYYY-MM-DD`. */
  opens_at: string;
  /** ISO date `YYYY-MM-DD`. */
  closes_at: string;
  /** Whether the initiative accepts ballots today, computed by the backend. */
  is_open: boolean;
  scope: InitiativeScope;
  created_by_id: number;
  options: InitiativeOption[];
}

/**
 * One of the caller's units that may vote in an initiative
 * (backend `EligibleUnitRead`). `option_id` and `vote_id` stay `null` until the
 * unit has cast a ballot, so a single list drives both "cast a ballot here" and
 * "you chose X".
 */
export interface EligibleUnit {
  unit_id: number;
  unit_identifier: string;
  unit_type: UnitType;
  vote_id: number | null;
  option_id: number | null;
}

/** One cast ballot (backend `VoteRead`). */
export interface Vote {
  id: number;
  initiative_id: number;
  option_id: number;
  option_label: string;
  unit_id: number;
  unit_identifier: string;
}

/** Ballot count for one option (backend `VoteTally`). */
export interface VoteTally {
  option_id: number;
  label: string;
  votes: number;
}

/** Aggregation response for one initiative (backend `VoteResult`). */
export interface VoteResult {
  initiative_id: number;
  total_votes: number;
  tallies: VoteTally[];
}
