# PR audit — backlog task 8: property and tag management endpoints

This is a completed copy of `.github/pull_request_template.md` for the change
that added the CRUD endpoints for communities, buildings, units, and tags, and
the shared `app/access.py` scoping module. It is the audit that caught a real
**security defect** — a resident-scoped query that returned every row — which
the model's passing tests had not detected.

## Summary

- Backlog task: 8 (Add property and tag management endpoints)
- Files touched: `backend/app/routers/` (communities, buildings, units, tags),
  `backend/app/access.py`, `backend/tests/test_properties.py`,
  `backend/scripts/scope_audit.py`, `openapi.yaml`, `AGENTS.md`
- Related issue/spec section: `docs/specs.md` §2 "User Roles & Permissions" and
  §3 "Property Structure & Tagging System"

## Provenance (AI-assisted work)

- [x] I recorded the prompt/task delegation that produced this change (link the
      session, issue, or `docs/ai_workflow.md` entry).
      → `docs/ai_workflow.md` §3, "Phase C — Backend domain (task 8)".
- [x] I recorded the context files the model was given (specs, backlog, existing
      code) so the change can be reproduced.
      → `AGENTS.md` (role boundaries), `docs/specs.md` §2–§3.
- [x] I read the entire diff myself; I can explain every changed line.
- [x] The change matches `docs/specs.md` and the required behavior rules in
      `AGENTS.md`.
      → Administrators global, managers limited to their assigned communities,
      residents limited to their own units.

## Correctness and tests

- [x] New or changed behavior has focused tests, and they fail without the fix.
      → `tests/test_properties.py` covers CRUD and all three role boundaries.
      The boundary tests passed on the model's first draft *because the leak
      below was masked by the small fixture* (only one resident had data), so a
      dedicated audit script was added — see the reviewer notes.
- [x] `make lint` passes (Ruff check + format check, then ESLint).
- [ ] `make integration` passes when the change touches domain behavior
      (needs PostgreSQL up).
      → **Struck.** Backlog task 18 did not exist yet; the endpoints were instead
      driven end to end against the live PostgreSQL container via
      `scripts/scope_audit.py`.
- [x] The frontend production build passes (`cd frontend && npm run build`).
      → Not applicable at task 8 (frontend screens come later); build left green.

## API contract

- [x] Any API change was applied to the backend, then re-exported with
      `make openapi`; `openapi.yaml` is committed (never hand-edited).
- [x] The frontend API client was updated to match the new contract.
      → Not applicable at task 8 (client updated in the frontend phase).
- [x] `make openapi-check` passes.

## Security and privacy

- [x] No credential, token, connection string, or personal data is added to the
      source, tests, logs, or prompts.
- [x] Role boundaries are still enforced server-side; the frontend never hides
      access by itself.
      → **The box that failed first.** See the review finding below: a
      resident-scoped list endpoint returned every row.
- [x] New database rules are backed by a constraint, not only an application
      check.
      → Not applicable (no new schema in this task), noted for the reviewer.
- [x] If dependencies or base images changed, I re-ran `make security` and the
      `security/` reports were refreshed.
      → No dependency or base-image change in this task.

## Database

- [x] Every schema change has a hand-written Alembic migration that upgrades and
      downgrades cleanly (with the explicit enum `drop()` in `downgrade`).
      → No schema change in this task (models shipped in task 5).

## Documentation

- [x] User-visible behavior, endpoints, and setup commands are documented.
      → `backend/README.md` endpoint table and `AGENTS.md` (scoping rule) updated.

## Reviewer notes and verdict

**Verdict: CHANGES REQUESTED (then approved).**

**Finding 1 — HTTP 500 on a scoped list with a filter.** A list endpoint built
its scope with a plain `query.join(Building)` and then applied `?community_id=`,
which joined `buildings` a second time and raised *"ambiguous column name"* →
`500 Internal Server Error`.

**Finding 2 (security) — data leak.** A resident-scoped predicate was written as
a bare `Unit.assignments.any(...)` instead of the correlated
`Bill.unit.has(Unit.assignments.any(...))`. The bare form added `units` to the
`FROM` clause as a cartesian product, so the query matched **every** row and
returned other residents' properties. The existing role-boundary tests did not
catch it because the fixture gave only one resident any data to read.

**Fix applied by the human reviewer.** Every scope rule in `app/access.py` was
rewritten as a correlated `EXISTS` built from the relationship of the entity
being filtered (`X.unit.has(...)`, `Unit.building.has(...)`,
`Unit.tags.any(...)`), and a rule was added to `AGENTS.md`: *"Access rules for
every property, unit, bill, incidence, and vote live in `backend/app/access.py`.
Do not reimplement scoping in a router."*

**Independent check added so it cannot regress.** `backend/scripts/scope_audit.py`
drives all **27** list endpoints as an administrator, a manager, and a resident,
and compares each response against an expectation computed **independently** of
the endpoint code. It reproduced both failures on the original code and passed
on the fixed code. The session is written up in `docs/operations.md` (entry 2).

**Evidence used to accept.** `scope_audit.py` passing all 27 checks against the
live Docker Compose PostgreSQL, plus `tests/test_properties.py`.

- [x] I applied the requested changes and re-ran the affected checks.
- Reviewer sign-off: human reviewer, after `scope_audit.py` passed.
