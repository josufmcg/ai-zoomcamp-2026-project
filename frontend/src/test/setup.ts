import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";

// Sessions live in local storage, so every test starts from a signed-out state
// and never inherits a token written by an earlier test.
beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
});
