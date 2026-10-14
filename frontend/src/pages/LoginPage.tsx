/**
 * Login page (backlog task 14).
 *
 * Calls `/auth/token` through the shared client, then `/auth/me` to learn the
 * role, and hands the resulting session to the auth provider. Persisting the
 * session is all this page does: the `/login` route notices the signed-in user
 * and redirects to the screen their role actually uses, or back to the path the
 * guard turned them away from.
 */

import { useState, type FormEvent } from "react";

import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../services";
import { Card, CenteredPanel } from "./components";

export default function LoginPage() {
  const { signIn } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) {
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      // Signing in updates the auth context, which makes the `/login` route
      // redirect on the next render. Nothing else is needed here on success.
      await signIn(email, password);
    } catch (cause) {
      const message =
        cause instanceof ApiError && cause.status === 401
          ? "Incorrect email or password."
          : cause instanceof Error
            ? cause.message
            : "Unable to sign in.";
      setError(message);
      setSubmitting(false);
    }
  }

  return (
    <CenteredPanel>
      <header className="text-center">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          EFINGES
        </h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          Residential property management platform
        </p>
      </header>

      <Card title="Sign in" subtitle="Use the email and password of your account.">
        <form className="flex flex-col gap-4" onSubmit={handleSubmit} noValidate>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
            Email
            <input
              type="email"
              name="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-slate-300">
            Password
            <input
              type="password"
              name="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
            />
          </label>

          {error && (
            <p role="alert" className="text-sm text-red-600 dark:text-red-400">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </Card>
    </CenteredPanel>
  );
}
