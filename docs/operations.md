# Operational diagnosis notes

Real troubleshooting sessions on the EFINGES stack (backlog task 21). Each
entry records the symptom, the evidence gathered, the root cause, the fix, and
how the fix was verified, so the next person hits the answer instead of the
problem.

## 1. Loki and Tempo report "not ready" while serving queries

**Symptom.** Grafana showed Loki and Tempo as healthy enough to query — logs
appeared in Loki's Explore view and traces appeared in Tempo — but a direct
readiness probe failed, which is exactly the check a load balancer or an
orchestrator would use to decide whether to route traffic.

**Evidence.**

```bash
$ docker compose ps --format '{{.Service}}\t{{.Status}}'
loki     Up 12 hours
tempo    Up 12 hours
...
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:3100/ready
HTTP 503
$ curl -s http://127.0.0.1:3100/loki/api/v1/labels | head -c 40
{"status":"success"}
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:3200/ready
HTTP 503
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:9090/-/healthy
HTTP 200
```

So `/ready` returned `503` while the query API returned success, and Prometheus
was healthy throughout.

**Root cause.** Loki's `/ready` endpoint does not only check that the process is
up; it waits for the ring to reach a stable state. In single-binary mode with
the default settings, the ring never fully stabilizes the way the readiness
check expects, so `/ready` keeps returning `503`. The query path does not depend
on that ring state, which is why queries worked the whole time. Tempo's
`/ready` has the same behavior in its single-binary mode.

**Fix.** Treat `/ready` for the single-binary Loki and Tempo services as
informational rather than a health gate:

- Do not wire a container health check or an orchestrator readiness probe to
  Loki/Tempo `/ready`; use the process staying up and the query API instead.
- Confirm the pipeline with a query, not with `/ready`:

  ```bash
  curl -s "http://127.0.0.1:3100/loki/api/v1/labels"           # Loki
  curl -s "http://127.0.0.1:3200/api/search/tags"              # Tempo
  ```

**Verification.** The labels query returned `{"status":"success"}` and the
Compose stack stayed `Up` and served both logs and traces while `/ready`
returned `503`, confirming the pipeline was healthy and the probe was the only
thing misreporting.

## 2. Scope-filtered list endpoints returned every row (or HTTP 500)

**Symptom.** Two different failures appeared on the same code path as the
role-based scoping was added to the list endpoints:

1. Adding `?community_id=` to a list request produced
   `500 Internal Server Error`, with the database complaining about an
   **ambiguous column**.
2. Worse, a resident-scoped query silently returned **every** row in the table
   instead of only the rows the resident could see.

**Evidence.** Both failures traced back to how the scope predicate was written
in `backend/app/access.py`:

```python
# WRONG: a plain join adds `buildings` to the FROM clause once, and the later
# ?community_id= filter joins it again -> "ambiguous column: buildings.community_id"
query = query.join(Building)

# WRONG: a bare relationship `.any()` (instead of the correlated `Bill.unit.has(...)`)
# pulls `units` into the FROM clause as a cartesian product -> the filter matches
# every row and the response leaks unrelated data.
query = query.filter(Unit.assignments.any(UnitAssignment.user_id == user_id))
```

**Root cause.** Scoping must be a **correlated** predicate so it stays inside the
outer query's `WHERE` clause and never widens the `FROM` clause. A plain
`.join(...)` adds a table that a later filter also joins (ambiguous column), and
a bare relationship `.any(...)` on a column that is not the current entity adds
a cartesian product (massive over-match). The second failure is a security bug,
not just a 500: it returned other residents' data.

**Fix.** Express every scope rule as a correlated `EXISTS` built from the
relationship attribute of the entity being filtered:

```python
# Correct: correlated through the relationship, no extra FROM entry.
query = query.filter(Bill.unit.has(Unit.assignments.any(UnitAssignment.user_id == user_id)))
query = query.filter(Unit.building.has(Building.community_id == community_id))
query = query.filter(Unit.tags.any(Tag.id.in_(tag_ids)))
```

**Verification.** `backend/scripts/scope_audit.py` drives all 27 list endpoints
as an administrator, a manager, and a resident, and compares each response
against an independently computed expectation. It caught both regressions when
they were present and passes on the fixed code:

```bash
cd backend
DATABASE_URL=postgresql+psycopg://efinges:efinges@127.0.0.1:5432/efinges \
    uv run python -m scripts.scope_audit
```

## 3. The browser kept serving the old frontend after a code change

**Symptom.** A frontend fix was committed and the code was correct, but the
browser kept behaving like the old version — for example, still showing a page
without the login screen after login was added.

**Root cause.** `make up` builds the images, but at the time of this session the
running containers were started earlier and were serving the **old** bundle
baked into the pre-change image. The Vite build is compiled into the image at
build time, so editing `frontend/src` changes nothing until the image is
rebuilt.

**Fix.** Rebuild the affected image and recreate its container before verifying
in the browser:

```bash
docker compose build frontend && docker compose up -d frontend
```

**Verification.** After the rebuild the browser served the new bundle and the
previously missing screen appeared. The general rule adopted from this session:
**the running Compose images are stale after any code edit — rebuild before
verifying.**

## 4. Integration tests destroyed the in-memory database after the first test

**Symptom.** The first integration test passed, but every test after it failed
with "no such table", as if the schema had vanished between tests.

**Root cause.** The test client was used as a context manager, which runs the
application lifespan on exit. The lifespan calls `database.dispose()`, and for
the session-scoped in-memory SQLite database (`StaticPool`) that destroys the
only connection — and with it the database — after the first test.

**Fix.** The integration suite builds the app once per session and **does not**
enter the client as a context manager, so the lifespan never disposes the shared
database. The workflows under test do not need the telemetry that the lifespan
would set up. Schema is created once with `create_all()` and the tables are
wiped (never dropped) between tests.

**Verification.** The full integration suite (`uv run pytest tests/integration`,
13 tests) passes against both in-memory SQLite and the live PostgreSQL
`efinges_test` database.

## General debugging checklist

1. `docker compose ps` — is every service `Up`, and which ones are `healthy`?
2. `make url` — confirm the ports you are probing are the ones the stack
   published.
3. Query the pipeline directly (Loki labels, Tempo tags, Prometheus
   `/-/healthy`) instead of trusting a single readiness endpoint.
4. Rebuild the image before verifying a code change in the browser.
5. For a data-scoping bug, run `backend/scripts/scope_audit.py` to compare every
   list endpoint against an independent expectation.
6. When a test behaves differently from the app, check the lifespan: `dispose()`
   on a `StaticPool` SQLite database throws the database away.
