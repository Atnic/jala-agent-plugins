#!/usr/bin/env python3
"""Generate named App Store Connect MCP actions from Apple's OpenAPI file."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path


SOURCE_URL = (
    "https://developer.apple.com/sample-code/app-store-connect/"
    "app-store-connect-openapi-specification.zip"
)
HTTP_METHODS = {"get", "post", "patch", "put", "delete"}
SCHEMA_KEYS = {
    "$ref", "type", "format", "enum", "const", "title", "description", "default",
    "required", "properties", "items", "additionalProperties", "allOf", "anyOf",
    "oneOf", "not", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "multipleOf", "minLength", "maxLength", "pattern", "minItems", "maxItems", "uniqueItems",
    "minProperties", "maxProperties", "nullable", "readOnly", "writeOnly", "deprecated",
}


def resolve_component(document: dict, ref: str, group: str) -> dict:
    prefix = f"#/components/{group}/"
    if not ref.startswith(prefix):
        raise ValueError(f"Unsupported OpenAPI reference: {ref}")
    name = ref[len(prefix):].replace("~1", "/").replace("~0", "~")
    return document["components"][group][name]


def dereference_object(document: dict, value: dict, group: str) -> dict:
    while isinstance(value, dict) and "$ref" in value:
        value = resolve_component(document, value["$ref"], group)
    return value


def walk_refs(value) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            found.add(ref.rsplit("/", 1)[-1].replace("~1", "/").replace("~0", "~"))
        for child in value.values():
            found.update(walk_refs(child))
    elif isinstance(value, list):
        for child in value:
            found.update(walk_refs(child))
    return found


def convert_schema(value):
    if isinstance(value, list):
        return [convert_schema(child) for child in value]
    if not isinstance(value, dict):
        return value

    converted = {}
    for key, child in value.items():
        if key not in SCHEMA_KEYS or key in {"nullable", "deprecated"}:
            continue
        if key == "properties":
            converted[key] = {name: convert_schema(schema) for name, schema in child.items()}
            continue
        if key in {"enum", "const", "default"}:
            converted[key] = child
            continue
        if key == "$ref":
            if not isinstance(child, str) or not child.startswith("#/components/schemas/"):
                raise ValueError(f"Unsupported schema reference: {child}")
            child = "#/$defs/" + child[len("#/components/schemas/"):]
        converted[key] = convert_schema(child)

    if value.get("deprecated"):
        converted["deprecated"] = True
    if value.get("nullable"):
        schema_type = converted.get("type")
        if isinstance(schema_type, str):
            converted["type"] = [schema_type, "null"]
        elif isinstance(schema_type, list) and "null" not in schema_type:
            converted["type"] = [*schema_type, "null"]
        else:
            converted = {"anyOf": [converted, {"type": "null"}]}
    return converted


def parameter_schema(parameter: dict) -> dict:
    schema = parameter.get("schema")
    if schema is None and parameter.get("content"):
        schema = next(iter(parameter["content"].values())).get("schema", {"type": "string"})
    return convert_schema(schema or {"type": "string"})


def tool_name(operation_id: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", operation_id)
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value).lower().strip("_")
    name = f"asc_{value}"
    if len(name) > 64:
        suffix = hashlib.sha256(name.encode()).hexdigest()[:8]
        name = f"{name[:55].rstrip('_')}_{suffix}"
    return name


def title_from_operation_id(operation_id: str) -> str:
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", operation_id).replace("_", " ")
    words = re.sub(r"([A-Z])([A-Z][a-z])", r"\1 \2", words)
    return words.strip().title()


def risk_for(method: str, path: str, operation_id: str) -> str | None:
    if method == "DELETE":
        return "delete-or-revoke"
    if method == "GET":
        return None
    text = f"{path} {operation_id}".casefold()
    if re.search(r"revoke|revocation", text):
        return "delete-or-revoke"
    if re.search(r"submission|submit|release|phasedrelease", text):
        return "submission-or-release"
    if re.search(r"price|pricing|availabilit|pre.?orders?|territory", text):
        return "pricing-or-availability"
    if re.search(r"/users?(?:/|$)|userinvitations|userroles|useraccess|userprovisioning|accesscontrol", text):
        return "user-or-access"
    return None


def collect_schema_closure(document: dict, roots: list[dict]) -> dict:
    schemas = document["components"]["schemas"]
    found = set()
    pending = []
    for root in roots:
        pending.extend(walk_refs(root))
    while pending:
        name = pending.pop()
        if name in found:
            continue
        if name not in schemas:
            raise ValueError(f"OpenAPI references missing schema: {name}")
        found.add(name)
        pending.extend(walk_refs(schemas[name]) - found)
    return {
        name: convert_schema(schemas[name])
        for name in sorted(found)
    }


def build_operation(document: dict, path: str, path_item: dict, method: str, operation: dict) -> dict:
    parameters = {}
    for raw in (path_item.get("parameters", []) or []) + (operation.get("parameters", []) or []):
        parameter = dereference_object(document, raw, "parameters") if "$ref" in raw else raw
        parameters[(parameter.get("in"), parameter.get("name"))] = parameter

    grouped = {"path": {}, "query": {}, "headers": {}}
    required_by_group = {"path": [], "query": [], "headers": []}
    roots = []
    for (location, name), parameter in parameters.items():
        if location not in {"path", "query", "header"}:
            raise ValueError(f"Unsupported OpenAPI parameter location {location!r} for {path}")
        group = "headers" if location == "header" else location
        schema = parameter_schema(parameter)
        grouped[group][name] = schema
        roots.append(schema)
        if parameter.get("required"):
            required_by_group[group].append(name)

    raw_body = operation.get("requestBody")
    body_schema = None
    body_required = False
    if raw_body:
        request_body = dereference_object(document, raw_body, "requestBodies") if "$ref" in raw_body else raw_body
        content = request_body.get("content", {})
        json_content = content.get("application/json") or content.get("application/vnd.api+json")
        if content and not json_content:
            raise ValueError(f"Unsupported request body media type(s) for {path}: {', '.join(content)}")
        if json_content:
            body_schema = convert_schema(json_content.get("schema", {"type": "object"}))
            roots.append(json_content.get("schema", {"type": "object"}))
            body_required = bool(request_body.get("required"))

    operation_id = operation["operationId"]
    risk = risk_for(method.upper(), path, operation_id)
    description = operation.get("summary") or operation.get("description") or operation_id
    description = re.sub(r"\s+", " ", description).strip()
    description = description[:600]

    properties = {}
    required = []
    for group in ("path", "query", "headers"):
        if grouped[group]:
            group_required = required_by_group[group]
            properties[group] = {
                "type": "object",
                "properties": grouped[group],
                "additionalProperties": False,
                **({"required": sorted(group_required)} if group_required else {}),
                "description": {
                    "path": "Values for the URL path parameters shown in this action's endpoint.",
                    "query": "Values for this action's documented query parameters.",
                    "headers": "Values for this action's documented HTTP header parameters.",
                }[group],
            }
            if group_required:
                required.append(group)
    if body_schema is not None:
        properties["body"] = body_schema
        if body_required:
            required.append("body")
    if method.upper() == "GET":
        properties["outputFile"] = {
            "type": "string",
            "description": "Optional absolute destination for a binary report or download. Existing files are never overwritten.",
        }

    input_schema = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        input_schema["required"] = required
    definitions = collect_schema_closure(document, roots)
    if definitions:
        input_schema["$defs"] = definitions

    path_template = path
    endpoint = f"{method.upper()} {path_template}"
    summary = operation.get("summary")
    operation_description = operation.get("description")
    tool_description = f"{endpoint}. {summary or description}"
    if operation_description and operation_description != summary:
        tool_description += " " + re.sub(r"\s+", " ", operation_description).strip()[:350]
    if risk:
        tool_description += f" High-impact action ({risk}); a local confirmation page must be approved before the request is sent."

    return {
        "name": tool_name(operation_id),
        "operationId": operation_id,
        "method": method.upper(),
        "path": path_template,
        "title": (summary or title_from_operation_id(operation_id)).strip()[:128],
        "description": tool_description[:1000],
        "tags": operation.get("tags", []),
        "riskCategory": risk,
        "inputSchema": input_schema,
        "parameters": {
            location: [
                {
                    "name": name,
                    "in": location,
                    "required": bool(parameter.get("required")),
                    "style": parameter.get("style"),
                    "explode": parameter.get("explode"),
                    "allowReserved": parameter.get("allowReserved", False),
                }
                for (parameter_location, name), parameter in parameters.items()
                if parameter_location == location
            ]
            for location in ("path", "query", "header")
        },
        "requestBodyRequired": body_required,
        "hasRequestBody": body_schema is not None,
    }


def generate(document: dict) -> dict:
    operations = []
    for path, path_item in document["paths"].items():
        for method, operation in path_item.items():
            if method.lower() in HTTP_METHODS:
                operations.append(build_operation(document, path, path_item, method, operation))
    names = [operation["name"] for operation in operations]
    ids = [operation["operationId"] for operation in operations]
    if len(names) != len(set(names)):
        raise ValueError("Generated MCP tool names are not unique")
    if len(ids) != len(set(ids)):
        raise ValueError("Apple OpenAPI operation IDs are not unique")
    operations.sort(key=lambda item: item["name"])
    return {
        "source": SOURCE_URL,
        "apiVersion": document["info"]["version"],
        "openapiVersion": document["openapi"],
        "operationCount": len(operations),
        "operations": operations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Apple openapi.oas.json extracted from its published ZIP")
    parser.add_argument("--output", type=Path, default=Path(__file__).parents[1] / "operations.json")
    args = parser.parse_args()
    raw = args.source.read_bytes()
    document = json.loads(raw)
    if document.get("info", {}).get("title") != "App Store Connect API":
        raise SystemExit("Input is not Apple's App Store Connect OpenAPI document.")
    data = generate(document)
    data["specSha256"] = hashlib.sha256(raw).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({
        "apiVersion": data["apiVersion"],
        "operationCount": data["operationCount"],
        "output": str(args.output),
        "specSha256": data["specSha256"],
    }))


if __name__ == "__main__":
    main()
