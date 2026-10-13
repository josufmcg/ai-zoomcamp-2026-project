# EFINGES - Implementation Backlog

Tasks are ordered by dependency. Each task is one focused unit of work: implement it, test it, and commit it before starting the next. Unless stated otherwise, every task must include tests and must keep all existing tests passing.

## Phase A - Foundations

## 1. Bootstrap the FastAPI backend skeleton
Goal: Run a minimal FastAPI service locally with one passing test.
Description: Create the `backend/` project with `uv` and `pyproject.toml`. Add an application factory, a `GET /healthz` endpoint returning `{"status": "ok"}`, and a settings module reading `DATABASE_URL`, `SECRET_KEY`, and `OTEL_EXPORTER_OTLP_ENDPOINT` from environment variables with safe defaults. Add a pytest smoke test for `/healthz` and document the command to run it.

## 2. Bootstrap the React frontend skeleton
Goal: Run a minimal React SPA locally with one passing test.
Description: Create the `frontend/` project with Vite, TypeScript, and Tailwind CSS. Add a centralized API client module in `src/services/` that wraps `fetch`, attaches a JSON content type, an optional Bearer token from local storage, and normalizes error responses into thrown `Error` objects. Add a Vitest smoke test for the client's error handling and document the commands to run and test the app.

## 3. Add the core Docker Compose environment
Goal: Start the backend, frontend, and PostgreSQL together with one command.
Description: Add `Dockerfile.backend` and `Dockerfile.frontend` and a `docker-compose.yml` with `backend`, `frontend`, and `postgres` services. The frontend image must receive the backend URL as a `VITE_API_URL` build argument (never `NEXT_PUBLIC_API_URL`). Configure the backend `DATABASE_URL` to point at the postgres service, add health checks, a named volume for postgres data, and a default compose subnet of `10.215.25.0/24`. Add a Makefile with `up`, `down`, `logs`, `test`, and `url` targets.

## 4. Add the observability pipeline
Goal: Collect backend traces, metrics, and logs in Grafana via Docker Compose.
Description: Add `otel-collector`, `prometheus`, `loki`, `tempo`, and `grafana` services to the compose file, with configuration files under `observability/` modeled on the existing homework 4 setup. Add a backend telemetry module that initializes OTel exporters from `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_SERVICE_NAME`, counts HTTP requests, and shuts down cleanly on exit. Provision one Grafana dashboard showing HTTP request rate and error codes, and document the local URLs.

## Phase B - Data and identity

## 5. Create the property hierarchy models
Goal: Persist communities, buildings, units, and tags in PostgreSQL.
Description: Add SQLAlchemy models for Community, Building, and Unit with a unit type restricted to apartment, garage, or storage, plus a Tag model that managers can attach to buildings or units. Create the initial Alembic migration and configure separate database URLs for development and tests. Add model tests covering hierarchy creation and invalid unit types.

## 6. Add users, roles, and JWT authentication
Goal: Let users log in and access only what their role allows.
Description: Add a User model with an email, hashed password, and role restricted to administrator, manager, or resident. Implement `POST /auth/token` using the OAuth2 password flow that returns a signed JWT containing the user id and role. Add request dependencies that resolve the current user and enforce roles, returning 401 for missing or invalid tokens and 403 for insufficient role. Test login success, login failure, and role rejection.

## 7. Add resident and unit assignments
Goal: Link residents to the units they own or occupy.
Description: Add an assignment model relating one user to one unit with an ownership or tenancy flag, allowing a resident to hold several units. Add manager-only endpoints to list, create, and remove assignments, and a helper that returns all units belonging to the current resident. Test assignment creation, duplicate prevention, and resident-scoped listing.

## Phase C - Backend domain

## 8. Add property and tag management endpoints
Goal: Let managers maintain the property tree and tags for their assignments.
Description: Add CRUD endpoints for communities, buildings, units, and tags. Administrators may access everything; managers may only access properties they are assigned to; residents have read access limited to their own units. Add a manager-to-property assignment mechanism. Test the CRUD flows and all three role boundaries.

## 9. Add administrator user management endpoints
Goal: Let administrators manage user accounts across the firm.
Description: Add administrator-only endpoints to create, update, and list users, including assigning the manager role and activating or deactivating accounts. Passwords must be hashed and never returned in responses. Test that administrators succeed, that other roles receive 403, and that responses exclude password data.

## 10. Add bill management endpoints
Goal: Let managers issue manual bills and residents check their status.
Description: Add a Bill model with an amount, description, issue date, due date, and a status of pending or paid, linked to one unit. Managers create bills for units they manage; residents list bills for their own units only. Marking a bill paid is a manager action, and any pending bill past its due date is reported as overdue without changing the stored status. Test creation, the paid transition, computed overdue status, and role boundaries.

## 11. Add incidence and comment endpoints
Goal: Let residents report issues and discuss them with managers in one thread.
Description: Add an Incidence model with a status restricted to submitted, in progress, resolved, or closed, and a Comment model attached to one incidence. Residents create incidences for their own units and may comment on them; managers transition statuses following only the allowed order and may comment. Test the full lifecycle, an illegal transition, and a resident's inability to touch another resident's incidence.

## 12. Add initiative and voting endpoints
Goal: Let managers run community votes with one ballot per unit.
Description: Add Initiative and Vote models. Managers create an initiative with a title, description, open and close dates, two or more options, and an eligible unit scope expressed as a filter over communities, buildings, unit types, or tags. A resident casts one ballot per eligible unit they own, each recording a chosen option. Votes are rejected after the close date, and an aggregation endpoint returns the count of unit ballots per option. Test multi-unit voting, scope exclusion, double-vote prevention on the same unit, and closed initiatives.

## 13. Export the OpenAPI contract
Goal: Freeze the API surface as a versioned contract file used by the frontend.
Description: Add a Makefile target that exports the FastAPI-generated OpenAPI schema to `openapi.yaml` at the repository root. Review the exported contract against every frontend API call and fix any mismatch on either side. Document the workflow: change the backend, re-export, then update the frontend client. Commit the updated `openapi.yaml` with every API change.

## Phase D - Frontend features

## 14. Build the login and role-based navigation
Goal: Let each user sign in and reach only their role's screens.
Description: Add a login page that calls `/auth/token`, stores the JWT and user role, and attaches the Bearer token to every API request through the shared client. Add a navigation shell with role-filtered links, a logout action that clears the stored token, and protected routes that redirect signed-out users to login. Test token attachment, logout, and route guarding.

## 15. Build the resident screens
Goal: Give residents their units, bills, incidences, and votes.
Description: Add resident pages that list the user's units, show bills with a status filter including computed overdue, let the user submit and track incidences with their comment threads, and list open initiatives with a voting form that submits one ballot per owned eligible unit. Reuse the shared API client for all calls. Add Vitest coverage for the bill status filter and the per-unit ballot submission logic.

## 16. Build the manager screens
Goal: Give managers their properties, bills, incidences, and initiatives.
Description: Add manager pages that show the assigned property tree with tags, manage resident assignments to units, create bills for a chosen unit, manage incidence statuses and comment threads, and create initiatives with options and an eligible unit scope. Reuse the shared API client for all calls. Add Vitest coverage for the incidence status transition controls and the initiative scope form.

## 17. Build the administrator screens
Goal: Give administrators user management and a global property overview.
Description: Add administrator pages that list and create users, change roles, and deactivate accounts, plus a read-only overview of all communities, buildings, and units. Reuse the shared API client for all calls. Add Vitest coverage for the user creation form and role change actions.

## Phase E - Quality and delivery

## 18. Add the integration test suite
Goal: Verify the three key end-to-end workflows against a real database.
Description: Create a separate integration test location in the backend, run against a dedicated test database, clearly documented and distinct from unit tests. Cover the three workflows from the architecture document: resident submits an incidence, manager updates status, and both exchange comments; manager creates an initiative and a resident casts property-weighted votes that aggregate correctly; manager creates a bill and the resident sees it move from pending to paid. Document the command that runs only the integration suite.

## 19. Add the CI pipeline
Goal: Run all checks automatically on every push and pull request.
Description: Add a GitHub Actions workflow that installs backend dependencies and runs lint and pytest, installs frontend dependencies and runs lint, tests, and a production build, and builds both Docker images when all previous steps pass. Keep the total runtime reasonable by caching dependencies. Document the required workflow status in the README.

## 20. Add the agent extension pack
Goal: Give AI coding assistants project-specific context, tools, and guardrails.
Description: The root `AGENTS.md` already exists with project context, repository layout, required behavior rules, and validation commands; extend it only if this pack adds new rules. Add reusable prompt templates for common tasks and a subagent profile for bug hunting. Add a mock MCP server script that exposes the database schema to LLM assistants. Add a pre-commit hook that blocks hardcoded secrets and validates that `openapi.yaml` matches the backend schema. Document permission notes describing what the agents and tools are allowed to do.

## 21. Add security and audit artifacts
Goal: Show deterministic scan results and audit practices for AI-assisted work.
Description: Add a Bandit scan for the backend and a Trivy scan of both Docker images, committing their output reports under `security/`. Add a pull request audit template checklist for reviewing AI-generated changes. Add operational diagnosis notes covering at least one real troubleshooting session with the containers or telemetry. Write `docs/ai_policy.md` covering prompt construction, data privacy, and mandatory human review.

## 22. Document the AI-assisted workflow
Goal: Show exactly how AI tools produced and were checked on this project.
Description: Add a document describing the AI workflow used: the prompts or task delegations given to the models, the context files provided such as the specs and backlog, how each output was manually reviewed, and how it was verified with tests. Include at least one concrete example per phase showing the prompt, the result, and the correction or approval.

## 23. Add demo seed data
Goal: Let a reviewer explore a populated system immediately after startup.
Description: Add an idempotent seed script, runnable with one documented command, that creates one administrator, one manager, and three residents, a two-building community with apartments, garages, and storage units, tags, resident assignments, bills in all three statuses, one incidence per lifecycle stage with comments, and one open initiative with a few votes. Ensure re-running the script does not duplicate data.

## 24. Write the README
Goal: Let a new contributor set up, run, test, and explore the system end to end.
Description: Write a README that describes the problem EFINGES solves and its expected behavior, summarizes the architecture and how the components fit together, and gives exact commands to start the full stack with Docker Compose, run the seed script, run unit and integration tests for both sides, and open the API docs, frontend, and Grafana. State clearly that cloud deployment is intentionally out of scope and that contractors, automatic billing, and advanced analytics are excluded from version one.
