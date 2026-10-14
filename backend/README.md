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
| `OTEL_SERVICE_NAME` | `efinges-backend` | Service name reported to the observability pipeline |

The defaults are for local development only. Production must set a strong
`SECRET_KEY` and a PostgreSQL `DATABASE_URL`.

## Telemetry

`app/telemetry.py` configures OpenTelemetry for the application. When
`OTEL_EXPORTER_OTLP_ENDPOINT` is set, the backend exports traces, metrics, and
logs over OTLP/gRPC to that endpoint; when it is unset, telemetry is disabled
and nothing is exported. A middleware counts every HTTP request by matched
route and response status code (`http.server.request.count`), and the providers
are flushed and shut down cleanly when the application stops.

The Docker Compose stack sets `OTEL_EXPORTER_OTLP_ENDPOINT` to
`http://otel-collector:4317` and `OTEL_SERVICE_NAME` to `efinges-backend`. See
the root `README.md` for the Grafana, Prometheus, Loki, and Tempo URLs.
