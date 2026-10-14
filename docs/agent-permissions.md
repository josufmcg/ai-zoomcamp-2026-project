# AI agent and tool permissions

Project-specific assistant context lives in `AGENTS.md` and
`.github/copilot-instructions.md`. Reusable task prompts are in
`.github/prompts/`, and `.github/agents/bug-hunter.agent.md` defines a
read-only review profile.

## Allowed work

- Read project source, tests, specifications, and generated API contracts in
  this repository.
- Edit project files needed for an explicitly requested task and run local
  tests, lint, builds, and schema checks.
- Use the mock MCP tool to inspect SQLAlchemy table and column metadata.
- Request clarification before materially changing behavior when the intended
  outcome is ambiguous.

## Restricted work

- The mock MCP server is a local stdio tool. It exposes model metadata only:
  it does not connect to a database, return row data, or offer write tools.
- Do not read or disclose credentials, local database contents, or unrelated
  files outside the task scope. Never copy credentials into source, prompts,
  logs, or external services.
- Do not invoke external services or publish data unless the user explicitly
  authorizes it. Do not deploy, commit, or push unless explicitly requested.
- Do not run destructive database, filesystem, or infrastructure operations
  without explicit user approval.
- Treat generated or model-produced changes as untrusted: inspect the diff
  and run relevant tests before reporting completion.

## Local safeguards

Install the pre-commit framework and enable the repository hooks:

```bash
python3 -m pip install pre-commit
pre-commit install
```

The hooks scan staged additions for likely hard-coded credentials and check
that `openapi.yaml` exactly matches the backend application schema. The
credential check is a guardrail, not a replacement for a dedicated secret
scanner; never stage a real credential to test it.

The schema-only MCP server can be started from the backend directory by an MCP
client configured for stdio:

```bash
uv run python -m scripts.mock_mcp_server
```

It provides the `get_database_schema` tool, optionally filtered by table
names. The server communicates over stdin/stdout; stdout is reserved for
JSON-RPC messages.
