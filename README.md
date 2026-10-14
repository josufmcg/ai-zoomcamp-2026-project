# EFINGES

EFINGES is a residential property management platform for property management
firms: property hierarchies, manual billing, maintenance incidences with
comment threads, and community initiatives with per-unit voting.

## The problem EFINGES solves

A property management firm runs many communities, each with several buildings
and many units — apartments, garages, and storage units that are owned or
rented individually by residents. Keeping that hierarchy, the billing per unit,
the maintenance conversations, and community votes in one place usually means
spreadsheets, email threads, and phone calls, with no single source of truth
and no reliable way to keep each resident's data separate from the rest.

EFINGES turns that into one system with three roles and a strict, server-side
access boundary:

- **Administrators** manage user accounts across the whole firm and see every
  property.
- **Managers** maintain the communities they are assigned to: the property
  tree, tags, resident assignments, manual bills, incidence status, and
  initiatives.
- **Residents** see only their own units, bills, incidences, and votes, and
  reach their manager only through comment threads on an incidence.

### Expected behavior

- Communities contain buildings, and buildings contain units; a unit is an
  apartment, a garage, or a storage unit, and is billed individually.
- A resident can hold several units. Each unit has at most one resident at a
  time, so assigning the same unit twice is rejected.
- Bills are issued manually by managers. A bill is `pending` or `paid`; a
  pending bill past its due date is reported as **overdue** — a computed
  value, never a stored status.
- Maintenance incidences follow `submitted → in progress → resolved → closed`
  in that order, only one step at a time, and `closed` is terminal. All
  resident–manager communication happens in comment threads on the incidence.
- Initiatives let managers run a vote with two or more options over an
  eligible scope; a resident casts **one ballot per eligible owned unit**, a
  second ballot for the same unit is rejected, and voting stops after the
  close date.
- Every role boundary is enforced on the server in `backend/app/access.py`;
  the frontend guard is usability only.

This repository is built task by task from `docs/backlog.md`. The sections
below cover what is implemented so far.

## Quick start

The whole stack (backend, frontend, PostgreSQL, and the observability
pipeline) starts with one command, then a single idempotent command fills it
with demo data you can sign in to:

```bash
make up      # build the images, start every service, wait for health, print URLs
make seed    # create the demo administrator, manager, residents, and domain data
```

Then open <http://127.0.0.1:3000> and sign in as `admin@efinges.demo`,
`manager@efinges.demo`, or `alice@efinges.demo` (password `efinges-demo-123`).
The API docs are at <http://127.0.0.1:8000/docs> and Grafana at
<http://127.0.0.1:3001>. See [Run the full stack with Docker
Compose](#run-the-full-stack-with-docker-compose) for the full command list and
[Run the services without Docker](#run-the-services-without-docker) to develop
without containers.

## Architecture

The system is a three-tier application plus a local observability pipeline,
all orchestrated by Docker Compose on a single machine:

```mermaid
flowchart LR
  browser["Browser\nReact SPA :3000"]
  api["FastAPI backend :8000"]
  db[("PostgreSQL\n:5432")]
  otel["OTel Collector"]
  prom["Prometheus"]
  loki["Loki"]
  tempo["Tempo"]
  grafana["Grafana :3001"]

  browser -->|"REST + JWT (CORS)"| api
  api -->|"SQLAlchemy / Alembic"| db
  api -->|"OTLP"| otel
  otel --> prom
  otel --> loki
  otel --> tempo
  grafana --> prom
  grafana --> loki
  grafana --> tempo
```

- **Presentation:** a React + Vite + TypeScript + Tailwind SPA served by nginx;
  every call goes through one centralized API client that attaches the JWT.
- **Application:** a FastAPI service (SQLAlchemy 2.0 + Alembic) that owns the
  business rules, the role boundaries, and the exported OpenAPI contract.
- **Data:** PostgreSQL in a named volume for the running system; the unit
  suite uses in-memory SQLite and the integration suite a dedicated database.
- **Observability:** the backend exports traces, metrics, and logs over OTLP to
  the collector, which fans them out to Prometheus, Loki, and Tempo for Grafana.

See [docs/architecture.md](docs/architecture.md) for the full stack rationale
and [docs/specs.md](docs/specs.md) for the functional requirements.

## Repository layout

- `backend/`: FastAPI application (see `backend/README.md`).
- `frontend/`: React + Vite + TypeScript + Tailwind SPA (see `frontend/README.md`).
- `docs/`: functional spec, architecture, and backlog.
- `observability/`: OpenTelemetry Collector, Prometheus, Loki, Tempo, and Grafana configuration.
- `docker-compose.yml`: local stack with the backend, frontend, PostgreSQL, and the observability pipeline.

## Run the full stack with Docker Compose

The backend, frontend, PostgreSQL, and the observability pipeline run together
with one command:

```bash
make up      # build the images, start the stack, wait for health, print URLs
make url     # print the local URLs again
make logs    # follow the backend and frontend logs
make down    # stop and remove the containers
```

`make up` waits for every service health check before returning, so the stack
is ready to use as soon as the command finishes.

| Service | URL |
| --- | --- |
| Frontend | <http://127.0.0.1:3000> |
| Backend | <http://127.0.0.1:8000> |
| API docs (Swagger UI) | <http://127.0.0.1:8000/docs> |
| Grafana | <http://127.0.0.1:3001> (`admin` / `admin`) |
| Prometheus | <http://127.0.0.1:9090> |
| Loki | <http://127.0.0.1:3100> |
| Tempo | <http://127.0.0.1:3200> |
| PostgreSQL | `postgresql://efinges:efinges@127.0.0.1:5432/efinges` |

### Configuration

Every value has a safe default, so no configuration is required for local
development. To override one, copy `.env.example` to `.env` or pass it on the
command line:

```bash
make up POSTGRES_PORT=5434   # use a different host port for PostgreSQL
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `BACKEND_PORT` | `8000` | Host port for the backend |
| `FRONTEND_PORT` | `3000` | Host port for the frontend |
| `POSTGRES_PORT` | `5432` | Host port for PostgreSQL |
| `GRAFANA_PORT` | `3001` | Host port for Grafana |
| `PROMETHEUS_PORT` | `9090` | Host port for Prometheus |
| `LOKI_PORT` | `3100` | Host port for Loki |
| `TEMPO_PORT` | `3200` | Host port for Tempo |
| `GRAFANA_ADMIN_USER` | `admin` | Grafana admin username |
| `GRAFANA_ADMIN_PASSWORD` | `admin` | Grafana admin password |
| `VITE_API_URL` | `http://localhost:8000` | Backend URL baked into the frontend bundle at build time |
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Browser origins allowed to call the API |
| `SECRET_KEY` | `dev-only-secret-key-change-me-in-production` | Secret used to sign JWTs |
| `EFINGES_SUBNET` | `10.215.25.0/24` | Docker Compose network subnet |
| `EFINGES_TAG` | `local` | Image tag for the backend and frontend images |

The frontend reads the backend URL from `VITE_API_URL` (never
`NEXT_PUBLIC_API_URL`). Because Vite inlines it at build time, changing it
requires rebuilding the frontend image:

```bash
make down
make up VITE_API_URL=http://localhost:9000
```

### How the services fit together

- `postgres` stores all application data in the `postgres_data` named volume.
- `backend` connects to `postgres` over the Compose network using
  `DATABASE_URL=postgresql+psycopg://efinges:efinges@postgres:5432/efinges`.
- `frontend` is a static nginx image serving the Vite build; it calls the
  backend at the browser-facing `VITE_API_URL`.
- The SPA and the API run on different origins (ports 3000 and 8000), so the
  backend answers cross-origin requests from the origins listed in
  `CORS_ALLOW_ORIGINS`. Add a deployed frontend origin to that list or the
  browser will discard every API response.
- All services publish their ports on `127.0.0.1` only and share the
  `10.215.25.0/24` subnet.

### Observability

The backend exports OpenTelemetry traces, metrics, and logs to the
`otel-collector` service, which fans them out to the storage backends:

- **Metrics** go to Prometheus (scraped from the collector's Prometheus
  exporter) and are visualized in the provisioned **EFINGES** Grafana
  dashboard, which shows the HTTP request rate and error rate by status code.
- **Logs** go to Loki.
- **Traces** go to Tempo.

The backend only exports when `OTEL_EXPORTER_OTLP_ENDPOINT` is set, which the
Compose stack sets to `http://otel-collector:4317`. When the variable is unset
(for example when running the backend directly with `make run`), telemetry is
disabled and nothing is exported. The service name reported to the pipeline is
`OTEL_SERVICE_NAME` (default `efinges-backend`).

Open Grafana at <http://127.0.0.1:3001> and select the **EFINGES** dashboard to
see live request and error rates.

## Run the services without Docker

```bash
make install   # install backend (uv sync) and frontend (npm install) dependencies
make run       # start the backend dev server on port 8000
make lint      # lint both sides (Ruff for the backend, ESLint for the frontend)
make test      # run the backend pytest unit suite and the frontend Vitest suite
make integration   # run the backend end-to-end workflows (needs postgres up)
make build     # type-check and build the frontend for production
make openapi   # re-export the OpenAPI contract to openapi.yaml
```

See `backend/README.md` and `frontend/README.md` for the individual commands.

## Demo data

A reviewer can explore a populated system immediately after startup. With the
stack running, one idempotent command creates a complete demo scenario:

```bash
make seed   # populate the demo data (re-running creates nothing)
```

The seed creates one administrator, one manager, and three residents; a
community with two buildings and apartments, garages, and storage units; tags;
resident assignments; bills in all three display statuses (pending, paid, and
computed overdue); one incidence per lifecycle stage with comment threads; and
one open initiative with a few ballots already cast.

Sign in with any of these accounts (password `efinges-demo-123`):

| Role | Email |
| --- | --- |
| Administrator | `admin@efinges.demo` |
| Manager | `manager@efinges.demo` |
| Resident | `alice@efinges.demo` |
| Resident | `bob@efinges.demo` |
| Resident | `carol@efinges.demo` |

The script is idempotent: every row is matched by a stable natural key (email,
name, identifier, title, description) before it is created, so running it again
adds nothing. To restore the demo to its initial state, `make seed-reset`
deletes only the demo rows and recreates them, leaving any hand-made data
untouched. Run it directly against a different database with
`cd backend && uv run python -m scripts.seed_demo --database-url <url>`.

## Continuous integration

`.github/workflows/ci.yml` runs on every push and every pull request and has
four jobs:

| Job | What it does |
| --- | --- |
| **backend** | Installs dependencies with `uv`, runs `ruff check` and `ruff format --check`, runs the unit suite (`uv run pytest`), then runs the integration workflows (`uv run pytest tests/integration`) against a PostgreSQL service container |
| **frontend** | Installs dependencies with `npm ci`, runs ESLint (`npm run lint`), runs Vitest (`npm test`), then produces the production build (`npm run build`, which type-checks first) |
| **docker** | Runs only after both jobs pass, and builds both Docker images to prove they still build from the committed `Dockerfile.backend` and `Dockerfile.frontend` |
| **deploy** | Runs only after `backend` and `frontend` pass, brings the whole stack up with `docker compose up --build --detach --wait`, seeds the demo data, and reads it back through the live HTTP API |

The `deploy` job is the project's deployment step. Cloud deployment is out of
scope (see [Scope](#scope)), so "deploy" means "bring the local Compose stack
up from the committed images and prove the running system answers": both health
checks pass, the backend serves `/healthz` after applying its migrations, the
frontend serves, and the seeded demo manager can sign in and read `/bills`.

```bash
# the deploy job's steps, reproducible locally from a clean checkout
docker compose up --build --detach --wait
curl --fail http://127.0.0.1:8000/healthz
make seed
```

The unit test step fails if `openapi.yaml` no longer matches the backend schema,
so a forgotten re-export is caught in CI. Everything the pipeline checks can be
reproduced locally, without the PostgreSQL service container for the unit suite:

```bash
make lint    # ruff check + ruff format --check, then eslint
make test    # backend unit suite + frontend Vitest suite
make build   # the frontend production build
```

`make integration` needs a reachable PostgreSQL; locally it uses the compose
postgres. Because each job installs the dependencies, a run is a few minutes;
uv, npm, and the Docker layers are all cached between runs.

Every job must be green before a change is merged. The `backend`, `frontend`,
`docker`, and `deploy` checks are the required status checks for `main`.

## Tests

The backend has two suites, kept deliberately separate:

- **Unit tests** (`make test`, or `cd backend && uv run pytest`) run against an
  in-memory SQLite database and mock or seed nothing external. They are the fast
  suite every change runs.
- **Integration tests** (`make integration`) run the three key end-to-end
  workflows — incidence lifecycle with comments, initiative creation with
  property-weighted voting and aggregation, and manual billing from pending to
  paid — against a **dedicated PostgreSQL database**, driving only the HTTP API.

```bash
make up               # start the stack (provides the PostgreSQL server)
make integration-db   # create the dedicated integration database (once)
make integration      # run the workflows against it
```

`make integration` points `TEST_DATABASE_URL` at
`postgresql+psycopg://efinges:efinges@127.0.0.1:5432/efinges_test` by default;
override it with `INTEGRATION_DATABASE_URL=...`. The workflows wipe the
application tables before each test, so always point it at a database you can
clear — never your development data.

The frontend (Vitest + React Testing Library) side runs as follows:

```bash
cd frontend
npm test           # run the component and unit tests once
npm run test:watch # re-run on change while developing
```

Both sides together, exactly as CI runs them:

```bash
make test    # backend unit suite + frontend Vitest suite
make lint    # Ruff check + format check, then ESLint
```

See `frontend/README.md` and `backend/README.md` for each side's commands and
test layout in detail.

## Database

The backend uses SQLAlchemy 2.0 with Alembic migrations. The property hierarchy
is Community → Building → Unit (apartment, garage, or storage), with shared
tags that managers can attach to buildings and units. The `users` table stores
accounts with a role of `administrator`, `manager`, or `resident`;
`unit_assignments` links each resident to the units they own or rent; and
`manager_assignments` records which communities each manager is responsible
for. Bills, incidences with comment threads, and initiatives with per-unit
votes are stored alongside them.

The models and the Pydantic schemas are split into `app/models/` and
`app/schemas/` packages (`property`, `identity`, `billing`, `maintenance`,
`governance`), with every name re-exported so imports stay short.

```bash
make migrate   # apply the migrations to the configured database
make revision m="describe the change"   # create a migration from the models
```

`DATABASE_URL` configures the application and Alembic; `TEST_DATABASE_URL`
configures the test suite and defaults to an in-memory SQLite database.

## Authentication

`POST /auth/token` implements the OAuth2 password flow and returns a signed JWT
carrying the user id and role. Send it as `Authorization: Bearer <token>` on
every protected request; `GET /auth/me` returns the signed-in user. Missing or
invalid tokens return 401, and an insufficient role returns 403. Passwords are
stored as Argon2 hashes and never returned. See `backend/README.md` for
details.

The frontend opens on a login page, calls `/auth/token`, and stores the JWT plus
the user profile in local storage, so a page refresh stays signed in. The shared
API client attaches the Bearer token to every request, and a navigation shell
shows only the links allowed for the signed-in role. Visiting a route your role
does not own redirects to a "not allowed" screen. That guard is for usability
only: the backend re-checks the role on every request. See
`frontend/README.md` for the route table.

## Resident unit assignments

A resident can own or rent several units. Managers and administrators manage
those links through `/assignments` (list, create, remove), while a resident
reads their own units through `GET /auth/me/units`. A unit has at most one
resident at a time, so assigning the same unit twice returns 409. See
`backend/README.md` for the endpoint table.

## What the API covers

Administrators have global scope, managers are limited to the communities they
are assigned to, and residents see only their own units. Every role boundary is
enforced server-side in `backend/app/access.py`.

| Area | Endpoints | Who |
| --- | --- | --- |
| Property tree and tags | `/communities`, `/buildings`, `/units`, `/tags` | Managers maintain their scope; residents read their own units |
| Manager scope | `/manager-assignments` | Administrators only |
| User management | `/users` | Administrators only |
| Bills | `/bills`, `/bills/{id}/pay` | Managers issue and settle; residents read their own |
| Incidences | `/incidences`, `/incidences/{id}/comments` | Residents report; managers advance status; both comment |
| Initiatives | `/initiatives`, `/initiatives/{id}/votes` | Managers create; residents cast one ballot per eligible unit |

Two derived values are never stored: a bill's **overdue** status is computed
from its due date every time it is serialized, and a unit's **eligibility** for
an initiative is computed from the scope filter at voting time. Money uses
`NUMERIC(12, 2)` and `decimal.Decimal`, never binary floating point.

## API contract

`openapi.yaml` at the repository root is the single source of truth for the API
surface. It is generated from the FastAPI application and never hand-edited:

```bash
make openapi   # re-export openapi.yaml from the backend schema
```

Run it after every API change and commit the result. `cd backend && uv run
pytest` fails if the committed file no longer matches the live schema, so a
forgotten re-export is caught immediately.

## AI assistant extensions

Repository-specific assistant instructions are in `AGENTS.md`; reusable
prompts and the bug-hunter profile are under `.github/prompts/` and
`.github/agents/`. See [docs/agent-permissions.md](docs/agent-permissions.md)
for permission boundaries and setup. The record of how AI tools were used —
prompts, context files, manual review, and verification — is in
[docs/ai_workflow.md](docs/ai_workflow.md).

Install and enable the local pre-commit checks:

```bash
python3 -m pip install pre-commit
pre-commit install
```

The hooks scan staged additions for likely hard-coded credentials and verify
the generated API contract:

```bash
make openapi-check   # fail if openapi.yaml needs to be regenerated
```

The optional stdio MCP server is launched from `backend/` with
`uv run python -m scripts.mock_mcp_server`. It only publishes SQLAlchemy table
and column metadata; it does not connect to the database or expose row data.

## Security and audit

The committed security artifacts live under `security/`:

| File | What it is |
| --- | --- |
| `security/bandit-report.txt` | Bandit static analysis of the backend Python code |
| `security/trivy-backend.txt` | Trivy vulnerability scan of the backend image |
| `security/trivy-frontend.txt` | Trivy vulnerability scan of the frontend image |
| `security/README.md` | Triage of every finding and how to reproduce the scans |

Regenerate all three reports with one command (needs `trivy` on the `PATH` and
the built images):

```bash
make security   # Bandit (backend) + Trivy (both images) -> security/
```

The backend application code in `app/` produces no Bandit findings; the
remaining Low findings and the container findings are triaged, with the
remediation steps, in `security/README.md`.

Every pull request is reviewed with the checklist in
`.github/pull_request_template.md`, which covers provenance, tests, the API
contract, security and privacy, and the database migrations. Completed examples
of that checklist applied to real tasks — including reviews that caught a
migration defect and a data-leak defect — are in
[docs/pr_audits/](docs/pr_audits/). AI-assisted work follows
[docs/ai_policy.md](docs/ai_policy.md) (prompt construction, data privacy, and
mandatory human review); real troubleshooting sessions with the containers and
telemetry are recorded in [docs/operations.md](docs/operations.md).

## Scope

Cloud deployment is intentionally out of scope: the system runs locally with
Docker Compose. Contractors, automatic billing, and advanced analytics are
excluded from version one.
