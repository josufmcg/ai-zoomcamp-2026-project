"""Export the FastAPI OpenAPI schema to ``openapi.yaml`` (backlog task 13).

The repository-root ``openapi.yaml`` is the frozen API contract shared by the
backend and the frontend. It is always generated from the application, never
hand-edited: change the backend, run ``make openapi``, then update the frontend
client to match.

Determinism matters because the file is committed and diffed on every API
change, so the document is dumped with sorted keys and a stable block style.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI

from app.main import create_app

# ``backend/scripts/export_openapi.py`` -> ``backend/scripts`` -> ``backend`` ->
# repository root.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "openapi.yaml"


def build_schema(app: FastAPI | None = None) -> dict[str, Any]:
    """Return the OpenAPI document for ``app`` (or a freshly built one).

    The schema is round-tripped through JSON so every value is plain data
    (dicts, lists, strings, numbers) before it is dumped to YAML; FastAPI can
    otherwise hand back objects that PyYAML does not know how to represent.
    """
    application = app or create_app()
    return json.loads(json.dumps(application.openapi()))


def render_yaml(schema: dict[str, Any]) -> str:
    """Serialize ``schema`` deterministically to YAML."""
    return yaml.safe_dump(
        schema,
        sort_keys=True,
        allow_unicode=True,
        default_flow_style=False,
        width=100,
    )


def write_schema(output: Path = DEFAULT_OUTPUT, app: FastAPI | None = None) -> Path:
    """Write the OpenAPI schema to ``output`` and return the path."""
    output.write_text(render_yaml(build_schema(app)), encoding="utf-8")
    return output


def check_schema(output: Path = DEFAULT_OUTPUT, app: FastAPI | None = None) -> bool:
    """Return whether the checked-in schema matches the current application."""
    return output.is_file() and output.read_text(encoding="utf-8") == render_yaml(build_schema(app))


def main() -> None:
    """Export the schema, or check that the committed contract is up to date."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail instead of writing when the committed contract is stale",
    )
    args = parser.parse_args()

    if args.check:
        if not check_schema():
            parser.exit(
                1,
                "openapi.yaml is missing or stale; run `make openapi` to update it\n",
            )
        print("openapi.yaml matches the current backend schema")
        return

    path = write_schema()
    print(f"Wrote {path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
