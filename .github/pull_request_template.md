<!--
Pull request audit template (backlog task 21).

GitHub shows this checklist on every new pull request. It exists because most
changes to this repository are produced with AI assistance (see
docs/ai_policy.md): a human must review and verify every change before it is
merged. Tick each box, or strike it through with a one-line reason.
-->

## Summary

<!-- What does this change do, and which docs/backlog.md task does it implement? -->

- Backlog task: #
- Files touched:
- Related issue/spec section:

## Provenance (AI-assisted work)

- [ ] I recorded the prompt/task delegation that produced this change (link the
      session, issue, or `docs/ai_workflow.md` entry).
- [ ] I recorded the context files the model was given (specs, backlog, existing
      code) so the change can be reproduced.
- [ ] I read the entire diff myself; I can explain every changed line.
- [ ] The change matches `docs/specs.md` and the required behavior rules in
      `AGENTS.md`.

## Correctness and tests

- [ ] New or changed behavior has focused tests, and they fail without the fix.
- [ ] `make lint` passes (Ruff check + format check, then ESLint).
- [ ] `make test` passes (backend unit suite + frontend Vitest suite).
- [ ] `make integration` passes when the change touches domain behavior
      (needs PostgreSQL up).
- [ ] The frontend production build passes (`cd frontend && npm run build`).

## API contract

- [ ] Any API change was applied to the backend, then re-exported with
      `make openapi`; `openapi.yaml` is committed (never hand-edited).
- [ ] The frontend API client was updated to match the new contract.
- [ ] `make openapi-check` passes.

## Security and privacy

- [ ] No credential, token, connection string, or personal data is added to the
      source, tests, logs, or prompts.
- [ ] Role boundaries are still enforced server-side; the frontend never hides
      access by itself.
- [ ] New database rules are backed by a constraint, not only an application
      check.
- [ ] If dependencies or base images changed, I re-ran `make security` and the
      `security/` reports were refreshed.

## Database

- [ ] Every schema change has a hand-written Alembic migration that upgrades and
      downgrades cleanly (with the explicit enum `drop()` in `downgrade`).

## Documentation

- [ ] I updated the documentation for any endpoint, setup command, or
      user-visible behavior that changed.

## Reviewer sign-off

- [ ] I reviewed the diff against the checklist above and accept the change.
