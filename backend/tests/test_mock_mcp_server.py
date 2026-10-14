from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.mock_mcp_server import (
    PROTOCOL_VERSION,
    database_schema,
    handle_message,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_database_schema_is_sorted_and_exposes_metadata_only() -> None:
    schema = database_schema()
    table_names = [table["name"] for table in schema["tables"]]

    assert table_names == sorted(table_names)
    assert "users" in table_names
    user_table = next(table for table in schema["tables"] if table["name"] == "users")
    assert "email" in {column["name"] for column in user_table["columns"]}
    assert all("rows" not in table for table in schema["tables"])


def test_schema_can_be_filtered_and_rejects_unknown_tables() -> None:
    assert [table["name"] for table in database_schema(["users"])["tables"]] == ["users"]

    try:
        database_schema(["not_a_table"])
    except ValueError as error:
        assert "not_a_table" in str(error)
    else:
        raise AssertionError("unknown tables must not be silently ignored")


def test_mcp_initialize_and_tool_discovery() -> None:
    initialized = handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    tools = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    assert initialized is not None
    assert initialized["result"]["protocolVersion"] == PROTOCOL_VERSION
    assert tools is not None
    assert [tool["name"] for tool in tools["result"]["tools"]] == ["get_database_schema"]


def test_mcp_schema_tool_returns_json_content() -> None:
    response = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_database_schema",
                "arguments": {"table_names": ["users"]},
            },
        }
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is False
    assert json.loads(result["content"][0]["text"])["tables"][0]["name"] == "users"


def test_mcp_notifications_have_no_response_and_invalid_calls_are_reported() -> None:
    notification = handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"})
    invalid_call = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "get_database_schema",
                "arguments": {"table_names": ["not_a_table"]},
            },
        }
    )

    assert notification is None
    assert invalid_call is not None
    assert invalid_call["result"]["isError"] is True


def test_stdio_server_emits_json_rpc_without_non_protocol_stdout() -> None:
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_database_schema",
                "arguments": {"table_names": ["users"]},
            },
        },
    ]
    process = subprocess.run(
        [sys.executable, "-m", "scripts.mock_mcp_server"],
        input="".join(json.dumps(message) + "\n" for message in messages),
        capture_output=True,
        check=True,
        cwd=BACKEND_DIR,
        text=True,
    )

    responses = [json.loads(line) for line in process.stdout.splitlines()]
    assert [response["id"] for response in responses] == [1, 2]
    assert json.loads(responses[1]["result"]["content"][0]["text"])["tables"][0]["name"] == "users"
