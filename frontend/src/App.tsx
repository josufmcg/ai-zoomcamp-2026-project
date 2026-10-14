import { useEffect, useState } from "react";

import { api, ApiError } from "./services";

type HealthState =
  | { kind: "loading" }
  | { kind: "ok" }
  | { kind: "error"; message: string };

/**
 * Minimal application shell.
 *
 * It calls the backend `/healthz` endpoint through the shared API client so
 * the wiring between the SPA and the API is visible from the first run.
 */
export default function App() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    let active = true;

    api
      .get<{ status: string }>("/healthz")
      .then((data) => {
        if (active) {
          setHealth(
            data.status === "ok"
              ? { kind: "ok" }
              : { kind: "error", message: `Unexpected status: ${data.status}` },
          );
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        const message =
          error instanceof ApiError
            ? error.message
            : "Unable to reach the backend";
        setHealth({ kind: "error", message });
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center gap-6 p-8">
      <header className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          EFINGES
        </h1>
        <p className="mt-2 text-slate-600 dark:text-slate-400">
          Residential property management platform
        </p>
      </header>

      <section
        aria-live="polite"
        className="w-full rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800"
      >
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Backend status
        </h2>
        <p className="mt-2 text-lg">
          {health.kind === "loading" && (
            <span className="text-slate-500">Checking…</span>
          )}
          {health.kind === "ok" && (
            <span className="text-emerald-600 dark:text-emerald-400">
              Connected — API is healthy
            </span>
          )}
          {health.kind === "error" && (
            <span className="text-red-600 dark:text-red-400">
              {health.message}
            </span>
          )}
        </p>
      </section>
    </main>
  );
}
