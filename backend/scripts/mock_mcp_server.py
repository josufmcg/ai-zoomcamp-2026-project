"""Read-only stdio MCP server that exposes the SQLAlchemy database schema."""

from __future__ import annotations

import json
import sys
from typing import Any

from app import models as _models  # noqa: F401 - registers all ORM models on Base.metadata
from app.database import Base

PROTOCOL_VERSION = "2025-03-26"
SERVER_INFO = {"name": "efinges-schema", "version": "1.0.0"}
SCHEMA_TOOL = {
    "name": "get_database_schema",
    "description": (
        "Return table and column metadata from SQLAlchemy models. "
        "This tool reads no database data and cannot modify the database."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "table_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional table names to include; omit to return all tables.",
            }
        },
        "additionalProperties": False,
    },
}


def database_schema(table_names: list[str] | None = None) -> dict[str, Any]:
    """Build deterministic, data-free schema metadata from registered models."""
    known_tables = sorted(Base.metadata.tables)
    requested = set(table_names) if table_names is not None else set(known_tables)
    unknown = requested - set(known_tables)
    if unknown:
        raise ValueError(f"Unknown table name(s): {', '.join(sorted(unknown))}")

    tables: list[dict[str, Any]] = []
    for table_name in sorted(requested):
        table = Base.metadata.tables[table_name]
        tables.append(
            {
                "name": table.name,
                "columns": [
                    {
                        "name": column.name,
                        "type": str(column.type),
                        "nullable": column.nullable,
                        "primary_key": column.primary_key,
                        "foreign_keys": sorted(
                            foreign_key.target_fullname for foreign_key in column.foreign_keys
                        ),
                    }
                    for column in table.columns
                ],
            }
        )
    return {"tables": tables}


def _response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def handle_message(message: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC request; return None for notifications."""
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params", {})
    if not isinstance(params, dict):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32602, "message": "params must be an object"},
        }

    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return _response(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        )
    if method == "ping":
        return _response(request_id, {})
    if method == "tools/list":
        return _response(request_id, {"tools": [SCHEMA_TOOL]})
    if method == "tools/call":
        if params.get("name") != SCHEMA_TOOL["name"]:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "Unknown tool"},
            }
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": "arguments must be an object",
                },
            }
        table_names = arguments.get("table_names")
        if table_names is not None and (
            not isinstance(table_names, list)
            or not all(isinstance(name, str) for name in table_names)
        ):
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": "table_names must be an array of strings",
                },
            }
        try:
            schema = database_schema(table_names)
        except ValueError as error:
            return _response(
                request_id,
                {
                    "content": [{"type": "text", "text": str(error)}],
                    "isError": True,
                },
            )
        return _response(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(schema, sort_keys=True)}],
                "isError": False,
            },
        )
    if request_id is None:
        return None
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def serve() -> None:
    """Serve newline-delimited JSON-RPC messages over stdio."""
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if isinstance(request, dict) else None,
                    "error": {"code": -32600, "message": "Invalid JSON-RPC request"},
                }
            else:
                response = handle_message(request)
        except (json.JSONDecodeError, TypeError) as error:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {error}"},
            }
        if response is not None:
            print(json.dumps(response, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    serve()
