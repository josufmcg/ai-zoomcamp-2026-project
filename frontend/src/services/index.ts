export {
  api,
  apiFetch,
  ApiError,
  API_BASE_URL,
  clearToken,
  getToken,
  setToken,
  TOKEN_STORAGE_KEY,
} from "./apiClient";
export type { HttpMethod, RequestOptions } from "./apiClient";

export { clearSession, readSession, saveSession, USER_STORAGE_KEY } from "./session";

export { login } from "./auth";

// Domain calls (backlog task 15 onward). Each screen imports the module it
// needs; the barrel re-exports them so tests can import from one place.
export * as propertyApi from "./property";
export * as assignmentApi from "./assignments";
export * as billingApi from "./billing";
export * as maintenanceApi from "./maintenance";
export * as governanceApi from "./governance";

