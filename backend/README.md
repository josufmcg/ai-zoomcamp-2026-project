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

## Database and migrations

The backend uses SQLAlchemy 2.0 with Alembic for migrations. The property
hierarchy is Community → Building → Unit, where a unit is an apartment, a
garage, or a storage room, plus a shared `Tag` table that managers can attach
to buildings and units. The `User` table (see **Authentication** below) stores
accounts and roles.

Apply the migrations to the configured database:

```bash
uv run alembic upgrade head
```

Create a new migration after changing the models:

```bash
uv run alembic revision --autogenerate -m "describe the change"
```

Development and tests use separate databases. `DATABASE_URL` is used by the
running application and by Alembic; `TEST_DATABASE_URL` is used by the test
suite and defaults to an in-memory SQLite database that is created fresh for
every test. Point `TEST_DATABASE_URL` at a dedicated PostgreSQL database to run
the integration suite against a real server.

## Authentication

`POST /auth/token` implements the OAuth2 password flow. Send a form body with
`username` (the user's email) and `password`; the response is a signed JWT with
a `bearer` token type:

```bash
curl -s http://127.0.0.1:8000/auth/token \
  -d 'username=manager@efinges.test' -d 'password=correct horse battery staple'
```

The JWT carries the user id (`sub`) and `role` (`administrator`, `manager`, or
`resident`) and is signed with `SECRET_KEY` using HMAC-SHA256. Send it on every
protected request as `Authorization: Bearer <token>`. `GET /auth/me` returns
the signed-in user's profile (never the password hash).

Request dependencies in `app/dependencies.py` resolve the current user and
enforce roles. A missing, invalid, or expired token returns **401**; a valid
token whose role is not allowed returns **403**. Role checks always run
server-side; the frontend is never trusted to hide access. Use
`require_role(UserRole.MANAGER, ...)` as a route dependency to restrict an
endpoint:

```python
from typing import Annotated

from fastapi import Depends

from app.dependencies import require_role
from app.models import User, UserRole

@app.get("/manager-area")
def manager_area(
    user: Annotated[User, Depends(require_role(UserRole.MANAGER))],
) -> dict[str, str]:
    return {"email": user.email}
```

There is no public sign-up endpoint: users are created by administrators
(backlog task 9), so tests seed accounts directly against the database.

## Makefile shortcuts

The repository root `Makefile` wraps the commands above:

```bash
make install   # uv sync
make run       # start the dev server on port 8000
make test      # run the pytest suite
make migrate   # apply the database migrations (alembic upgrade head)
make revision m="describe the change"   # create a new migration
```

`make run` accepts `BACKEND_PORT` to change the port, for example
`make run BACKEND_PORT=9000`.

## Configuration

Settings are read from environment variables (or a `.env` file):

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./efinges.db` | SQLAlchemy database URL used by the app and Alembic |
| `TEST_DATABASE_URL` | `sqlite:///:memory:` | SQLAlchemy database URL used by the test suite |
| `SECRET_KEY` | `dev-only-secret-key-change-me-in-production` | Secret used to sign JWTs |
| `JWT_ALGORITHM` | `HS256` | Signing algorithm for access tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access-token lifetime in minutes |
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
