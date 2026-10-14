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
- `docker-compose.yml`: local stack with the backend, frontend, and PostgreSQL.

## Run the full stack with Docker Compose

The backend, frontend, and PostgreSQL run together with one command:

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
| PostgreSQL | `postgresql://efinges:efinges@127.0.0.1:5433/efinges` |

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
| `POSTGRES_PORT` | `5433` | Host port for PostgreSQL |
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

## Run the services without Docker

```bash
make install   # install backend (uv sync) and frontend (npm install) dependencies
make run       # start the backend dev server on port 8000
make test      # run the backend pytest suite and the frontend Vitest suite
make build     # type-check and build the frontend for production
```

See `backend/README.md` and `frontend/README.md` for the individual commands.

## Scope

Cloud deployment is intentionally out of scope: the system runs locally with
Docker Compose. Contractors, automatic billing, and advanced analytics are
excluded from version one.
