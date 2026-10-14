# EFINGES

EFINGES is a residential property management platform for property management
firms: property hierarchies, manual billing, maintenance incidences with
comment threads, and community initiatives with per-unit voting.

This repository is being built task by task from `docs/backlog.md`. The
sections below cover what is implemented so far.

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
| `SECRET_KEY` | `dev-only-secret-key-change-me` | Secret used to sign JWTs |
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
make test      # run the backend pytest suite and the frontend Vitest suite
make build     # type-check and build the frontend for production
```

See `backend/README.md` and `frontend/README.md` for the individual commands.

## Database

The backend uses SQLAlchemy 2.0 with Alembic migrations. The property hierarchy
is Community → Building → Unit (apartment, garage, or storage), with shared
tags that managers can attach to buildings and units.

```bash
make migrate   # apply the migrations to the configured database
make revision m="describe the change"   # create a migration from the models
```

`DATABASE_URL` configures the application and Alembic; `TEST_DATABASE_URL`
configures the test suite and defaults to an in-memory SQLite database.

## Scope

Cloud deployment is intentionally out of scope: the system runs locally with
Docker Compose. Contractors, automatic billing, and advanced analytics are
excluded from version one.
