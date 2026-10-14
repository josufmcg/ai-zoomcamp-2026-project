/**
 * Incidence and comment types shared by the frontend (backlog task 15).
 *
 * `IncidenceStatus` is the exact four-stage lifecycle the API issues, and
 * `Incidence` mirrors `IncidenceRead`, which embeds the whole comment thread so
 * a single response carries the conversation.
 */

/** The four stages of an incidence, in lifecycle order (backend `IncidenceStatus`). */
export type IncidenceStatus =
  | "submitted"
  | "in progress"
  | "resolved"
  | "closed";

/** Every lifecycle stage, in the order the backend enum declares them. */
export const INCIDENCE_STATUSES: readonly IncidenceStatus[] = [
  "submitted",
  "in progress",
  "resolved",
  "closed",
];

/** One comment in an incidence thread (backend `CommentRead`). */
export interface Comment {
  id: number;
  incidence_id: number;
  author_id: number;
  author_email: string;
  body: string;
  /** ISO date-time. */
  created_at: string;
}

/** An incidence reported against one unit (backend `IncidenceRead`). */
export interface Incidence {
  id: number;
  unit_id: number;
  unit_identifier: string;
  created_by_id: number;
  created_by_email: string;
  title: string;
  description: string;
  status: IncidenceStatus;
  /** ISO date-time. */
  created_at: string;
  comments: Comment[];
}

/** Narrow an unknown value to an {@link IncidenceStatus}. */
export function isIncidenceStatus(
  value: unknown,
): value is IncidenceStatus {
  return (
    typeof value === "string" &&
    INCIDENCE_STATUSES.some((status) => status === value)
  );
}
