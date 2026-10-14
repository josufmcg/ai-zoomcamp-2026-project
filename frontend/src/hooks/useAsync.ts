/**
 * Minimal async data-loading hook (backlog task 15).
 *
 * Every resident screen loads a list from the API on mount. Rather than repeat
 * the same `useState`/`useEffect`/cancellation dance in each section, they use
 * this hook, which reports the loading, error, and success states and exposes a
 * `reload` action so a mutation can refresh its list.
 *
 * The loader is read through a ref, so passing an inline arrow function does not
 * restart the request on every render; only the values in `deps` (plus an
 * explicit reload) do.
 *
 * The effect only subscribes to the request; it never sets state synchronously.
 * The loading and error flags are updated from the promise callbacks instead,
 * which avoids the cascading renders React warns about.
 */

import { useCallback, useEffect, useRef, useState } from "react";

/** What {@link useAsync} returns. */
export interface AsyncState<T> {
  /** The loaded value, or `null` before the first success. */
  data: T | null;
  /** The failure of the most recent attempt, or `null`. */
  error: Error | null;
  /** True while a request is in flight. */
  loading: boolean;
  /** Run the loader again, for example after a successful mutation. */
  reload: () => void;
}

/**
 * Run an async loader on mount and whenever `deps` change.
 *
 * Results are ignored once the component unmounts or the dependencies change,
 * so a slow response can never overwrite a newer one.
 */
export function useAsync<T>(
  loader: () => Promise<T>,
  deps: readonly unknown[] = [],
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);

  const loaderRef = useRef(loader);
  useEffect(() => {
    loaderRef.current = loader;
  });

  useEffect(
    () => {
      let cancelled = false;
      loaderRef.current().then(
        (result) => {
          if (!cancelled) {
            setData(result);
            setError(null);
            setLoading(false);
          }
        },
        (cause: unknown) => {
          if (!cancelled) {
            setError(cause instanceof Error ? cause : new Error(String(cause)));
            setLoading(false);
          }
        },
      );
      return () => {
        cancelled = true;
      };
    },
    // The hook is generic over the caller's dependency list, so this rule
    // cannot check the array statically. The loader itself is read from a ref,
    // so the request restarts only when `deps` or an explicit reload changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [...deps, nonce],
  );

  const reload = useCallback(() => {
    // The next data or error lands asynchronously, so mark the reload as in
    // flight here: the effect reacts to `deps` and this nonce.
    setLoading(true);
    setNonce((value) => value + 1);
  }, []);

  return { data, error, loading, reload };
}

export default useAsync;
