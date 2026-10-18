/**
 * Manager bills (backlog task 16).
 *
 * Managers issue a manual bill for one of their properties and mark a bill paid.
 * Bills are listed through `GET /bills`, which the backend scopes to the
 * manager's communities and returns with the computed display status, so an
 * `overdue` bill is shown as such without the frontend touching the dates.
 *
 * Marking paid is a one-way transition: the backend rejects a second payment
 * with 409, so the button is hidden once the bill is paid.
 */

import { useCallback, useMemo, useState, type FormEvent } from "react";

import { useAsync } from "../../hooks/useAsync";
import { billingApi, propertyApi } from "../../services";
import type { Bill } from "../../types/billing";
import type { Unit } from "../../types/property";
import { formatAmount, formatDate, unitTypeLabel } from "../format";
import {
  AsyncSection,
  Notice,
  SectionCard,
  StatusBadge,
} from "../components";

/** Badge tone for a display status. */
function statusTone(status: Bill["status"]) {
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
function statusLabel(status: Bill["status"]): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

/** Today as an ISO `YYYY-MM-DD` string, for the issue-date default. */
function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/** One bill row with a pay action while it is unpaid. */
function BillRow({ bill, onPaid }: { bill: Bill; onPaid: () => void }) {
  const [paying, setPaying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function pay() {
    setPaying(true);
    setError(null);
    try {
      await billingApi.payBill(bill.id);
      onPaid();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to mark paid.");
    } finally {
      setPaying(false);
    }
  }

  return (
    <li
      className="rounded-md border border-slate-200 px-4 py-3 dark:border-slate-700"
      data-testid={`bill-${bill.id}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-medium text-slate-900 dark:text-slate-100">
            {bill.description}
          </p>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {bill.unit_identifier} ({unitTypeLabel(bill.unit_type)})
            {" · due "}
            {formatDate(bill.due_date)}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-semibold text-slate-900 dark:text-slate-100">
            {formatAmount(bill.amount)}
          </span>
          <span data-testid={`bill-status-${bill.id}`}>
            <StatusBadge label={statusLabel(bill.status)} tone={statusTone(bill.status)} />
          </span>
          {bill.status !== "paid" && (
            <button
              type="button"
              onClick={pay}
              disabled={paying}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
            >
              {paying ? "Saving…" : "Mark paid"}
            </button>
          )}
        </div>
      </div>
      {error && (
        <div className="mt-2">
          <Notice tone="red">{error}</Notice>
        </div>
      )}
    </li>
  );
}

export function ManagerBillsSection() {
  const loadBills = useCallback(() => billingApi.listBills(), []);
  const bills = useAsync<Bill[]>(loadBills);
  const loadUnits = useCallback(() => propertyApi.listUnits(), []);
  const units = useAsync<Unit[]>(loadUnits);

  const [unitId, setUnitId] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [issueDate, setIssueDate] = useState(todayIso);
  const [dueDate, setDueDate] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const unitOptions = useMemo(() => units.data ?? [], [units.data]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) {
      return;
    }
    const parsedUnit = Number(unitId);
    if (!parsedUnit || !amount.trim() || !description.trim() || !dueDate) {
      setError("Choose a property, an amount, a description, and a due date.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await billingApi.createBill({
        unit_id: parsedUnit,
        amount: amount.trim(),
        description: description.trim(),
        issue_date: issueDate || undefined,
        due_date: dueDate,
      });
      setAmount("");
      setDescription("");
      setDueDate("");
      bills.reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to issue the bill.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard
      title="Bills"
      description="Issue a manual bill for a property you manage, and mark bills paid."
    >
      <form
        className="mb-5 grid gap-3 rounded-md border border-slate-200 p-4 sm:grid-cols-2 dark:border-slate-700"
        onSubmit={handleSubmit}
      >
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          Property
          <select
            aria-label="Bill property"
            value={unitId}
            onChange={(event) => setUnitId(event.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          >
            <option value="">Select a property…</option>
            {unitOptions.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.identifier} ({unitTypeLabel(unit.unit_type)})
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          Amount
          <input
            type="text"
            inputMode="decimal"
            aria-label="Amount"
            placeholder="125.50"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300 sm:col-span-2">
          Description
          <input
            type="text"
            aria-label="Bill description"
            value={description}
            maxLength={500}
            onChange={(event) => setDescription(event.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          Issue date
          <input
            type="date"
            aria-label="Issue date"
            value={issueDate}
            onChange={(event) => setIssueDate(event.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          Due date
          <input
            type="date"
            aria-label="Due date"
            value={dueDate}
            onChange={(event) => setDueDate(event.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          />
        </label>
        {error && (
          <div className="sm:col-span-2">
            <Notice tone="red">{error}</Notice>
          </div>
        )}
        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
          >
            {saving ? "Issuing…" : "Issue bill"}
          </button>
        </div>
      </form>

      <AsyncSection
        state={bills}
        emptyMessage="No bills have been issued for your properties."
        render={(rows) => (
          <ul className="flex flex-col gap-3" data-testid="bill-list">
            {rows.map((bill) => (
              <BillRow key={bill.id} bill={bill} onPaid={bills.reload} />
            ))}
          </ul>
        )}
      />
    </SectionCard>
  );
}

export default ManagerBillsSection;
