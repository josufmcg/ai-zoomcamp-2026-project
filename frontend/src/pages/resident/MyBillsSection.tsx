/**
 * "My bills" resident section (backlog task 15).
 *
 * Shows the bills for the resident's own units with a status filter that
 * includes the computed `overdue` status. The backend already computed that
 * status (a pending bill past its due date), so this section only *selects* the
 * rows it was sent — it never derives a status from the dates itself. The
 * filtering rule lives in {@link filterBills} and is unit tested there.
 *
 * The list is fetched once and filtered in memory, which keeps the per-tab
 * counts consistent with the visible rows without a request per tab.
 */

import { useCallback, useMemo, useState } from "react";

import { useAsync } from "../../hooks/useAsync";
import { billingApi } from "../../services";
import type { Bill, BillDisplayStatus } from "../../types/billing";
import {
  BILL_FILTERS,
  billFilterLabel,
  countBillsByFilter,
  filterBills,
  type BillFilter,
} from "./billFilter";
import { formatAmount, formatDate, unitTypeLabel } from "../format";
import { AsyncSection, SectionCard, StatusBadge } from "../components";

/** Badge tone for each display status. */
function statusTone(status: BillDisplayStatus) {
  switch (status) {
    case "paid":
      return "green" as const;
    case "overdue":
      return "red" as const;
    case "pending":
      return "amber" as const;
  }
}

/** Title-case label for a display status. */
function statusLabel(status: BillDisplayStatus): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export function MyBillsSection() {
  const [filter, setFilter] = useState<BillFilter>("all");

  const loadBills = useCallback(() => billingApi.listBills(), []);
  const request = useAsync<Bill[]>(loadBills);

  const bills = useMemo(() => request.data ?? [], [request.data]);
  const counts = useMemo(() => countBillsByFilter(bills), [bills]);
  const visible = useMemo(() => filterBills(bills, filter), [bills, filter]);

  return (
    <SectionCard
      title="My bills"
      description="Bills issued for your units. Overdue is computed from the due date."
    >
      <div
        className="mb-4 flex flex-wrap gap-2"
        role="group"
        aria-label="Bill status filter"
      >
        {BILL_FILTERS.map((option) => {
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
              {billFilterLabel(option)}{" "}
              <span data-testid={`bill-count-${option}`}>
                ({counts[option]})
              </span>
            </button>
          );
        })}
      </div>

      <AsyncSection
        state={request}
        emptyMessage={
          filter === "all"
            ? "You have no bills."
            : `No ${billFilterLabel(filter).toLowerCase()} bills.`
        }
        isEmpty={() => visible.length === 0}
        render={() => (
          <ul className="flex flex-col gap-3" data-testid="bill-list">
            {visible.map((bill) => (
              <li
                key={bill.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 px-4 py-3 dark:border-slate-700"
                data-testid={`bill-${bill.id}`}
              >
                <div>
                  <p className="font-medium text-slate-900 dark:text-slate-100">
                    {bill.description}
                  </p>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    {bill.unit_identifier} ({unitTypeLabel(bill.unit_type)})
                    {" · "}
                    issued {formatDate(bill.issue_date)}
                    {" · "}
                    due {formatDate(bill.due_date)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-slate-900 dark:text-slate-100">
                    {formatAmount(bill.amount)}
                  </span>
                  <span data-testid={`bill-status-${bill.id}`}>
                    <StatusBadge
                      label={statusLabel(bill.status)}
                      tone={statusTone(bill.status)}
                    />
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      />
    </SectionCard>
  );
}
