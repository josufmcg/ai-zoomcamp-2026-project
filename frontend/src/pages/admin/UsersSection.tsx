/**
 * Administrator user management (backlog task 17).
 *
 * Lists every account with its role and activation state, lets the
 * administrator create a new account, change a role, and activate or
 * deactivate an account. All writes go through the shared API client and
 * refresh the list afterwards so the screen shows what the backend stored.
 *
 * The two edits are guarded client-side with the same rules the backend
 * enforces: the form logic lives in `userForm.ts`, and an administrator cannot
 * demote or deactivate their own account, so those controls are disabled with a
 * short explanation instead of failing on the server.
 */

import { useCallback, useMemo, useState, type FormEvent } from "react";

import { useAuth } from "../../auth/AuthContext";
import { useAsync } from "../../hooks/useAsync";
import { userApi } from "../../services";
import { USER_ROLES, type User, type UserRole } from "../../types/auth";
import { roleLabel } from "../format";
import {
  AsyncSection,
  Notice,
  SectionCard,
  StatusBadge,
} from "../components";
import {
  deactivateBlockedReason,
  emptyUserDraft,
  roleChangeBlockedReason,
  roleChangePatch,
  toCreatePayload,
  validateUserDraft,
  type UserDraft,
} from "./userForm";

/** Collapsed form that creates one account. */
function NewUserForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<UserDraft>(emptyUserDraft);
  const [errors, setErrors] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) {
      return;
    }
    const problems = validateUserDraft(draft);
    if (problems.length > 0) {
      setErrors(problems);
      return;
    }
    setSaving(true);
    setErrors([]);
    try {
      await userApi.createUser(toCreatePayload(draft));
      setDraft(emptyUserDraft());
      setOpen(false);
      onCreated();
    } catch (cause) {
      setErrors([
        cause instanceof Error ? cause.message : "Unable to create the user.",
      ]);
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mb-5 text-sm font-medium text-slate-600 underline hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100"
      >
        Add user
      </button>
    );
  }

  return (
    <form
      className="mb-5 grid gap-3 rounded-md border border-slate-200 p-4 sm:grid-cols-3 dark:border-slate-700"
      onSubmit={handleSubmit}
    >
      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
        Email
        <input
          type="email"
          aria-label="Email"
          value={draft.email}
          maxLength={320}
          onChange={(event) =>
            setDraft((current) => ({ ...current, email: event.target.value }))
          }
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
        Password
        <input
          type="password"
          aria-label="Password"
          value={draft.password}
          maxLength={128}
          onChange={(event) =>
            setDraft((current) => ({ ...current, password: event.target.value }))
          }
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
        Role
        <select
          aria-label="New user role"
          value={draft.role}
          onChange={(event) =>
            setDraft((current) => ({
              ...current,
              role: event.target.value as UserRole,
            }))
          }
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
        >
          {USER_ROLES.map((role) => (
            <option key={role} value={role}>
              {roleLabel(role)}
            </option>
          ))}
        </select>
      </label>
      {errors.length > 0 && (
        <div className="sm:col-span-3">
          <Notice tone="red">
            <ul className="list-disc pl-4">
              {errors.map((problem) => (
                <li key={problem}>{problem}</li>
              ))}
            </ul>
          </Notice>
        </div>
      )}
      <div className="flex gap-2 sm:col-span-3">
        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
        >
          {saving ? "Creating…" : "Create user"}
        </button>
        <button
          type="button"
          onClick={() => {
            setDraft(emptyUserDraft());
            setErrors([]);
            setOpen(false);
          }}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

/** One account row with a role selector and an activation toggle. */
function UserRow({
  user,
  actorId,
  onChanged,
}: {
  user: User;
  actorId: number;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ownRow = user.id === actorId;

  async function changeRole(role: UserRole) {
    const reason = roleChangeBlockedReason(actorId, user, role);
    if (reason) {
      setError(reason);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await userApi.updateUser(user.id, roleChangePatch(role));
      onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to change role.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive() {
    const reason = user.is_active ? deactivateBlockedReason(actorId, user) : null;
    if (reason) {
      setError(reason);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await userApi.updateUser(user.id, { is_active: !user.is_active });
      onChanged();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to change the account.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <li
      className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 px-4 py-3 dark:border-slate-700"
      data-testid={`user-${user.id}`}
    >
      <div>
        <p className="font-medium text-slate-900 dark:text-slate-100">
          {user.email}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <StatusBadge label={roleLabel(user.role)} tone="blue" />
          <StatusBadge
            label={user.is_active ? "Active" : "Inactive"}
            tone={user.is_active ? "green" : "slate"}
          />
          {ownRow && (
            <span className="text-xs text-slate-500 dark:text-slate-400">
              (you)
            </span>
          )}
        </div>
        {error && (
          <div className="mt-1">
            <Notice tone="red">{error}</Notice>
          </div>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
          <span className="sr-only">Role</span>
          <select
            aria-label={`Role for ${user.email}`}
            value={user.role}
            disabled={busy}
            onChange={(event) => changeRole(event.target.value as UserRole)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-slate-900 outline-none focus:border-slate-500 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          >
            {USER_ROLES.map((role) => (
              <option key={role} value={role}>
                {roleLabel(role)}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={toggleActive}
          disabled={busy}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          {user.is_active ? "Deactivate" : "Reactivate"}
        </button>
      </div>
    </li>
  );
}

export function UsersSection() {
  const { user: actor } = useAuth();
  const [roleFilter, setRoleFilter] = useState<UserRole | "">("");
  const [activeFilter, setActiveFilter] = useState<"" | "active" | "inactive">(
    "",
  );

  const loadUsers = useCallback(
    () =>
      userApi.listUsers({
        role: roleFilter || undefined,
        isActive:
          activeFilter === ""
            ? undefined
            : activeFilter === "active",
      }),
    [roleFilter, activeFilter],
  );
  const users = useAsync<User[]>(loadUsers, [roleFilter, activeFilter]);

  const actorId = actor?.id ?? -1;
  const rows = useMemo(() => users.data ?? [], [users.data]);

  return (
    <SectionCard
      title="User accounts"
      description="Create accounts, assign roles, and activate or deactivate access."
    >
      <NewUserForm onCreated={users.reload} />

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          Filter by role
          <select
            aria-label="Filter by role"
            value={roleFilter}
            onChange={(event) =>
              setRoleFilter(event.target.value as UserRole | "")
            }
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          >
            <option value="">All roles</option>
            {USER_ROLES.map((role) => (
              <option key={role} value={role}>
                {roleLabel(role)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
          Filter by status
          <select
            aria-label="Filter by status"
            value={activeFilter}
            onChange={(event) =>
              setActiveFilter(event.target.value as "" | "active" | "inactive")
            }
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          >
            <option value="">All accounts</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </label>
      </div>

      <AsyncSection
        state={users}
        emptyMessage="No accounts match the current filters."
        render={() => (
          <ul className="flex flex-col gap-3" data-testid="user-list">
            {rows.map((row) => (
              <UserRow
                key={row.id}
                user={row}
                actorId={actorId}
                onChanged={users.reload}
              />
            ))}
          </ul>
        )}
      />
    </SectionCard>
  );
}

export default UsersSection;
