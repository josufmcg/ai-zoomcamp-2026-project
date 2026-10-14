# AI-assisted workflow record

This document records **how** AI coding assistants were used to build EFINGES:
the task delegations (prompts) given to the models, the context files they were
given, how each result was reviewed by a human, and how it was verified with
tests and commands. It is the concrete record that `docs/ai_policy.md` (section
2, "Keep a record") and the pull request audit template
(`.github/pull_request_template.md`) point at, and it satisfies backlog task 22.

The goal is auditability: a reviewer who was not present should be able to
reconstruct **what was asked, what the model produced, and how it was checked**,
and then reproduce it. Where this document disagrees with a stricter rule in
`AGENTS.md`, `docs/ai_policy.md`, or `docs/agent-permissions.md`, the stricter
rule wins.

## 1. Ground rules used for every task

Three rules shaped every AI interaction in this project:

1. **One backlog task per delegation.** Each prompt named the exact
   `docs/backlog.md` task and restated its goal, so the work stayed a single
   reviewable unit with its own tests.
2. **Point at the source of truth, do not restate it.** Prompts referenced
   `AGENTS.md`, `docs/specs.md`, and `docs/architecture.md` instead of copying
   the domain rules into the prompt, so the model worked from the same files the
   review used.
3. **Demand verification, not prose.** Every result was accepted only after the
   relevant command was run in the real environment and its real output was
   seen. "The model said the tests pass" was never accepted as evidence.

Personal data, credentials, `.env` contents, and real database rows were never
placed in a prompt; examples used synthetic values from `.env.example` and the
documented `dev-only-...` defaults. The only tool that touches database
structure, `backend/scripts/mock_mcp_server.py`, returns table and column
metadata and never a row or a connection — see `docs/agent-permissions.md`.

## 2. The supporting extension pack

The workflow reuses the artifacts from backlog task 20 rather than inventing new
ones each time:

| Artifact | Role in the workflow |
| --- | --- |
| `AGENTS.md` | Project context, required domain behavior, and the validation-command list given to every session. |
| `.github/copilot-instructions.md` | Entry point that tells the assistant to follow `AGENTS.md` and the backlog. |
| `.github/prompts/implement-backlog-task.prompt.md` | The default delegation for one backlog task. |
| `.github/prompts/diagnose-failing-check.prompt.md` | The delegation for "this check is red, find the cause before editing". |
| `.github/prompts/review-api-change.prompt.md` | The delegation for checking an API change across router, schema, access rules, contract, and frontend. |
| `.github/agents/bug-hunter.agent.md` | A read-only subagent that reports only evidence-backed defects, ranked by severity. |
| `backend/scripts/mock_mcp_server.py` | A read-only, metadata-only stdio MCP server exposing the SQLAlchemy schema. |
| `.pre-commit-config.yaml` | Blocks staged hard-coded secrets and a drifted `openapi.yaml`. |
| `.github/workflows/ci.yml` | Runs lint, both test suites, the frontend build, and both image builds on every push and pull request. |

The typical delegation for a task was:

```text
Implement backlog task <N> from docs/backlog.md.

Before changing code, read AGENTS.md, the relevant backlog entry, and any
related specification or architecture section. Inspect the current worktree and
preserve unrelated changes. Implement only this task, following existing
patterns, with focused tests and directly related documentation. For API
changes, regenerate openapi.yaml with `make openapi` and update any affected
frontend client use. Run the smallest relevant checks, then report changed
files, validation results, and any remaining limitations. Do not commit unless
explicitly requested.
```

Two human habits sat on top of that pattern for nearly every task:

- **The result was read line by line and the model's claims were spot-checked**
  against the file, not trusted. When a claim and the file disagreed, the file
  won.
- **Everything was verified in the real environment** — `uv run pytest`,
  `npm test`, `npm run build`, and (for backend changes) the live Docker Compose
  PostgreSQL at `127.0.0.1:5432`, not only the in-memory SQLite used by unit
  tests.

## 3. Worked examples per phase

Each example below shows the **prompt** (the delegation), the **result** (what
the model produced), and the **correction or approval** (what the human review
and the tests changed or accepted). These are real, verifiable artifacts: the
file names, migration revisions, and test counts can be checked in the
repository.

### Phase A — Foundations (task 3, Docker Compose environment)

**Prompt.** "Implement backlog task 3: add `Dockerfile.backend`,
`Dockerfile.frontend`, and a `docker-compose.yml` with `backend`, `frontend`,
and `postgres`. The frontend image must receive the backend URL as a
`VITE_API_URL` build argument (never `NEXT_PUBLIC_API_URL`). Configure the
backend `DATABASE_URL` to point at the postgres service, add health checks, a
named volume for postgres data, and a default subnet of `10.215.25.0/24`. Add a
Makefile with `up`, `down`, `logs`, `test`, and `url`."

**Result.** `Dockerfile.frontend` built the Vite bundle with
`ARG VITE_API_URL` / `ENV VITE_API_URL`, the compose file wired
`VITE_API_URL` as a build arg, and `make up` used `docker compose up --build -d
--wait`.

**Correction / approval.** Review found a real operational gap rather than a
code bug: because Vite **inlines** `VITE_API_URL` at build time, a running
container keeps the old backend URL until the image is rebuilt. This was
recorded as the rule "the running Compose images are stale after any code edit —
rebuild before verifying" and later written up in `docs/operations.md`. The
task's own tests and `make up` (all services reaching `healthy`) were the
acceptance evidence. Approved after the rebuild behaviour was documented.

### Phase B — Data and identity (task 5, property hierarchy models)

**Prompt.** "Implement backlog task 5: add SQLAlchemy models for Community,
Building, and Unit with a unit type restricted to apartment, garage, or storage,
plus a Tag model attachable to buildings or units. Create the initial Alembic
migration and configure separate database URLs for development and tests. Add
model tests covering hierarchy creation and invalid unit types."

**Result.** `app/models.py` with a native PostgreSQL enum plus a SQLite `CHECK`
for `UnitType`, the M2M `building_tags` / `unit_tags` tables, and an
autogenerated migration.

**Correction.** The autogenerated migration emitted the SQLite `CheckConstraint`
**twice**, and the downgrade did not drop the PostgreSQL enum, so an
upgrade/downgrade round-trip would fail on PostgreSQL. The human rewrote the
migration by hand (`037df15570b5`) to drop the enum explicitly in `downgrade`,
and turned that into a standing rule in `AGENTS.md`: "Write new Alembic
migrations by hand in the established style (explicit enum `drop()` in
`downgrade`); autogenerate emits SQLite `CHECK` constraints twice." The
reviewer then **proved** the fix by round-tripping `alembic upgrade head` /
`alembic downgrade base` against both in-memory SQLite and the live PostgreSQL
container, and by confirming no autogenerate drift remained. Approved.

### Phase C — Backend domain (task 8, property and tag management endpoints)

**Prompt.** "Implement backlog task 8: CRUD endpoints for communities,
buildings, units, and tags. Administrators may access everything; managers may
only access properties they are assigned to; residents have read access limited
to their own units. Test the CRUD flows and all three role boundaries."

**Result.** Routers with role dependencies and a shared `app/access.py` that
answers the scoping questions in one place.

**Correction (the most important one in the project).** Two defects surfaced on
the same scoping path, one of them a **security bug**, not just an error:

- Writing scoping as a plain `query.join(Building)` and then filtering by
  `?community_id=` joined `buildings` twice and returned
  `500 Internal Server Error` ("ambiguous column").
- Worse, a resident-scoped predicate written as a bare
  `Unit.assignments.any(...)` (instead of the correlated
  `Bill.unit.has(Unit.assignments.any(...))`) added `units` to the `FROM` clause
  as a cartesian product and matched **every** row — leaking other residents'
  data.

The human corrected `app/access.py` to express every scope rule as a correlated
`EXISTS` built from the relationship of the entity being filtered
(`X.unit.has(...)`, `Unit.tags.any(...)`), and added a rule to `AGENTS.md`:
"Access rules ... live in `backend/app/access.py`. Do not reimplement scoping in
a router." To prevent a silent regression, the human wrote
`backend/scripts/scope_audit.py`, which drives all 27 list endpoints as an
administrator, a manager, and a resident and compares each response against an
independently computed expectation. It reproduced both failures and passed on
the fixed code. The full session is recorded in `docs/operations.md` (entry 2).
Approved only after the audit script passed against the live PostgreSQL.

### Phase D — Frontend features (task 14, login and role-based navigation)

**Prompt.** "Implement backlog task 14: add a login page calling `/auth/token`,
store the JWT and role, attach the Bearer token to every API request through the
shared client, add a navigation shell with role-filtered links, a logout action,
and protected routes redirecting signed-out users to login. Test token
attachment, logout, and route guarding."

**Result.** `src/auth/` (context, provider, `RequireAuth`, navigation model),
`src/services/session.ts`, and role-filtered routes, with Vitest coverage.

**Correction.** The unit tests were green, but browser verification failed:
every API call was discarded because the SPA (`:3000`) and the API (`:8000`) are
different origins and **no CORS middleware existed**. The human added a
`cors_allow_origins` setting, `CORSMiddleware` in `create_app`, a
`tests/test_cors.py` backend test, and the rule in `AGENTS.md` that the backend
must allow the frontend origin. A second correction came from the same session:
two competing navigations (the page navigating *and* the route guard navigating)
lost the `state.from` redirect target, so navigation was consolidated into
`LoginRoute`. Approved after the browser served the rebuilt bundle and the
guard redirected correctly.

### Phase E — Quality and delivery (task 18, integration test suite)

**Prompt.** "Implement backlog task 18: create a separate integration test
location run against a dedicated test database, clearly distinct from unit
tests. Cover the three key workflows from the architecture document ... Document
the command that runs only the integration suite."

**Result.** `backend/tests/integration/` with a session-scoped app and the three
workflow files.

**Correction.** The first test passed and every test after it failed with "no
such table". Review traced it to the test client being used as a context
manager: exiting ran the application lifespan, which calls
`database.dispose()`, and for the session-scoped in-memory SQLite database
(`StaticPool`) that destroys the only connection — and the database — after the
first test. The human fixed it by building the app once per session and **not**
entering the client as a context manager, then created the schema with
`create_all()` and wiped (never dropped) tables between tests. The fix was
verified by running the full suite (13 tests) against **both** in-memory SQLite
and the live PostgreSQL `efinges_test` database. Recorded in `docs/operations.md`
(entry 4). Approved.

A second Phase E example is task 19 (CI): the model's first Ruff pass raised
`F821` on the string relationship annotations like `Mapped["Unit"]`. The human
resolved it with `TYPE_CHECKING` imports instead of `# noqa` suppressions, and
pinned the GitHub Actions versions to the newest majors that still run on
Node 20 runners. Approved after `make lint`, both suites, and the frontend build
passed locally and mirrored what CI runs.

A third Phase E example is task 23 (demo seed data). **Prompt.** "Add an
idempotent seed script, runnable with one documented command, that creates one
administrator, one manager, and three residents, a two-building community with
apartments, garages, and storage units, tags, resident assignments, bills in all
three statuses, one incidence per lifecycle stage with comments, and one open
initiative with a few votes. Ensure re-running the script does not duplicate
data."

**Result.** `backend/scripts/seed_demo.py` with per-row natural-key lookups, a
`run()` that commits once, a `--reset` flag, and tests in
`backend/tests/test_seed_demo.py`.

**Correction.** The idempotent path was green on the first run, but the human
ran the script a second time (twice) and then exercised `--reset`: deleting the
community relied on `ON DELETE CASCADE`, which SQLite does **not** enforce
unless foreign keys are switched on, so the initiative options survived and the
re-insert hit the `(initiative_id, position)` unique constraint. The reset was
rewritten to delete every level explicitly (options, votes, comments, bills,
assignments, and the tag association rows) before the parents, and the tests
were extended to assert that a second run creates zero rows and that `--reset`
leaves a hand-made community and account untouched. Verified against both
SQLite and the live Compose PostgreSQL. Approved.

## 4. Verification evidence (acceptance commands)

Every change was accepted only when the commands it affected passed. The
standing set, also listed in `AGENTS.md`:

```bash
make lint          # Ruff check + format check (backend), ESLint (frontend)
make test          # backend unit suite (uv run pytest) + frontend Vitest
make integration   # three end-to-end workflows against a dedicated PostgreSQL
make openapi-check # fails if openapi.yaml drifted from the backend schema
make build         # frontend production build (type-checks first)
make security      # refreshes the Bandit and Trivy reports under security/
```

For anything touching the database, the checks were also run against the **live
Docker Compose PostgreSQL**, not only the in-memory SQLite the unit suite uses;
for anything touching the API surface, `make openapi` was re-run and
`openapi.yaml` committed together with the change.

The audit trail for each task is therefore: the recorded prompt and context
(this document and the reusable templates), the committed diff, the human
review (visible in the pull request), the passing checks above, and — where
relevant — the scan reports under `security/`.

## 5. Corrections log

The corrections in section 3 share a pattern worth calling out: the model's
first draft was usually structurally correct and its unit tests usually passed,
but the defects that mattered were the ones only a **second, independent check**
exposed — a round-trip against real PostgreSQL, a scope audit written from an
independent expectation, a look in the actual browser, or a run against the
dedicated integration database. This is why the workflow never stopped at "the
tests pass":

| Task | Model result | Correction / independent check |
| --- | --- | --- |
| 3 | Compose stack built and started | Rebuild required because Vite inlines `VITE_API_URL` at build time |
| 5 | Autogenerated migration | Rewritten by hand; enum `drop()` added; upgrade/downgrade round-tripped on SQLite and PostgreSQL |
| 8 | Scoping in a shared module | Plain join → ambiguous-column 500; bare `.any()` → data leak. Rewritten as correlated `EXISTS`, guarded by `scope_audit.py` |
| 14 | Login and routes with green tests | CORS middleware missing; competing navigations lost the redirect target |
| 18 | Session-scoped integration app | Lifespan `dispose()` destroyed the in-memory DB; client no longer used as a context manager |
| 19 | Ruff/CI configuration | `F821` fixed with `TYPE_CHECKING` imports; action versions pinned for Node 20 runners |
| 23 | Idempotent demo seed | Second run and `--reset` re-tested by hand; reset rewritten to delete every level explicitly because SQLite skips `ON DELETE CASCADE` |

## 6. Reproducing and auditing a change

To reconstruct any task in this project:

1. Read the backlog entry for the task in `docs/backlog.md` — that is the
   delegation's goal and definition of done.
2. Points at the same context the model was given: `AGENTS.md`,
   `docs/specs.md`, and `docs/architecture.md`.
3. Inspect the committed diff for that task and compare it with the
   "correction" noted here and with the review checklist in
   `.github/pull_request_template.md`.
4. Re-run the acceptance commands from section 4 and confirm they pass.
5. Where a defect was found, re-read the matching `docs/operations.md` entry,
   which records the symptom, evidence, root cause, fix, and verification.

Because the context files and the reusable prompts are versioned with the code,
a reviewer can replay the same delegation and check whether the model now
produces the corrected result directly — which is the strongest available proof
that the correction was real and durable.
