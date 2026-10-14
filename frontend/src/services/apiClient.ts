/**
 * Centralized API client for the EFINGES backend.
 *
 * Every network call in the frontend must go through this module. It wraps
 * `fetch`, attaches a JSON content type, adds an optional Bearer token read
 * from local storage, and normalizes every failure into a thrown `Error`.
 */

/** Local storage key holding the JWT returned by `POST /auth/token`. */
export const TOKEN_STORAGE_KEY = "efinges.token";

/** Base URL of the backend API, injected at build time via `VITE_API_URL`. */
export const API_BASE_URL: string =
  import.meta.env.VITE_API_URL?.replace(/\/+$/, "") ?? "http://localhost:8000";

/** HTTP methods supported by the client. */
export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

/** Options accepted by {@link apiFetch}. */
export interface RequestOptions {
  /** HTTP method. Defaults to `GET`. */
  method?: HttpMethod;
  /** Request body. Plain objects are serialized to JSON automatically. */
  body?: unknown;
  /**
   * Form-encoded body. The client serializes it with `URLSearchParams` and sets
   * `Content-Type: application/x-www-form-urlencoded`.
   *
   * Required for the OAuth2 password flow (`POST /auth/token`), which is the
   * only endpoint that reads a form body instead of JSON. It cannot be combined
   * with `body`.
   */
  form?: Record<string, string>;
  /** Extra headers merged over the defaults. */
  headers?: Record<string, string>;
  /** Query string parameters; `undefined` values are skipped. */
  query?: Record<string, string | number | boolean | undefined | null>;
  /** Set to `true` to skip attaching the stored Bearer token. */
  skipAuth?: boolean;
  /** Abort signal forwarded to `fetch`. */
  signal?: AbortSignal;
}

/**
 * Error thrown for any non-2xx response or network failure.
 *
 * `status` is the HTTP status code, or `0` when the request never reached the
 * server (for example a network error or an aborted request).
 */
export class ApiError extends Error {
  readonly status: number;
  readonly payload: unknown;

  constructor(message: string, status: number, payload: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

/** Read the stored JWT, or `null` when the user is signed out. */
export function getToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    // Storage can be unavailable (private mode, SSR); treat as signed out.
    return null;
  }
}

/** Persist the JWT so later requests are authenticated. */
export function setToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // Ignore storage failures; the caller still holds the token in memory.
  }
}

/** Remove the stored JWT, signing the user out. */
export function clearToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Nothing to do if storage is unavailable.
  }
}

/** Build a query string from the given parameters, skipping empty values. */
function buildQueryString(
  query: RequestOptions["query"],
): string {
  if (!query) {
    return "";
  }
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) {
      continue;
    }
    params.append(key, String(value));
  }
  const serialized = params.toString();
  return serialized ? `?${serialized}` : "";
}

/** Extract a human-readable message from an error response body. */
function extractErrorMessage(status: number, payload: unknown): string {
  if (payload && typeof payload === "object") {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    // FastAPI validation errors return `detail` as a list of objects.
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown };
      if (typeof first?.msg === "string" && first.msg.trim()) {
        return first.msg;
      }
    }
    const message = (payload as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }
  return `Request failed with status ${status}`;
}

/** Parse a response body as JSON, falling back to text, then to `null`. */
async function parseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

/**
 * Perform an API request and return the parsed JSON body.
 *
 * @throws {ApiError} for any non-2xx response or network failure.
 */
export async function apiFetch<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    method = "GET",
    body,
    form,
    headers = {},
    query,
    skipAuth = false,
    signal,
  } = options;

  if (body !== undefined && form !== undefined) {
    throw new Error("Pass either `body` or `form` to apiFetch, never both.");
  }

  const url = `${API_BASE_URL}${path}${buildQueryString(query)}`;

  const requestHeaders: Record<string, string> = {
    Accept: "application/json",
    ...headers,
  };

  const token = skipAuth ? null : getToken();
  if (token) {
    requestHeaders.Authorization = `Bearer ${token}`;
  }

  let requestBody: BodyInit | undefined;
  if (form !== undefined) {
    requestHeaders["Content-Type"] = "application/x-www-form-urlencoded";
    requestBody = new URLSearchParams(form).toString();
  } else if (body !== undefined && body !== null) {
    requestHeaders["Content-Type"] = "application/json";
    requestBody = JSON.stringify(body);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: requestHeaders,
      body: requestBody,
      signal,
    });
  } catch (cause) {
    const message =
      cause instanceof Error ? cause.message : "Network request failed";
    throw new ApiError(message, 0, null);
  }

  const payload = await parseBody(response);

  if (!response.ok) {
    throw new ApiError(
      extractErrorMessage(response.status, payload),
      response.status,
      payload,
    );
  }

  return payload as T;
}

/** Convenience helpers for the common HTTP verbs. */
export const api = {
  get: <T = unknown>(path: string, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "GET" }),
  post: <T = unknown>(path: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "POST", body }),
  put: <T = unknown>(path: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "PUT", body }),
  patch: <T = unknown>(path: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "PATCH", body }),
  delete: <T = unknown>(path: string, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "DELETE" }),
};

export default api;
