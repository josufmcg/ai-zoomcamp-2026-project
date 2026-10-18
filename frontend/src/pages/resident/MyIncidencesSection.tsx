/**
 * "My incidences" resident section (backlog task 15).
 *
 * A resident reports maintenance issues against their own properties and discusses
 * them with managers in a single comment thread per incidence. The list
 * endpoint scopes to the caller and embeds each thread, so one fetch renders
 * the whole section; creating an incidence or posting a comment refreshes it.
 *
 * The incidence status is manager-controlled (only the immediate next lifecycle
 * stage is allowed), so this resident screen displays the status but never
 * offers to change it.
 */

import { useCallback, useMemo, useState, type FormEvent } from "react";

import { useAsync } from "../../hooks/useAsync";
import { useI18n } from "../../i18n/I18nContext";
import { maintenanceApi, propertyApi } from "../../services";
import type { Incidence, IncidenceStatus } from "../../types/maintenance";
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

/** One incidence with its thread and a comment box. */
function IncidenceCard({
  incidence,
  onCommented,
}: {
  incidence: Incidence;
  onCommented: () => void;
}) {
  const { language, t } = useI18n();
  const [comment, setComment] = useState("");
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      onCommented();
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
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-medium text-slate-900 dark:text-slate-100">
            {incidence.title}
          </p>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {incidence.unit_identifier}
            {" · "}
            {t("submitted")}{" "}
            {formatDateTime(incidence.created_at, language)}
          </p>
        </div>
        <span data-testid={`incidence-status-${incidence.id}`}>
          <StatusBadge
            label={t(incidence.status)}
            tone={statusTone(incidence.status)}
          />
        </span>
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
          <ul className="mt-2 flex flex-col gap-2" data-testid={`comments-${incidence.id}`}>
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
            placeholder={t("Write a comment…")}
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          />
          <button
            type="submit"
            disabled={posting || comment.trim().length === 0}
            className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
          >
            {posting ? t("Posting…") : t("Comment")}
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

export function MyIncidencesSection() {
  const { t } = useI18n();
  const loadIncidences = useCallback(() => maintenanceApi.listIncidences(), []);
  const incidences = useAsync<Incidence[]>(loadIncidences);
  const loadUnits = useCallback(() => propertyApi.listMyUnits(), []);
  const units = useAsync(loadUnits);

  const [unitId, setUnitId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const unitOptions = useMemo(() => units.data ?? [], [units.data]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) {
      return;
    }
    const parsedUnitId = Number(unitId);
    if (!parsedUnitId || !title.trim() || !description.trim()) {
      setError(t("Choose a property and fill in both fields."));
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await maintenanceApi.createIncidence({
        unit_id: parsedUnitId,
        title: title.trim(),
        description: description.trim(),
      });
      setTitle("");
      setDescription("");
      incidences.reload();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to submit incidence.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <SectionCard
      title={t("My incidences")}
      description={t("Report an issue and track the conversation with your manager.")}
    >
      <form
        className="mb-5 grid gap-3 rounded-md border border-slate-200 p-4 dark:border-slate-700"
        onSubmit={handleCreate}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
            {t("Property")}
            <select
              aria-label={t("Property")}
              value={unitId}
              onChange={(event) => setUnitId(event.target.value)}
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
            >
              <option value="">{t("Select a property…")}</option>
              {unitOptions.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unit.identifier}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
            {t("Title")}
            <input
              type="text"
              aria-label={t("Title")}
              value={title}
              maxLength={200}
              onChange={(event) => setTitle(event.target.value)}
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
            />
          </label>
        </div>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          {t("Description")}
          <textarea
            aria-label={t("Description")}
            rows={3}
            value={description}
            maxLength={4000}
            onChange={(event) => setDescription(event.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          />
        </label>
        {error && <Notice tone="red">{error}</Notice>}
        <div>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
          >
            {submitting ? t("Submitting…") : t("Submit incidence")}
          </button>
        </div>
      </form>

      <AsyncSection
        state={incidences}
        emptyMessage="You have not reported any incidences."
        render={(rows) => (
          <ul className="flex flex-col gap-4" data-testid="incidence-list">
            {rows.map((incidence) => (
              <IncidenceCard
                key={incidence.id}
                incidence={incidence}
                onCommented={incidences.reload}
              />
            ))}
          </ul>
        )}
      />
    </SectionCard>
  );
}
