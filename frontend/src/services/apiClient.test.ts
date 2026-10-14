import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  api,
  apiFetch,
  ApiError,
  API_BASE_URL,
  clearToken,
  getToken,
  setToken,
  TOKEN_STORAGE_KEY,
} from "./apiClient";

/** Build a `Response`-like object for the mocked `fetch`. */
function jsonResponse(
  body: unknown,
  init: { status?: number; ok?: boolean } = {},
): Response {
  const status = init.status ?? 200;
  return {
    ok: init.ok ?? (status >= 200 && status < 300),
    status,
    text: async () => (body === null ? "" : JSON.stringify(body)),
  } as unknown as Response;
}

describe("apiClient", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns the parsed JSON body on success", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ status: "ok" }));

    const result = await apiFetch<{ status: string }>("/healthz");

    expect(result).toEqual({ status: "ok" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe(`${API_BASE_URL}/healthz`);
  });

  it("throws an ApiError carrying the status and detail on an error response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ detail: "Not authenticated" }, { status: 401 }),
    );

    await expect(apiFetch("/protected")).rejects.toBeInstanceOf(ApiError);

    await expect(apiFetch("/protected")).rejects.toMatchObject({
      status: 401,
      message: "Not authenticated",
    });
  });

  it("extracts the first message from a FastAPI validation error list", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        { detail: [{ msg: "field required", loc: ["body", "email"] }] },
        { status: 422 },
      ),
    );

    await expect(apiFetch("/users", { method: "POST", body: {} })).rejects.toMatchObject(
      { status: 422, message: "field required" },
    );
  });

  it("falls back to a generic message when the body has no detail", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(null, { status: 500 }),
    );

    await expect(apiFetch("/boom")).rejects.toMatchObject({
      status: 500,
      message: "Request failed with status 500",
    });
  });

  it("normalizes a network failure into an ApiError with status 0", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new TypeError("Failed to fetch"),
    );

    await expect(apiFetch("/healthz")).rejects.toMatchObject({
      status: 0,
      message: "Failed to fetch",
    });
  });

  it("attaches the stored Bearer token to requests", async () => {
    setToken("test-jwt");
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({}));

    await api.get("/me");

    const headers = fetchMock.mock.calls[0][1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer test-jwt");
  });

  it("omits the Authorization header when no token is stored", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({}));

    await api.get("/healthz");

    const headers = fetchMock.mock.calls[0][1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it("skips the token when skipAuth is set", async () => {
    setToken("test-jwt");
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({}));

    await apiFetch("/auth/token", { method: "POST", skipAuth: true });

    const headers = fetchMock.mock.calls[0][1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it("serializes a JSON body and sets the content type", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({}));

    await api.post("/auth/token", { username: "a", password: "b" });

    const init = fetchMock.mock.calls[0][1];
    const headers = init?.headers as Record<string, string>;
    expect(headers["Content-Type"]).toBe("application/json");
    expect(init?.body).toBe(JSON.stringify({ username: "a", password: "b" }));
  });

  it("builds a query string and skips empty values", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({}));

    await api.get("/bills", {
      query: { status: "pending", unit: 3, tag: undefined, page: null },
    });

    expect(fetchMock.mock.calls[0][0]).toBe(
      `${API_BASE_URL}/bills?status=pending&unit=3`,
    );
  });

  it("stores, reads, and clears the token", () => {
    expect(getToken()).toBeNull();

    setToken("abc");
    expect(getToken()).toBe("abc");
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBe("abc");

    clearToken();
    expect(getToken()).toBeNull();
  });
});
