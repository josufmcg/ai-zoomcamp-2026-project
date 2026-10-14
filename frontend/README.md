# EFINGES Frontend

React single-page application for EFINGES, a residential property management
platform. Built with Vite, TypeScript, and Tailwind CSS.

## Requirements

- Node.js 20 or newer (the repository is developed against Node 20 LTS).
- npm 10 or newer.

## Setup

```bash
cd frontend
npm install
```

## Run the development server

```bash
npm run dev
```

The app is then available at <http://localhost:3000>. It calls the backend
`/healthz` endpoint on load and shows the connection status.

The backend base URL is read from the `VITE_API_URL` environment variable and
defaults to `http://localhost:8000`. To point the app at another backend, create
a `.env.local` file:

```bash
VITE_API_URL=http://localhost:9000
```

## Run the tests

```bash
npm test          # single run (Vitest)
npm run test:watch  # watch mode
```

## Type-check and build

```bash
npm run typecheck   # tsc --noEmit
npm run build       # type-check then produce dist/
npm run preview     # serve the production build locally
```

## Makefile shortcuts

The repository root `Makefile` wraps the commands above:

```bash
make frontend-install   # npm install
make frontend-run       # start the dev server on port 3000
make frontend-test      # run the Vitest suite
make frontend-build     # type-check and build for production
```

## Project structure

```
src/
  App.tsx                 # application shell
  main.tsx                # React entry point
  styles.css              # Tailwind entry point
  services/
    apiClient.ts          # centralized API client (all backend calls)
    apiClient.test.ts     # Vitest smoke tests for the client
    index.ts              # public re-exports
  test/
    setup.ts              # Vitest setup (jest-dom matchers)
```

## API client

Every backend call must go through the centralized client in
`src/services/apiClient.ts`. It:

- prefixes requests with `VITE_API_URL`,
- sets a JSON `Content-Type` and `Accept` header,
- attaches an optional `Authorization: Bearer <token>` header read from local
  storage (`efinges.token`),
- normalizes every failure into a thrown `ApiError` carrying the HTTP `status`
  and the parsed response `payload`.

```ts
import { api, ApiError } from "./services";

try {
  const bills = await api.get<Bill[]>("/bills", { query: { status: "pending" } });
} catch (error) {
  if (error instanceof ApiError && error.status === 401) {
    // handle an expired session
  }
}
```

Use `setToken`, `getToken`, and `clearToken` to manage the stored JWT.
