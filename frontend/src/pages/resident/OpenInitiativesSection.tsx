/**
 * "Open initiatives" resident section (backlog task 15).
 *
 * Lists the initiatives that are open for voting and, for each one, the
 * caller's eligible properties. Voting is **one ballot per eligible owned property**, so
 * the form lets the resident pick an option for every property they hold and
 * submits one request per unit. The selection and submit rules live in
 * {@link ./ballot} and are unit tested there.
 *
 * A unit that has already voted comes back from the API with a `vote_id`, so it
 * is shown as "voted" and is never sent a second ballot.
 */

import { useCallback, useState, type FormEvent } from "react";

import { useAsync } from "../../hooks/useAsync";
import { useI18n } from "../../i18n/I18nContext";
import { governanceApi } from "../../services";
import type {
  EligibleUnit,
  Initiative,
  InitiativeOption,
} from "../../types/governance";
import {
  clearBallot,
  pendingBallots,
  setBallot,
  votableUnits,
  type BallotSelections,
} from "./ballot";
import { formatDate, unitTypeLabel } from "../format";
import {
  AsyncSection,
  Notice,
  SectionCard,
  StatusBadge,
} from "../components";

/** Voting form for one open initiative. */
function InitiativeVoteCard({ initiative }: { initiative: Initiative }) {
  const { language, t } = useI18n();
  const loadEligible = useCallback(
    () => governanceApi.listEligibleUnits(initiative.id),
    [initiative.id],
  );
  const eligible = useAsync<EligibleUnit[]>(loadEligible);

  const [selections, setSelections] = useState<BallotSelections>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  // Seed the form from the API so a unit that already voted shows its choice.
  // Adjusting state while rendering (rather than from an effect) is React's
  // documented pattern for deriving state from a prop: the form re-seeds as
  // soon as the fetch resolves and never keeps stale selections.
  const [seededFrom, setSeededFrom] = useState<{ data: EligibleUnit[] | null }>({
    data: null,
  });
  if (eligible.data && eligible.data !== seededFrom.data) {
    const seed: BallotSelections = {};
    for (const unit of eligible.data) {
      if (unit.vote_id !== null && unit.option_id !== null) {
        seed[unit.unit_id] = unit.option_id;
      }
    }
    setSeededFrom({ data: eligible.data });
    setSelections(seed);
  }

  const units = eligible.data ?? [];
  const openUnits = votableUnits(units);
  const pending = pendingBallots(selections, units);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || pending.length === 0) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      for (const ballot of pending) {
        await governanceApi.castVote(
          initiative.id,
          ballot.unit_id,
          ballot.option_id,
        );
      }
      setDone(true);
      eligible.reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("Unable to cast vote."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <li
      className="rounded-md border border-slate-200 p-4 dark:border-slate-700"
      data-testid={`initiative-${initiative.id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-medium text-slate-900 dark:text-slate-100">
            {initiative.title}
          </p>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {t("Voting open")} {formatDate(initiative.opens_at, language)} –{" "}
            {formatDate(initiative.closes_at, language)}
          </p>
        </div>
        <StatusBadge
          label={initiative.is_open ? "Open" : "Closed"}
          tone={initiative.is_open ? "green" : "slate"}
        />
      </div>
      <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">
        {initiative.description}
      </p>

      <AsyncSection
        state={eligible}
        emptyMessage={t("None of your properties are eligible to vote in this initiative.")}
        render={() => (
          <form className="mt-3 flex flex-col gap-3" onSubmit={handleSubmit}>
            <ul className="flex flex-col gap-2" data-testid={`eligible-${initiative.id}`}>
              {units.map((unit) => (
                <EligibleUnitRow
                  key={unit.unit_id}
                  unit={unit}
                  options={initiative.options}
                  selected={selections[unit.unit_id] ?? null}
                  disabled={!initiative.is_open || unit.vote_id !== null}
                  onSelect={(optionId) =>
                    setSelections((current) =>
                      setBallot(current, unit.unit_id, optionId),
                    )
                  }
                  onClear={() =>
                    setSelections((current) =>
                      clearBallot(current, unit.unit_id),
                    )
                  }
                />
              ))}
            </ul>

            {error && <Notice tone="red">{error}</Notice>}
            {done && pending.length === 0 && (
              <Notice>{t("Your ballots were recorded.")}</Notice>
            )}

            {initiative.is_open && (
              <div className="flex items-center gap-3">
                <button
                  type="submit"
                  disabled={submitting || pending.length === 0}
                  className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
                >
                  {submitting
                    ? t("Submitting…")
                    : pending.length === 1
                      ? t("Cast {{count}} ballot", { count: pending.length })
                      : t("Cast {{count}} ballots", { count: pending.length })}
                </button>
                <span className="text-sm text-slate-600 dark:text-slate-400" data-testid={`pending-${initiative.id}`}>
                  {openUnits.length === 0
                    ? t("All your eligible properties have voted.")
                    : openUnits.length === 1
                      ? t("{{selected}} of {{eligible}} property selected.", {
                          selected: pending.length,
                          eligible: openUnits.length,
                        })
                      : t("{{selected}} of {{eligible}} properties selected.", {
                          selected: pending.length,
                          eligible: openUnits.length,
                        })}
                </span>
              </div>
            )}
          </form>
        )}
      />
    </li>
  );
}

/** One property row: an option picker when it may vote, a summary when it has. */
function EligibleUnitRow({
  unit,
  options,
  selected,
  disabled,
  onSelect,
  onClear,
}: {
  unit: EligibleUnit;
  options: InitiativeOption[];
  selected: number | null;
  disabled: boolean;
  onSelect: (optionId: number) => void;
  onClear: () => void;
}) {
  const { t } = useI18n();
  const voted = unit.vote_id !== null;
  const chosenLabel =
    options.find((option) => option.id === unit.option_id)?.label ?? t("unknown");

  return (
    <li
      className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-slate-200 px-3 py-2 dark:border-slate-700"
      data-testid={`unit-${unit.unit_id}`}
    >
      <div>
        <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
          {unit.unit_identifier}{" "}
          <span className="text-slate-500 dark:text-slate-400">
            ({t(unitTypeLabel(unit.unit_type))})
          </span>
        </p>
      </div>

      {voted ? (
        <StatusBadge label={`${t("Voted")}: ${chosenLabel}`} tone="green" />
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <span className="sr-only">
              {t("Option for property")} {unit.unit_identifier}
            </span>
            <select
              aria-label={`${t("Option for")} ${unit.unit_identifier}`}
              value={selected ?? ""}
              disabled={disabled}
              onChange={(event) => {
                const value = event.target.value;
                if (value === "") {
                  onClear();
                } else {
                  onSelect(Number(value));
                }
              }}
              className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
            >
              <option value="">{t("No ballot")}</option>
              {options.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
    </li>
  );
}

export function OpenInitiativesSection() {
  const loadOpen = useCallback(
    () => governanceApi.listInitiatives({ isOpen: true }),
    [],
  );
  const initiatives = useAsync<Initiative[]>(loadOpen);

  return (
    <SectionCard
      title="Open initiatives"
      description="Community votes you can take part in. You cast one ballot per eligible property."
    >
      <AsyncSection
        state={initiatives}
        emptyMessage="There are no open initiatives right now."
        render={(rows) => (
          <ul className="flex flex-col gap-4" data-testid="initiative-list">
            {rows.map((initiative) => (
              <InitiativeVoteCard
                key={initiative.id}
                initiative={initiative}
              />
            ))}
          </ul>
        )}
      />
    </SectionCard>
  );
}
