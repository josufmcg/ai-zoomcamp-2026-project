# EFINGES Backend

FastAPI backend for EFINGES, a residential property management platform.

## Setup

```bash
cd backend
uv sync
```

## Run the development server

```bash
uv run uvicorn app.main:app --reload
```

The API is then available at <http://127.0.0.1:8000>, with interactive docs
at <http://127.0.0.1:8000/docs> and the health probe at
<http://127.0.0.1:8000/healthz>.

## Run the tests

```bash
uv run pytest
```

## Makefile shortcuts

The repository root `Makefile` wraps the commands above:

```bash
make install   # uv sync
make run       # start the dev server on port 8000
make test      # run the pytest suite
```

`make run` accepts `BACKEND_PORT` to change the port, for example
`make run BACKEND_PORT=9000`.

## Configuration

Settings are read from environment variables (or a `.env` file):

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./efinges.db` | SQLAlchemy database URL |
| `SECRET_KEY` | `dev-only-secret-key-change-me` | Secret used to sign JWTs |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | *(unset)* | OpenTelemetry OTLP endpoint; telemetry disabled when unset |

The defaults are for local development only. Production must set a strong
`SECRET_KEY` and a PostgreSQL `DATABASE_URL`.
