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

The app is then available at <http://localhost:3000>. It opens on the login
screen; after signing in you land on the screen for your role (resident,
manager, or administrator). The JWT and the user profile are kept in local
storage so a refresh stays signed in, and the shared API client attaches the
Bearer token to every request.

The backend base URL is read from the `VITE_API_URL` environment variable and
defaults to `http://localhost:8000`. To point the app at another backend, create
a `.env.local` file:

```bash
VITE_API_URL=http://localhost:9000
```

## Routes and authentication

| Route | Access | Screen |
| --- | --- | --- |
| `/login` | signed out | Email and password form (`POST /auth/token`) |
| `/` | any | Redirects to the role's home screen, or to `/login` |
| `/overview` | any signed-in role | Shared landing screen |
| `/resident` | resident | Resident screens (backlog task 15) |
| `/manager` | manager | Manager screens (backlog task 16) |
| `/admin` | administrator | Administrator screens (backlog task 17) |
| `/forbidden` | any signed-in role | Shown when a role lacks access |

Guarding lives in `src/auth/RequireAuth.tsx`: a signed-out visitor is redirected
to `/login` with the requested path preserved, and a signed-in user whose role
is not allowed is redirected to `/forbidden`. This is a usability guard only —
the backend re-checks the role on every request and returns 403 regardless of
what the UI shows.

The sidebar links come from `src/auth/navigation.ts`, which is a plain data
model filtered by role, so the shell and the tests agree on what each role sees.

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
  App.tsx                 # routes and the login/role redirects
  main.tsx                # React entry point (router + auth provider)
  styles.css              # Tailwind entry point
  auth/
    AuthContext.ts        # context handle and the useAuth hook
    AuthProvider.tsx      # restores the stored session, signIn/signOut
    RequireAuth.tsx       # route guarding by session and role
    navigation.ts         # role-filtered navigation model
  pages/
    LoginPage.tsx         # email and password form
    AppShell.tsx          # header, sidebar, routed content
    HomePages.tsx         # overview and per-role landing screens
    components.tsx        # shared presentational pieces
  services/
    apiClient.ts          # centralized API client (all backend calls)
    auth.ts               # POST /auth/token plus GET /auth/me
    session.ts            # persistence of the token and profile
    index.ts              # public re-exports
  types/
    auth.ts               # UserRole, User, and session types
  test/
    setup.ts              # Vitest setup (jest-dom matchers, cleanup)
    helpers.tsx           # render helpers and fixtures
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

Use `setToken`, `getToken`, and `clearToken` to manage the stored JWT. The login
flow is the one exception to the JSON default: `POST /auth/token` reads an
OAuth2 form body, so pass `form` instead of `body`:

```ts
const { access_token } = await api.post<{ access_token: string }>(
  "/auth/token",
  undefined,
  { form: { username: email, password }, skipAuth: true },
);
```
