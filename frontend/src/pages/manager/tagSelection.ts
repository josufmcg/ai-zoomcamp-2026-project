/**
 * Tag (and other id-list) selection helpers for the manager screens
 * (backlog tasks 16 and 19).
 *
 * The manager screens toggle ids in and out of a list in three places: the
 * building form, the unit form, and the tag editor. They used to share the
 * helper from the component module, which broke React Refresh's
 * "a module should only export components" rule. It lives in a plain module so
 * the components keep hot reloading.
 */

/** Add or remove one value from a list, returning a new list. */
export function toggleId<T>(values: readonly T[], value: T): T[] {
  return values.includes(value)
    ? values.filter((existing) => existing !== value)
    : [...values, value];
}
