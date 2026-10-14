/**
 * Reusable form pieces for the manager screens (backlog task 16).
 *
 * Tags are free-text labels a manager attaches to buildings, units, and
 * initiative scopes, so the same checkbox list appears in three places. Keeping
 * it in one controlled component means the three screens agree on how a tag is
 * toggled and how the selection is labelled.
 */

import { useState } from "react";

import type { Tag } from "../../types/property";
import { Notice } from "../components";
import { toggleId } from "./tagSelection";

/** Controlled checkbox list of every tag, with the current selection checked. */
export function TagChecklist({
  tags,
  selected,
  onToggle,
  legend = "Tags",
}: {
  tags: readonly Tag[];
  selected: readonly number[];
  onToggle: (tagId: number) => void;
  legend?: string;
}) {
  if (tags.length === 0) {
    return (
      <fieldset>
        <legend className="text-sm font-medium text-slate-700 dark:text-slate-300">
          {legend}
        </legend>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          No tags yet.
        </p>
      </fieldset>
    );
  }

  return (
    <fieldset>
      <legend className="text-sm font-medium text-slate-700 dark:text-slate-300">
        {legend}
      </legend>
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
        {tags.map((tag) => (
          <label
            key={tag.id}
            className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300"
          >
            <input
              type="checkbox"
              checked={selected.includes(tag.id)}
              onChange={() => onToggle(tag.id)}
            />
            #{tag.name}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/**
 * Collapsed tag editor for one building or unit.
 *
 * The manager sees the current tags inline and only expands the checkbox list
 * when they choose to change them, so the tree stays readable. The draft is
 * local until Save, so cancelling leaves the row untouched.
 */
export function TagEditor({
  tags,
  selectedTagIds,
  onSave,
  label,
}: {
  tags: readonly Tag[];
  selectedTagIds: readonly number[];
  onSave: (tagIds: number[]) => Promise<void>;
  label: string;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<number[]>([...selectedTagIds]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function openEditor() {
    setDraft([...selectedTagIds]);
    setError(null);
    setOpen(true);
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await onSave(draft);
      setOpen(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save tags.");
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={openEditor}
        className="text-xs font-medium text-slate-600 underline hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100"
      >
        Edit tags
      </button>
    );
  }

  return (
    <div className="mt-2 rounded-md border border-slate-200 p-3 dark:border-slate-700">
      <TagChecklist
        tags={tags}
        selected={draft}
        onToggle={(tagId) => setDraft((current) => toggleId(current, tagId))}
        legend={`${label} tags`}
      />
      {error && (
        <div className="mt-2">
          <Notice tone="red">{error}</Notice>
        </div>
      )}
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          onClick={save}
          disabled={saving}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
        >
          {saving ? "Saving…" : "Save tags"}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-100 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
