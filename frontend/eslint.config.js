// ESLint flat configuration (backlog task 19).
//
// The CI pipeline runs `npm run lint` before the type check, the tests, and the
// production build. The rules mirror the `vite` + React + TypeScript template:
// ESLint's own recommended set, the type-aware-free TypeScript set (plain
// parsing, so lint stays fast), the React hooks rules, and the React Refresh
// rule that keeps the dev server's hot reload working.

import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  // Build output and coverage reports are generated, never linted.
  { ignores: ["dist", "coverage"] },

  // Application sources: browser globals, React hooks, and React Refresh.
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      ...tseslint.configs.recommended,
      reactHooks.configs.flat["recommended-latest"],
    ],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      "react-refresh": reactRefresh,
    },
    rules: {
      "react-refresh/only-export-components": [
        "error",
        { allowConstantExport: true },
      ],
    },
  },

  // Vitest tests and the shared test helpers also use the Vitest globals
  // (`describe`, `it`, `expect`, `vi`) enabled by `globals: true` in the Vite
  // config, so they are not undefined.
  {
    files: ["src/**/*.test.{ts,tsx}", "src/test/**/*.{ts,tsx}"],
    languageOptions: {
      globals: globals.vitest,
    },
  },
);
