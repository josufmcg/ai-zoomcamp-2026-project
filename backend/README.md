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
accounts and roles, `UnitAssignment` links a resident to the units they own or
rent, `ManagerAssignment` links a manager to the communities they manage, and
`Bill`, `Incidence`, `Comment`, `Initiative`, `InitiativeOption`, and `Vote`
back the billing, maintenance, and voting features.

The models live in the `app/models/` package (`property`, `identity`,
`billing`, `maintenance`, `governance`), grouped by bounded area; every name is
re-exported from `app.models` so `from app.models import Bill` works as before.
The same split applies to `app/schemas/`.

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

## Resident unit assignments

`UnitAssignment` links one user to one unit with an `ownership_type` of `owner`
or `tenant`. A resident can hold several units (an apartment plus a garage and
a storage room, for example), but a unit has at most one resident at a time,
enforced by a unique constraint on `unit_id`. Managers and administrators
manage assignments; residents only read their own through the shared helper.

| Method | Path | Roles | Purpose |
| --- | --- | --- | --- |
| `GET` | `/auth/me/units` | any signed-in user | Units belonging to the caller, with the ownership flag |
| `GET` | `/assignments` | manager, administrator | List assignments (filter with `?user_id=` or `?unit_id=`) |
| `POST` | `/assignments` | manager, administrator | Assign a resident to a unit |
| `DELETE` | `/assignments/{id}` | manager, administrator | Remove an assignment |

`POST /assignments` returns 404 for an unknown user or unit, 409 when the unit
is already assigned, and 422 when the target user is not a resident:

```bash
curl -s -X POST http://127.0.0.1:8000/assignments \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"user_id": 3, "unit_id": 7, "ownership_type": "owner"}'
```

The reusable helpers live in `app/routers/assignments.py`:
`units_for_user(session, user_id)` returns a resident's units with their
ownership flag (used by the resident screens and by the later billing,
incidence, and voting tasks), and `list_assignments_for_user` returns the
underlying assignment rows.

## Property management

`GET /communities`, `/buildings`, and `/units` list the property tree;
`POST`/`PATCH`/`DELETE` maintain it; and `/tags` manages the shared free-text
labels. Administrators have global scope, managers are limited to the
communities they are assigned to through `/manager-assignments`, and residents
may read only their own units.

| Method | Path | Roles | Purpose |
| --- | --- | --- | --- |
| `GET` | `/communities` | any signed-in user | List communities in the caller's scope |
| `POST` / `PATCH` / `DELETE` | `/communities[/{id}]` | administrator | Create, rename, delete a community |
| `GET` | `/buildings` | any signed-in user | List buildings in scope (`?community_id=`) |
| `POST` | `/buildings` | manager, administrator | Create a building in an assigned community |
| `PATCH` / `DELETE` | `/buildings/{id}` | manager, administrator | Rename/re-tag, or delete |
| `GET` | `/units` | any signed-in user | List units in scope (`?building_id=`, `?community_id=`, `?tag_id=`) |
| `POST` | `/units` | manager, administrator | Create a unit |
| `PATCH` / `DELETE` | `/units/{id}` | manager, administrator | Update or delete a unit |
| `GET` / `POST` | `/tags` | any signed-in user / manager | List tags / create a tag |
| `DELETE` | `/tags/{id}` | manager, administrator | Delete a tag |
| `GET` / `POST` | `/manager-assignments` | administrator | List / create manager scope |
| `DELETE` | `/manager-assignments/{id}` | administrator | Revoke a manager's scope |

Creating a building or unit with a name or identifier that already exists in
the same parent returns **409**. A property outside the caller's scope returns
**404** rather than **403**, so an out-of-scope id cannot be probed for
existence.

The row-level rules live in `app/access.py`: `writable_community_ids` returns
`None` for an administrator (unrestricted) and a set of community ids for a
manager, and `can_read_unit` / `can_write_unit` / `can_comment_on_unit` are the
helpers every later feature reuses.

## Administrator user management

Administrators create and edit accounts; no other role can. **No response ever
contains a password or its hash.**

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/users` | List accounts (`?role=`, `?is_active=`) |
| `POST` | `/users` | Create an account (409 on a duplicate email) |
| `GET` | `/users/{id}` | Read one account |
| `PATCH` | `/users/{id}` | Change role, activation, or password |

Passwords are hashed with Argon2 before storage, and login fails immediately
for a deactivated account. An administrator cannot deactivate or demote their
own account (409): doing so would lock the firm out of user management.
Deactivation is preferred over deletion because it preserves assignments,
bills, and audit history.

## Bills

Managers issue manual bills against individual units; residents read the bills
for their own units. **`overdue` is computed, never stored**: a pending bill
whose due date has passed is reported as `overdue` in every response while its
row keeps the `pending` status.

| Method | Path | Roles | Purpose |
| --- | --- | --- | --- |
| `GET` | `/bills` | any signed-in user (scoped) | List bills (`?unit_id=`, `?status=overdue`) |
| `POST` | `/bills` | manager, administrator | Issue a bill for a managed unit |
| `GET` | `/bills/{id}` | any signed-in user (scoped) | Read one bill |
| `POST` | `/bills/{id}/pay` | manager, administrator | Mark a bill paid (409 if already paid) |

Amounts use `NUMERIC(12, 2)` and `decimal.Decimal`, never binary floating
point, so a value such as `0.30` round-trips exactly. `due_date` before
`issue_date` is rejected with 422, since the bill would be overdue the moment
it is issued.

```bash
curl -s -X POST http://127.0.0.1:8000/bills \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"unit_id": 7, "amount": "120.50", "description": "Monthly rent", "due_date": "2026-11-01"}'
```

## Incidences and comments

Residents report incidences against their own units; managers advance the
status along the strict lifecycle and everyone discusses it in the comment
thread attached to the incidence.

| Method | Path | Roles | Purpose |
| --- | --- | --- | --- |
| `GET` | `/incidences` | any signed-in user (scoped) | List incidences (`?unit_id=`, `?status=`) |
| `POST` | `/incidences` | resident (own unit), manager | Report an incidence |
| `GET` | `/incidences/{id}` | any signed-in user (scoped) | Read one incidence and its thread |
| `PATCH` | `/incidences/{id}/status` | manager, administrator | Advance one lifecycle step |
| `GET` / `POST` | `/incidences/{id}/comments` | any signed-in user (scoped) | Read / add a comment |

Allowed transitions are declared once in `INCIDENCE_TRANSITIONS`
(`app/models/maintenance.py`): `submitted → in progress → resolved → closed`,
with `closed` terminal. Anything else, including skipping a stage or moving
backwards, returns **409** with the allowed next stage in the detail.

## Initiatives and voting

Managers create an initiative with two or more options, open and close dates,
and an *eligible scope* filter; residents cast **one ballot per eligible unit
they hold**.

| Method | Path | Roles | Purpose |
| --- | --- | --- | --- |
| `GET` / `POST` | `/initiatives` | any signed-in user / manager | List (`?is_open=`) / create |
| `GET` | `/initiatives/{id}` | any signed-in user | Read with running ballot counts |
| `GET` | `/initiatives/{id}/eligible-units` | any signed-in user | The caller's votable units and any existing ballot |
| `POST` | `/initiatives/{id}/votes` | resident | Cast one ballot for one eligible unit |
| `GET` | `/initiatives/{id}/results` | any signed-in user | Ballot count per option |

The scope is an object with the optional keys `community_ids`,
`building_ids`, `unit_types`, and `tag_ids`; absent keys mean "no
restriction" and `{}` means every unit. The filters combine with AND.
`eligible_unit_ids(session, scope)` is the single place that translates a scope
into a query.

Voting returns **409** when the initiative is not open, when the unit is
outside the scope or not held by the caller, or when that unit already voted.
The last rule is enforced by the unique constraint on
`(initiative_id, unit_id)`, so it holds even under concurrent requests.

```bash
# A resident owning three eligible units casts three independent ballots.
curl -s -X POST http://127.0.0.1:8000/initiatives/1/votes \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"unit_id": 7, "option_id": 2}'
```

## OpenAPI contract

The API contract lives in `openapi.yaml` at the repository root. It is always
generated from the application and never hand-edited:

```bash
make openapi   # backend/scripts/export_openapi.py -> ../openapi.yaml
```

Commit the regenerated file with every API change, then update the frontend
client in `frontend/src/services/` to match. `tests/test_openapi_contract.py`
fails when the committed file drifts from the live schema, so re-export before
pushing. The export is deterministic (sorted keys), which keeps the diff
readable.

## Makefile shortcuts

The repository root `Makefile` wraps the commands above:

```bash
make install   # uv sync
make run       # start the dev server on port 8000
make test      # run the pytest suite
make migrate   # apply the database migrations (alembic upgrade head)
make revision m="describe the change"   # create a new migration
make openapi   # export the OpenAPI schema to ../openapi.yaml
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
