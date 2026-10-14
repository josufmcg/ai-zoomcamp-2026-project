---
name: implement-backlog-task
description: Implement one ordered EFINGES backlog item with focused tests and validation.
agent: agent
---

Implement backlog task **${input:task_number}** from `docs/backlog.md`.

Before changing code, read `AGENTS.md`, the relevant backlog entry, and any
related specification or architecture section. Inspect the current worktree and
preserve unrelated changes. Implement only this task, following existing
patterns, with focused tests and directly related documentation. For API
changes, regenerate `openapi.yaml` with `make openapi` and update any affected
frontend client use. Run the smallest relevant checks, then report changed
files, validation results, and any remaining limitations. Do not commit unless
explicitly requested.
