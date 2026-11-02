#!/usr/bin/env python3
"""Stdio MCP server with a named action for each supported Play API operation."""

from __future__ import annotations

import json
import sys
from typing import Any

from jsonschema import Draft202012Validator
from google_api import CATALOG, OPERATIONS, call_operation
from local_setup import start_background_setup
from runtime import StorageError, connection_status, forget_profile, list_profiles


SERVER_INFO = {"name": "google-play-console", "version": "0.1.0"}
PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOLS = {"2025-03-26", "2025-06-18"}
PAGE_SIZE = 200


def control_tools() -> list[dict]:
    def tool(name: str, description: str, schema: dict, *, read_only: bool = True, destructive: bool = False) -> dict:
        return {
            "name": name,
            "description": description,
            "inputSchema": schema,
            "annotations": {"readOnlyHint": read_only, "destructiveHint": destructive, "openWorldHint": True},
        }

    profile = {"type": "string", "minLength": 1, "description": "Name of a connected Play Console account profile."}
    return [
        tool("gpc_setup", "Open the local Google Play Console credential setup form. Upload a Desktop OAuth client JSON file or service-account key JSON; OS-native secure storage is required.", {"type": "object", "properties": {}, "additionalProperties": False}, read_only=False),
        tool("gpc_connection_status", "Check whether saved Play Console profile credentials can be read from the OS secret store.", {"type": "object", "properties": {}, "additionalProperties": False}),
        tool("gpc_list_profiles", "List connected Play Console profiles without exposing credentials.", {"type": "object", "properties": {}, "additionalProperties": False}),
        tool("gpc_forget_profile", "Remove a named local Play Console profile and its OS-stored credentials. This does not revoke Google access.", {"type": "object", "properties": {"profile": profile}, "required": ["profile"], "additionalProperties": False}, read_only=False, destructive=True),
        tool("gpc_find_actions", "Find one of the individually named typed actions generated from the bundled official Google API Discovery documents.", {"type": "object", "properties": {"query": {"type": "string", "minLength": 1}, "maxResults": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20}}, "required": ["query"], "additionalProperties": False}),
    ]


CONTROL_TOOLS = {item["name"]: item for item in control_tools()}
ALL_TOOLS = [*CATALOG["operations"], *CONTROL_TOOLS.values()]


def _tool_descriptor(operation: dict) -> dict:
    descriptor = {
        "name": operation["name"],
        "description": f"{operation['title']} API: {operation['operationId']} ({operation['method']} {operation['path']}). Version status: {operation['apiStatus']}. Required OAuth scope(s): {', '.join(operation['requiredScopes'])}.",
        "inputSchema": operation["inputSchema"],
        "annotations": {
            "readOnlyHint": bool(operation["readOnly"]),
            "destructiveHint": bool(operation["riskCategory"]),
            "idempotentHint": operation["method"] in {"GET", "PUT", "DELETE"},
            "openWorldHint": True,
        },
    }
    if operation["riskCategory"]:
        # Claude Code can require an interactive approval per invocation. Codex
        # users set approval_mode="prompt" per listed tool in config.toml.
        descriptor["_meta"] = {"anthropic/requiresUserInteraction": True}
    return descriptor


def _result_text(value: Any) -> list[dict]:
    return [{"type": "text", "text": json.dumps(value, ensure_ascii=False, separators=(",", ":"))}]


def _find_actions(arguments: dict) -> dict:
    query = arguments.get("query", "").casefold()
    limit = arguments.get("maxResults", 20)
    terms = [part for part in query.split() if part]
    matches = []
    for operation in CATALOG["operations"]:
        haystack = " ".join((operation["name"], operation["operationId"], operation["title"], operation["description"], operation["apiName"], operation["apiVersion"])).casefold()
        if all(term in haystack for term in terms):
            matches.append({"name": operation["name"], "api": operation["apiName"], "version": operation["apiVersion"], "status": operation["apiStatus"], "method": operation["method"], "operationId": operation["operationId"], "title": operation["title"], "riskCategory": operation["riskCategory"]})
            if len(matches) >= limit:
                break
    return {"query": arguments["query"], "matches": matches, "catalogOperationCount": len(CATALOG["operations"])}


def call_tool(name: str, arguments: dict) -> Any:
    if name in OPERATIONS:
        operation = OPERATIONS[name]
        return call_operation(operation, arguments)
    descriptor = CONTROL_TOOLS.get(name)
    if descriptor is None:
        raise ValueError(f"Unknown Google Play Console tool: {name}")
    errors = list(Draft202012Validator(descriptor["inputSchema"]).iter_errors(arguments))
    if errors:
        path = ".".join(str(part) for part in errors[0].absolute_path) or "input"
        raise ValueError(f"Input does not match this Google Play Console workflow at {path}.")
    if name == "gpc_setup":
        return start_background_setup()
    if name == "gpc_connection_status":
        return connection_status()
    if name == "gpc_list_profiles":
        return list_profiles()
    if name == "gpc_forget_profile":
        return forget_profile(arguments["profile"])
    if name == "gpc_find_actions":
        return _find_actions(arguments)
    raise ValueError(f"Unknown Google Play Console tool: {name}")


def _error(request_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(message: dict) -> dict | None:
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _error(message.get("id") if isinstance(message, dict) else None, -32600, "Invalid JSON-RPC request")
    method = message.get("method")
    request_id = message.get("id")
    if method == "notifications/initialized" or (isinstance(method, str) and method.startswith("notifications/")):
        return None
    if method == "initialize":
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        requested = params.get("protocolVersion", PROTOCOL_VERSION)
        negotiated = requested if requested in SUPPORTED_PROTOCOLS else PROTOCOL_VERSION
        return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": negotiated, "capabilities": {"tools": {"listChanged": False}}, "serverInfo": SERVER_INFO, "instructions": "Use gpc_setup to connect. Each published operation from Android Publisher v3 and Developer Reporting v1beta1/v1alpha1 has its own typed tool. Beta is preferred in guided flows; alpha actions are preview. Every write requires an explicit profile. Claude prompts for cataloged high-impact actions; Codex users must configure per-tool approval_mode=prompt."}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        try:
            offset = int(params.get("cursor", "0"))
        except (ValueError, TypeError):
            return _error(request_id, -32602, "Invalid tools/list cursor")
        if offset < 0 or offset > len(ALL_TOOLS):
            return _error(request_id, -32602, "tools/list cursor is out of range")
        page = ALL_TOOLS[offset:offset + PAGE_SIZE]
        descriptors = [CONTROL_TOOLS[item["name"]] if item["name"] in CONTROL_TOOLS else _tool_descriptor(item) for item in page]
        result = {"tools": descriptors}
        if offset + PAGE_SIZE < len(ALL_TOOLS):
            result["nextCursor"] = str(offset + PAGE_SIZE)
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    if method == "tools/call":
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return _error(request_id, -32602, "Tool name and object arguments are required")
        try:
            result = call_tool(name, arguments)
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": _result_text(result), "isError": False}}
        except (ValueError, StorageError, OSError, KeyError) as error:
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": _result_text({"error": str(error)}), "isError": True}}
        except Exception:
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": _result_text({"error": "The Play Console operation failed unexpectedly. Check the profile, network, and current API resource state before repeating a write."}), "isError": True}}
    return _error(request_id, -32601, f"Method not found: {method}")


def main() -> int:
    for raw in sys.stdin.buffer:
        try:
            message = json.loads(raw.decode("utf-8"))
            response = handle(message)
        except (UnicodeError, ValueError):
            response = _error(None, -32700, "Parse error")
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
