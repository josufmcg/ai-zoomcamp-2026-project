# AI usage policy

This document states how AI coding assistants are used on EFINGES: who may use
them, how work is requested, what data may never be shared with a model, what a
model is allowed to do, and what a human must do before any AI-produced change
is accepted (backlog task 21). It sits next to the concrete guidance in
`AGENTS.md`, `.github/copilot-instructions.md`, and `docs/agent-permissions.md`;
where they overlap, the stricter rule wins.

The guiding rule is simple: **AI produces drafts; humans own the result.** No
model output is merged, deployed, or trusted without review and verification by
a person who is accountable for it.

## 1. Scope and principles

- Applies to every AI-assisted change to this repository: code, tests,
  migrations, configuration, documentation, and scan reports.
- A model is a tool, not a contributor. Responsibility for correctness,
  security, and compliance always rests with the human who submits the change.
- Models are used for bounded tasks, not for open-ended autonomy: each task is
  one `docs/backlog.md` unit with a goal, a description, and a definition of
  done.
- Every claim in a model's output is treated as unverified until a test, a
  command, or a human inspection confirms it. "The model said so" is never
  evidence.

## 2. Prompt construction

Prompts are built deliberately and recorded so a change can be reproduced.

- **Anchor to the backlog.** The prompt names the exact `docs/backlog.md` task
  being implemented and restates its goal and description. This keeps the scope
  to one focused unit of work.
- **Provide the governing context files.** A prompt points the model at
  `AGENTS.md` (required behavior and validation commands), `docs/specs.md`
  (domain rules) and `docs/architecture.md` (infrastructure) rather than
  restating them, so the model works from the single source of truth. Reusable
  task prompts live in `.github/prompts/`.
- **State the constraints explicitly.** For example: "OAuth2 password flow,
  401 for missing token, 403 for insufficient role"; "overdue is computed, never
  stored"; "re-export `openapi.yaml` after any API change". Ambiguity is
  resolved by asking a question, not by guessing.
- **Ask for small, reviewable diffs.** One logical change at a time, with tests,
  so the human reviewer can read the whole diff.
- **Require self-verification.** Prompts require the model to run the relevant
  commands (`make lint`, the test suites, `make openapi-check`) and to report
  the real output, not a summary.
- **Keep a record.** The prompt (or a pointer to it) is preserved with the
  change — see `docs/ai_workflow.md` — so the reasoning can be audited.

## 3. Data privacy

The repository is public, and models are third-party services. Nothing that is
private, personal, or secret may be placed in a prompt.

**Never include in a prompt, a tool call, an issue, a commit, or a log:**

- Credentials of any kind: passwords, API keys, JWT secrets, `SECRET_KEY`
  values, database connection strings with real credentials, cloud tokens.
- Real resident or personal data: names, emails, addresses, unit ownership
  records, bills, or any production database row.
- The contents of a real database, `.env` file, or secret store.

**Allowed:**

- Public source code, tests, specifications, and the checked-in `openapi.yaml`.
- The example values already in `.env.example` and the documented
  `dev-only-...` defaults, which are intentionally fake.
- Model/schema metadata from the mock MCP server (`backend/scripts/mock_mcp_server.py`),
  which returns table and column names only — never row data, never a database
  connection.

Use synthetic data for examples. If a debugging task seems to need real data,
reproduce the bug with made-up fixtures instead; never paste production data.
The pre-commit hook and the review checklist both check for leaked secrets, but
they are guardrails, not replacements for not pasting them in the first place.

## 4. Permitted agent actions

The concrete allow/deny list is in `docs/agent-permissions.md`. In summary:

- **Allowed:** read project source, tests, specs, and generated contracts; edit
  files for an explicitly requested task; run local tests, lint, builds, and
  schema checks; request clarification.
- **Restricted:** the mock MCP server is metadata-only (no database connection,
  no row data, no write tools). Do not disclose secrets or unrelated files. Do
  not call external services, deploy, commit, or push unless explicitly asked.
  Do not run destructive database, filesystem, or infrastructure operations
  without explicit approval.

## 5. Mandatory human review

Every AI-produced change passes through human review before merge. The reviewer:

1. **Reads the entire diff** and can explain every line.
2. **Confirms the data rules above** were respected (no secrets, no personal
   data).
3. **Confirms the domain rules** in `AGENTS.md` are enforced server-side (roles,
   computed overdue, incidence transition order, one ballot per unit).
4. **Runs the validation commands** and sees them pass:

   ```bash
   make lint
   make test
   make integration     # when domain behavior changed
   make openapi-check
   ```

5. **Checks the record** — the prompt, the context provided, and the outcome —
   so the change is auditable.
6. **Uses the pull request checklist** in `.github/pull_request_template.md`,
   which encodes all of the above.

A change with red checks, unexplained output, or missing provenance is sent
back, regardless of how plausible it looks.

## 6. Guardrails and audit

Automation reduces, but never replaces, human review:

| Guardrail | What it catches |
| --- | --- |
| Pre-commit hooks (`.pre-commit-config.yaml`) | Hard-coded secrets in staged additions; a drifted `openapi.yaml`. |
| CI (`.github/workflows/ci.yml`) | Lint, unit tests, integration workflows, the frontend build, and both image builds on every push and pull request. |
| `openapi.yaml` contract test | A backend API change that was not re-exported. |
| Security scans (`security/`) | Static-analysis findings (Bandit) and image vulnerabilities (Trivy). |
| The AI workflow record (`docs/ai_workflow.md`) | The prompts, context, review, and verification behind the work. |

The audit trail for AI-assisted work is: the recorded prompt and context, the
committed diff, the human review (visible in the pull request), the passing
checks, and the scan reports. Together they let a third party reconstruct what
was asked, what was produced, and how it was verified.

## 7. Escalation

If a model produces something that looks unsafe, out of scope, or based on data
it should not have had, stop and treat it as a potential incident: do not merge
it, note what happened, and review the prompt and context that produced it. If a
secret may have been exposed, rotate it immediately — do not wait for the
review.
