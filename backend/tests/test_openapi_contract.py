"""Contract tests for the exported OpenAPI file (backlog task 13).

``openapi.yaml`` is generated, committed, and diffed on every API change, so
these tests protect two properties: the committed file matches the live
application, and the generator is deterministic (re-exporting produces the same
bytes, which keeps diffs meaningful).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from app.main import create_app
from scripts.export_openapi import build_schema, render_yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPOSITORY_ROOT / "openapi.yaml"


def _contract() -> dict:
    assert CONTRACT_PATH.exists(), "openapi.yaml is missing; run `make openapi` to export it"
    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_the_contract_is_committed_at_the_repository_root() -> None:
    assert CONTRACT_PATH.is_file()


def test_the_contract_matches_the_live_application() -> None:
    """Every path the app serves is in the file, and vice versa."""
    contract_paths = set(_contract()["paths"])
    live_paths = set(build_schema()["paths"])

    assert contract_paths == live_paths
    assert contract_paths, "the contract should describe at least one endpoint"


def test_the_contract_covers_the_frontend_call() -> None:
    """The one endpoint the SPA calls today must be in the contract."""
    assert "/healthz" in _contract()["paths"]


def test_the_contract_documents_the_three_roles() -> None:
    """The role enum is the contract's statement of the access model."""
    schemas = _contract()["components"]["schemas"]

    assert schemas["UserRole"]["enum"] == [
        "administrator",
        "manager",
        "resident",
    ]


def test_the_contract_exposes_overdue_as_a_computed_status() -> None:
    """Only the display status is public; the stored status never reaches the API."""
    schemas = _contract()["components"]["schemas"]

    assert set(schemas["BillDisplayStatus"]["enum"]) == {
        "pending",
        "paid",
        "overdue",
    }
    # ``BillStatus`` (the persisted column) has no schema because no request or
    # response model references it, so a client cannot send "overdue" or read
    # the raw stored value.
    assert "BillStatus" not in schemas
    assert set(schemas["BillCreate"]["properties"]) == {
        "unit_id",
        "amount",
        "description",
        "issue_date",
        "due_date",
    }


def test_exporting_is_deterministic() -> None:
    app = create_app()
    first = render_yaml(build_schema(app))
    second = render_yaml(build_schema(app))

    assert first == second


def test_the_committed_file_is_up_to_date() -> None:
    """Re-rendering the schema reproduces the committed file byte for byte.

    A failure here means an API change was made without re-running
    ``make openapi``.
    """
    assert render_yaml(build_schema()) == CONTRACT_PATH.read_text(encoding="utf-8")
