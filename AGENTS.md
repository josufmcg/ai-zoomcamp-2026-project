# AGENTS.md

## Project context

EFINGES is a residential property management platform for property management firms: property hierarchies, manual billing, maintenance incidences with comment threads, and community initiatives with per-unit voting. Read `docs/specs.md` before changing domain behavior, `docs/architecture.md` before changing infrastructure, and work through `docs/backlog.md` tasks in order.

## Repository layout

- `backend/`: FastAPI, SQLAlchemy, Alembic. Use `uv` for dependencies and commands. Models live in `backend/app/models/` and schemas in `backend/app/schemas/`, both split by area and re-exported for short imports.
- `frontend/`: React + Vite + TypeScript + Tailwind. Follow the scripts in its `package.json`.
- `observability/`: OpenTelemetry Collector, Prometheus, Loki, Tempo, and Grafana configuration.
- `docs/`: functional spec, architecture, backlog, AI policy.
- `security/`: scan reports and audit artifacts.
- `openapi.yaml`: exported API contract at the repository root; the single source of truth for the API surface. Regenerate with `make openapi`; `backend/tests/test_openapi_contract.py` fails if it drifts.

## Required behavior

- Three roles only: administrator, manager, resident. Enforce every role boundary server-side; never trust the frontend to hide access.
- Property hierarchy: Community → Building → Unit. Unit types are apartment, garage, and storage. Units are assigned, managed, and billed individually.
- Authentication is OAuth2 password flow returning a JWT with user id and role. Return 401 for missing or invalid tokens and 403 for insufficient role.
- The SPA and the API are different origins (ports 3000 and 8000), so the backend must allow the frontend origin via `CORS_ALLOW_ORIGINS`. Keep that list in sync with wherever the SPA is served; without it the browser discards every API response even though the request succeeded.
- Bills are created manually by managers only. Stored status is pending or paid; overdue is always computed from the due date, never stored.
- Incidence statuses follow submitted → in progress → resolved → closed, in that order; only the immediate next stage is allowed and "closed" is terminal.
- All resident-manager communication happens in comment threads attached to incidences. There is no direct messaging.
- Voting is one ballot per eligible owned unit: a resident owning N units in an initiative's scope casts N ballots. Reject a second ballot for the same unit and any vote after the close date.
- Initiative scope is a filter over communities, buildings, unit types, and tags; its keys combine with AND and an empty scope means every unit.
- Access rules for every property, unit, bill, incidence, and vote live in `backend/app/access.py`. Do not reimplement scoping in a router.
- Managers get write access only to the communities they are assigned to through `/manager-assignments`; administrators have global scope.
- Use decimal-safe arithmetic for money; never binary floating point for persisted or calculated amounts.
- Tags are free-text labels on buildings and units, used for grouping and scoping only.

## Development workflow

- Implement one `docs/backlog.md` task per change; keep every task's tests passing before moving on.
- After any API change, re-export `openapi.yaml` from the FastAPI schema and commit it; never hand-edit it. Then update the frontend API client to match. `make openapi` does the export.
- Write new Alembic migrations by hand in the established style (explicit enum `drop()` in `downgrade`); autogenerate emits SQLite `CHECK` constraints twice.
- Add a database constraint for every rule that must hold even under concurrent requests, and an application check for the friendly error message (for example the one-vote-per-unit unique constraint plus the 409).
- The frontend must reach the backend only through the centralized API client in `frontend/src/services/`.
- Add or update focused tests with every behavior change.
- Keep secrets and local databases out of version control; configure through environment variables.
- Update documentation when an endpoint, setup command, or user-visible behavior changes.

## Validation commands

```bash
make install   # install backend dependencies (uv sync)
make run       # run the backend dev server on port 8000
make test      # run the backend pytest suite
cd backend && uv run pytest
make openapi   # re-export openapi.yaml from the backend schema (required after API changes)
cd frontend && npm test
cd frontend && npm run build
make up        # start the full stack with Docker Compose (backlog task 3)
```

Some commands only exist once the corresponding backlog tasks are done; never run commands that the current project configuration does not define.
