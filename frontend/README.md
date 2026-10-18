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
| `/resident/units`, `/resident/bills`, `/resident/incidences`, `/resident/initiatives` | resident | Separate properties, bills, incidences, and open initiatives screens |
| `/manager/properties`, `/manager/assignments`, `/manager/bills`, `/manager/incidences`, `/manager/initiatives` | manager | Separate property tree, assignments, bills, incidences, and initiatives screens |
| `/admin/users`, `/admin/properties` | administrator | Separate user management and global property overview screens |
| `/resident`, `/manager`, `/admin` | matching role | Redirects to that role's first screen |
| `/forbidden` | any signed-in role | Shown when a role lacks access |

Guarding lives in `src/auth/RequireAuth.tsx`: a signed-out visitor is redirected
to `/login` with the requested path preserved, and a signed-in user whose role
is not allowed is redirected to `/forbidden`. This is a usability guard only —
the backend re-checks the role on every request and returns 403 regardless of
what the UI shows.

The sidebar links come from `src/auth/navigation.ts`, which is a plain data
model filtered by role, so the shell and the tests agree on what each role sees.

## Resident screens (backlog task 15)

The resident's four areas are separate sidebar destinations and routes. Each
screen loads its own data through the shared API client and renders its own
loading, error, and empty state:

- **My properties** — `GET /auth/me/units`, showing the ownership flag and tags.
- **My bills** — `GET /bills`, with a status filter that includes the computed
  `overdue` status. The backend computes `overdue` from the due date (a pending
  bill past its due date); the frontend only selects on the value it was sent
  and never derives a status from dates itself.
- **My incidences** — `GET /incidences` with an embedded comment thread per
  incidence, a form to report a new incidence against a property you own or rent, and a
  comment box per thread. The status is manager-controlled, so the resident
  screen shows it but never offers to change it.
- **Open initiatives** — `GET /initiatives?is_open=true` plus
  `GET /initiatives/{id}/eligible-units`. Voting is **one ballot per eligible
property** (stored as a unit by the API), so the form submits one
`POST /initiatives/{id}/votes` request per property the resident selected; a
property that already voted is shown as voted and is never sent a second ballot.

The two rules that need focused tests live in their own modules:
`src/pages/resident/billFilter.ts` (the status filter) and
`src/pages/resident/ballot.ts` (the per-unit ballot selection and submission),
with the corresponding `*.test.ts` files and component-level tests beside them.

## Manager screens (backlog task 16)

The manager's five areas are separate sidebar destinations and routes. Each
screen loads its own data through the shared API client and renders its own
loading, error, and empty state:

- **Property tree** — `GET /communities`, `GET /buildings`, `GET /units`, and
  `GET /tags`, grouped in memory into communities → buildings → properties. A manager
  adds buildings to a community and properties to a building, and edits the tags
  of a building or property. Every write refreshes the affected lists, so the tree always
  shows what the backend stored rather than an optimistic guess.
- **Resident assignments** — `GET /assignments` with a form to assign an active
  resident (`GET /residents`, a manager-accessible directory that never exposes
  the administrator-only `/users` endpoints) to one of the manager's properties, and
  a remove action.
- **Bills** — `GET /bills` (scoped to the manager's communities by the backend)
  with a form to issue a manual bill (`POST /bills`) and a "Mark paid" action
  (`POST /bills/{id}/pay`) offered only while the bill is unpaid, because the
  backend rejects a second payment with 409. `overdue` is always the value the
  API computed, never derived from dates on the client.
- **Incidences** — `GET /incidences` with a status filter, a per-incidence
  transition button (`PATCH /incidences/{id}/status`) that only offers the
  immediate next stage, and a reply box per thread.
- **Initiatives** — `GET /initiatives` with the options and running ballot
  counts, and a form to create a new initiative with two or more options and an
  eligible scope filter over communities, buildings, property types, and tags
  (`POST /initiatives`). Property wording in the interface maps to the API's
  existing unit terminology.

The two rules that need focused tests live in their own modules:
`src/pages/manager/incidenceStatus.ts` mirrors the backend lifecycle so the
screen only offers a legal transition, and
`src/pages/manager/initiativeScope.ts` validates an initiative draft and turns it
into the request body (the scope combines with AND, and an empty scope means
"every property"; the API represents each property as a unit). Both have
`*.test.ts` files beside them, with component-level
tests for the transition controls and the scope form.

## Administrator screens (backlog task 17)

The administrator's two areas are separate sidebar destinations and routes:

- **User accounts** — `GET /users` with filters by role and activation state, a
  form to create an account (`POST /users`), a role selector per row
  (`PATCH /users/{id}`), and an activate/deactivate action. Responses are always
  the public `UserRead` shape, which never carries the password hash. An
  administrator cannot demote or deactivate their own account: those controls
  are refused with a short explanation instead of failing on the server, which
  enforces the same rule.
- **Global property overview** — `GET /communities`, `GET /buildings`, and
  `GET /units`, grouped in memory into communities → buildings → units. The
  administrator is unrestricted, so this shows the whole firm. It is read-only:
  the property tree is the manager's to maintain.

The create-form validation and self-action guards live in
`src/pages/admin/userForm.ts` (with a `*.test.ts` beside it), keeping the
components thin and the rules testable without rendering.

## Run the tests

```bash
npm test          # single run (Vitest)
npm run test:watch  # watch mode
```

## Lint

ESLint (flat config, `eslint.config.js`) checks the sources and the tests; it is
part of the CI pipeline (backlog task 19) and runs before the tests:

```bash
npm run lint
```

The config applies ESLint's recommended rules, the TypeScript recommended rules,
the React hooks rules, and the React Refresh rule, and gives the `*.test.*`
files and `src/test/` the Vitest globals so `describe`/`it`/`expect`/`vi` are
recognized. `make lint` at the repository root runs it together with the backend
lint.

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
    HomePages.tsx         # overview and error screens
    ResidentHomePage.tsx  # resident screen container (task 15)
    ManagerHomePage.tsx   # manager screen container (task 16)
    AdminHomePage.tsx     # administrator screen container (task 17)
    SectionPages.tsx      # dedicated routes for the additional role sections
    components.tsx        # shared presentational pieces
    format.ts             # role, unit type, ownership, date, and money formatters
    resident/
      MyUnitsSection.tsx         # the resident's units
      MyBillsSection.tsx         # bills with a status filter
      MyIncidencesSection.tsx    # incidences and comment threads
      OpenInitiativesSection.tsx # open initiatives and per-unit voting
      billFilter.ts              # bill status filter logic (tested)
      ballot.ts                  # per-unit ballot selection (tested)
    manager/
      PropertyTreeSection.tsx        # communities, buildings, units, tags
      AssignmentsSection.tsx         # resident assignments
      ManagerBillsSection.tsx        # issue and pay bills
      ManagerIncidencesSection.tsx   # lifecycle transitions and replies
      InitiativesSection.tsx         # create initiatives with a scope
      TagChecklist.tsx               # tag checklist and editor
      tagSelection.ts                # add/remove id from a list (tested seam)
      incidenceStatus.ts             # lifecycle transition mirror (tested)
      initiativeScope.ts             # draft validation and payload (tested)
    admin/
      UsersSection.tsx               # user management (create, roles, active)
      GlobalOverviewSection.tsx      # read-only global property overview
      userForm.ts                    # create validation and guards (tested)
  hooks/
    useAsync.ts           # minimal async loading state helper
  services/
    apiClient.ts          # centralized API client (all backend calls)
    auth.ts               # POST /auth/token plus GET /auth/me
    session.ts            # persistence of the token and profile
    property.ts           # property tree CRUD and GET /auth/me/units
    billing.ts            # bills
    maintenance.ts        # incidences and comments
    governance.ts         # initiatives, eligible units, votes
    assignments.ts        # assignments and the resident directory
    users.ts              # administrator user management
    index.ts              # public re-exports
  types/
    auth.ts               # UserRole, User, and session types
    property.ts           # UnitType, OwnershipType, Tag, MyUnit
    billing.ts            # Bill and BillDisplayStatus
    maintenance.ts        # Incidence, IncidenceStatus, Comment
    governance.ts         # Initiative, EligibleUnit, Vote, VoteResult
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
