/**
 * Manager incidences (backlog task 16).
 *
 * Lists the incidences raised for the manager's units and lets the manager move
 * each one to its next lifecycle stage and reply in the thread. The status rule
 * lives in {@link ./incidenceStatus}: only the immediate next stage is offered,
 * and a closed incidence shows no button, because the backend rejects everything
 * else with 409.
 *
 * A status filter narrows the list to one stage, which is what a manager wants
 * when working through the outstanding requests.
 */

import { useCallback, useMemo, useState, type FormEvent } from "react";

import { useAsync } from "../../hooks/useAsync";
import { useI18n } from "../../i18n/I18nContext";
import { maintenanceApi } from "../../services";
import {
  INCIDENCE_STATUSES,
  type Incidence,
  type IncidenceStatus,
} from "../../types/maintenance";
import {
  isTerminal,
  nextStatuses,
  transitionLabel,
} from "./incidenceStatus";
import { formatDateTime } from "../format";
import {
  AsyncSection,
  Notice,
  SectionCard,
  StatusBadge,
} from "../components";

/** Badge tone for each lifecycle stage. */
function statusTone(status: IncidenceStatus) {
  switch (status) {
    case "submitted":
      return "slate" as const;
    case "in progress":
      return "amber" as const;
    case "resolved":
      return "green" as const;
    case "closed":
      return "blue" as const;
  }
}

/** One incidence with its transition control, thread, and comment box. */
function ManagerIncidenceCard({
  incidence,
  onChanged,
}: {
  incidence: Incidence;
  onChanged: () => void;
}) {
  const { language, t } = useI18n();
  const [comment, setComment] = useState("");
  const [posting, setPosting] = useState(false);
  const [advancing, setAdvancing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const next = nextStatuses(incidence.status);
  const terminal = isTerminal(incidence.status);

  async function advance() {
    if (next.length === 0 || advancing) {
      return;
    }
    setAdvancing(true);
    setError(null);
    try {
      await maintenanceApi.updateIncidenceStatus(incidence.id, next[0]);
      onChanged();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to change status.",
      );
    } finally {
      setAdvancing(false);
    }
  }

  async function handleComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = comment.trim();
    if (!body || posting) {
      return;
    }
    setPosting(true);
    setError(null);
    try {
      await maintenanceApi.addComment(incidence.id, body);
      setComment("");
      onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to comment.");
    } finally {
      setPosting(false);
    }
  }

  return (
    <li
      className="rounded-md border border-slate-200 p-4 dark:border-slate-700"
      data-testid={`incidence-${incidence.id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-900 dark:text-slate-100">
            {incidence.title}
          </p>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {incidence.unit_identifier}
            {" · "}
            {t("by")}{" "}
            {incidence.created_by_email}
            {" · "}
            {formatDateTime(incidence.created_at, language)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span data-testid={`incidence-status-${incidence.id}`}>
            <StatusBadge
              label={t(incidence.status)}
              tone={statusTone(incidence.status)}
            />
          </span>
          {!terminal && (
            <button
              type="button"
              onClick={advance}
              disabled={advancing}
              data-testid={`advance-${incidence.id}`}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
            >
              {advancing ? t("Saving…") : t(transitionLabel(next[0]))}
            </button>
          )}
        </div>
      </div>

      <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">
        {incidence.description}
      </p>

      <div className="mt-4 border-t border-slate-200 pt-3 dark:border-slate-700">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t("Discussion")} ({incidence.comments.length})
        </h4>
        {incidence.comments.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            {t("No comments yet.")}
          </p>
        ) : (
          <ul
            className="mt-2 flex flex-col gap-2"
            data-testid={`comments-${incidence.id}`}
          >
            {incidence.comments.map((entry) => (
              <li
                key={entry.id}
                className="rounded bg-slate-50 px-3 py-2 text-sm dark:bg-slate-900/40"
              >
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {entry.author_email} · {formatDateTime(entry.created_at, language)}
                </p>
                <p className="whitespace-pre-wrap text-slate-700 dark:text-slate-300">
                  {entry.body}
                </p>
              </li>
            ))}
          </ul>
        )}

        <form className="mt-3 flex gap-2" onSubmit={handleComment}>
          <input
            type="text"
            aria-label={`${t("Comment on")} ${incidence.title}`}
            placeholder={t("Reply to the resident…")}
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          />
          <button
            type="submit"
            disabled={posting || comment.trim().length === 0}
            className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
          >
            {posting ? t("Posting…") : t("Reply")}
          </button>
        </form>
        {error && (
          <div className="mt-2">
            <Notice tone="red">{error}</Notice>
          </div>
        )}
      </div>
    </li>
  );
}

export function ManagerIncidencesSection() {
  const { t } = useI18n();
  const [filter, setFilter] = useState<IncidenceStatus | "all">("all");

  const loadIncidences = useCallback(
    () =>
      maintenanceApi.listIncidences(
        filter === "all" ? {} : { status: filter },
      ),
    [filter],
  );
  const incidences = useAsync<Incidence[]>(loadIncidences, [filter]);

  const filters = useMemo<readonly (IncidenceStatus | "all")[]>(
    () => ["all", ...INCIDENCE_STATUSES],
    [],
  );

  return (
    <SectionCard
      title="Incidences"
      description="Maintenance requests for your properties. Advance the lifecycle and reply in the thread."
    >
      <div
        className="mb-4 flex flex-wrap gap-2"
        role="group"
        aria-label={t("Incidence status filter")}
      >
        {filters.map((option) => {
          const active = option === filter;
          return (
            <button
              key={option}
              type="button"
              aria-pressed={active}
              onClick={() => setFilter(option)}
              className={`rounded-md border px-3 py-1.5 text-sm font-medium transition ${
                active
                  ? "border-slate-900 bg-slate-900 text-white dark:border-slate-100 dark:bg-slate-100 dark:text-slate-900"
                  : "border-slate-300 text-slate-700 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
              }`}
            >
              {t(option === "all" ? "All" : option)}
            </button>
          );
        })}
      </div>

      <AsyncSection
        state={incidences}
        emptyMessage={
          filter === "all"
            ? "No incidences have been reported for your properties."
            : t("No incidences are {{status}}.", { status: t(filter) })
        }
        render={(rows) => (
          <ul className="flex flex-col gap-4" data-testid="incidence-list">
            {rows.map((incidence) => (
              <ManagerIncidenceCard
                key={incidence.id}
                incidence={incidence}
                onChanged={incidences.reload}
              />
            ))}
          </ul>
        )}
      />
    </SectionCard>
  );
}

export default ManagerIncidencesSection;
