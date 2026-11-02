#!/usr/bin/env python3
"""Generate named, typed MCP actions from Google API Discovery documents."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


API_SOURCES = (
    {
        "name": "androidpublisher",
        "version": "v3",
        "status": "stable",
        "url": "https://androidpublisher.googleapis.com/$discovery/rest?version=v3",
    },
    {
        "name": "playdeveloperreporting",
        "version": "v1beta1",
        "status": "beta",
        "url": "https://playdeveloperreporting.googleapis.com/$discovery/rest?version=v1beta1",
    },
    {
        "name": "playdeveloperreporting",
        "version": "v1alpha1",
        "status": "alpha",
        "url": "https://playdeveloperreporting.googleapis.com/$discovery/rest?version=v1alpha1",
    },
)

PARAMETER_SCHEMA_KEYS = {
    "type", "format", "description", "enum", "default", "pattern", "minimum", "maximum",
    "minLength", "maxLength", "minItems", "maxItems", "minProperties", "maxProperties",
    "uniqueItems", "multipleOf",
}
SCHEMA_KEYS = PARAMETER_SCHEMA_KEYS | {
    "$ref", "properties", "items", "additionalProperties", "required", "readOnly", "writeOnly",
    "deprecated", "nullable", "title", "const", "allOf", "anyOf", "oneOf", "not",
    "exclusiveMinimum", "exclusiveMaximum",
}
FILTERED_PARAMETERS = {
    "access_token", "oauth_token", "key", "callback", "uploadtype", "upload_protocol", "$.xgafv",
}
HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def pointer_escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def schema_name(document: dict, reference: str) -> str:
    if reference.startswith("#/schemas/"):
        return reference[len("#/schemas/"):].replace("~1", "/").replace("~0", "~")
    if reference in document.get("schemas", {}):
        return reference
    raise ValueError(f"Unsupported Google Discovery schema reference: {reference}")


def convert_schema(value):
    if isinstance(value, list):
        return [convert_schema(item) for item in value]
    if not isinstance(value, dict):
        return value

    converted = {}
    for key, child in value.items():
        if key not in SCHEMA_KEYS or key in {"deprecated", "nullable"}:
            continue
        if key == "$ref":
            converted[key] = "#/$defs/" + pointer_escape(child)
        elif key == "properties":
            converted[key] = {name: convert_schema(schema) for name, schema in child.items()}
        elif key == "additionalProperties" and isinstance(child, dict):
            converted[key] = convert_schema(child)
        elif key in {"items", "allOf", "anyOf", "oneOf", "not"}:
            converted[key] = convert_schema(child)
        else:
            converted[key] = child

    if value.get("deprecated"):
        converted["deprecated"] = True
    if value.get("nullable"):
        current_type = converted.get("type")
        if isinstance(current_type, str):
            converted["type"] = [current_type, "null"]
        elif isinstance(current_type, list) and "null" not in current_type:
            converted["type"] = [*current_type, "null"]
        else:
            converted = {"anyOf": [converted, {"type": "null"}]}
    return converted


def parameter_schema(parameter: dict) -> dict:
    schema = {key: parameter[key] for key in PARAMETER_SCHEMA_KEYS if key in parameter}
    schema.setdefault("type", "string")
    if parameter.get("repeated"):
        schema = {"type": "array", "items": schema}
    return schema


def walk_refs(value) -> set[str]:
    references: set[str] = set()
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str):
            references.add(reference)
        for child in value.values():
            references.update(walk_refs(child))
    elif isinstance(value, list):
        for child in value:
            references.update(walk_refs(child))
    return references


def schema_closure(document: dict, roots: list[dict]) -> dict:
    found: set[str] = set()
    pending = [ref for root in roots for ref in walk_refs(root)]
    schemas = document.get("schemas", {})
    while pending:
        reference = pending.pop()
        name = schema_name(document, reference)
        if name in found:
            continue
        if name not in schemas:
            raise ValueError(f"Google Discovery references missing schema: {name}")
        found.add(name)
        pending.extend(walk_refs(schemas[name]) - found)
    return {name: convert_schema(schemas[name]) for name in sorted(found)}


def tool_name(api_name: str, version: str, operation_id: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", operation_id)
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value).lower().strip("_")
    prefix = f"gpc_{api_name}_{version}_"
    value = value.removeprefix(f"{api_name}_")
    name = prefix + value
    if len(name) > 64:
        suffix = hashlib.sha256(name.encode()).hexdigest()[:8]
        name = f"{name[:55].rstrip('_')}_{suffix}"
    return name


def title_for(method: dict, operation_id: str) -> str:
    title = method.get("description") or operation_id
    title = re.sub(r"\s+", " ", title).strip()
    first = re.split(r"(?<=[.!?])\s", title, maxsplit=1)[0]
    return first[:128]


def is_read_only(method: dict) -> bool:
    if method.get("httpMethod", "").upper() == "GET":
        return True
    operation_id = method.get("id", "").casefold()
    description = re.sub(r"\s+", " ", method.get("description", "")).casefold()
    if operation_id.endswith((".get", ".list", ".query", ".batchget", ".validate", ".download", ".fetchreleasefilteroptions")):
        return True
    if "pricing:convertregionprices" in method.get("path", "").casefold():
        return True
    return description.startswith(("gets ", "retrieves ", "lists ", "queries ", "calculates ", "validates ", "fetches "))


def risk_category(method: dict, read_only: bool) -> str | None:
    if read_only:
        return None
    operation_id = method.get("id", "").casefold()
    path = method.get("path", "").casefold()
    text = f"{operation_id} {path} {method.get('description', '').casefold()}"
    if operation_id.endswith(".edits.commit"):
        return "edit-commit"
    if re.search(r"(?:^|\.)(?:users|grants)\.", operation_id):
        return "user-access"
    if "appsigning." in operation_id:
        return "app-signing"
    if re.search(r"refund|revoke|cancel|void", text):
        return "refund-or-cancellation"
    if re.search(r"(?:delete|deleteall|batchdelete)", operation_id) or method.get("httpMethod", "").upper() == "DELETE":
        return "delete"
    if "apprecovery.deploy" in operation_id or "apprecovery.cancel" in operation_id:
        return "release-state"
    if "publishstatus" in operation_id or "availability" in text:
        return "price-or-availability"
    if operation_id.endswith(".inappproducts.insert"):
        return "price-or-availability"
    if re.search(r"pricing|price|baseplans\.(?:activate|deactivate|batchmigrateprices|batchupdatestates)|offers\.(?:activate|deactivate|batchupdatestates)|purchaseoptions\.(?:activate|deactivate|batchupdatestates)", operation_id):
        return "price-or-availability"
    if "externaltransactions.createexternaltransaction" in operation_id:
        return "financial-transaction"
    if re.search(r"(?:^|\.)(?:subscriptions|onetimeproducts|inappproducts)\.(?:create|patch|update|batchupdate)$", operation_id):
        return "product-or-subscription-state"
    return None


def build_operation(document: dict, source: dict, method: dict) -> dict:
    api_name = source["name"]
    version = source["version"]
    operation_id = method["id"]
    parameters = dict(document.get("parameters", {}))
    parameters.update(method.get("parameters", {}))

    grouped: dict[str, dict] = {"path": {}, "query": {}, "headers": {}}
    required_by_group: dict[str, list[str]] = {"path": [], "query": [], "headers": []}
    roots = []
    parameter_details = {"path": [], "query": [], "header": []}
    for name, parameter in parameters.items():
        location = parameter.get("location")
        if name.casefold() in FILTERED_PARAMETERS or location not in {"path", "query", "header"}:
            continue
        group = "headers" if location == "header" else location
        schema = parameter_schema(parameter)
        grouped[group][name] = schema
        roots.append(schema)
        required = bool(parameter.get("required")) or location == "path"
        if required:
            required_by_group[group].append(name)
        parameter_details[location].append({
            "name": name,
            "required": required,
            "repeated": bool(parameter.get("repeated")),
            "reservedExpansion": "{+" + name + "}" in method.get("path", ""),
        })

    request_schema = None
    request_required = False
    request = method.get("request")
    if request:
        reference = request.get("$ref")
        if reference:
            schema_name(document, reference)
            request_schema = {"$ref": "#/$defs/" + pointer_escape(reference)}
            roots.append({"$ref": reference})
        else:
            request_schema = convert_schema(request)
            roots.append(request)
        request_required = True

    properties = {
        "profile": {
            "type": "string",
            "minLength": 1,
            "description": "Name of the Play Console account profile to use. Call gpc_list_profiles to see available profiles.",
        },
    }
    required_fields = ["profile"]
    for group in ("path", "query", "headers"):
        if not grouped[group]:
            continue
        description = {
            "path": "Values for this operation's documented URL path parameters.",
            "query": "Values for this operation's documented query parameters.",
            "headers": "Values for this operation's documented request headers.",
        }[group]
        properties[group] = {
            "type": "object",
            "properties": grouped[group],
            "additionalProperties": False,
            "description": description,
        }
        if required_by_group[group]:
            properties[group]["required"] = sorted(required_by_group[group])
            required_fields.append(group)

    if request_schema is not None:
        properties["body"] = request_schema
        if request_required:
            required_fields.append("body")

    upload = method.get("mediaUpload") if method.get("supportsMediaUpload") else None
    download = bool(method.get("supportsMediaDownload"))
    if upload:
        properties["uploadFile"] = {
            "type": "string",
            "minLength": 1,
            "description": "Absolute path to the local file uploaded by this API operation.",
        }
        required_fields.append("uploadFile")
    if download:
        properties["outputFile"] = {
            "type": "string",
            "minLength": 1,
            "description": "Optional absolute destination for the downloaded file. Existing files are never overwritten.",
        }

    input_schema = {
        "type": "object",
        "properties": properties,
        "required": required_fields,
        "additionalProperties": False,
    }
    definitions = schema_closure(document, roots)
    if definitions:
        input_schema["$defs"] = definitions

    read_only = is_read_only(method)
    risk = risk_category(method, read_only)
    title = title_for(method, operation_id)
    description = f"{method.get('httpMethod', 'GET').upper()} {method.get('path', '')}. {method.get('description', operation_id)}"
    description = re.sub(r"\s+", " ", description).strip()
    scopes = method.get("scopes") or document.get("auth", {}).get("oauth2", {}).get("scopes", {})
    if isinstance(scopes, dict):
        required_scopes = sorted(scopes)
    elif isinstance(scopes, list):
        required_scopes = sorted(scopes)
    else:
        required_scopes = []
    if source["status"] == "alpha":
        description = "Preview API v1alpha1. " + description
    if risk:
        description += f" Host confirmation required ({risk})."

    result = {
        "name": tool_name(api_name, version, operation_id),
        "apiName": api_name,
        "apiVersion": version,
        "apiStatus": source["status"],
        "operationId": operation_id,
        "method": method.get("httpMethod", "GET").upper(),
        "path": method.get("path", ""),
        "baseUrl": document.get("rootUrl") or document.get("baseUrl"),
        "title": title,
        "description": description[:1000],
        "readOnly": read_only,
        "riskCategory": risk,
        "inputSchema": input_schema,
        "parameters": parameter_details,
        "requestBodyRequired": request_required,
        "hasRequestBody": request_schema is not None,
        "supportsMediaUpload": bool(upload),
        "supportsMediaDownload": download,
        "uploadPath": (upload or {}).get("protocols", {}).get("resumable", {}).get("path"),
        "uploadMaxSize": int((upload or {}).get("maxSize", "0") or 0),
        "uploadContentTypes": (upload or {}).get("accept", []),
        "uploadMultipart": bool((upload or {}).get("protocols", {}).get("resumable", {}).get("multipart")),
        "responseSchema": method.get("response"),
        "requiredScopes": required_scopes,
    }
    return result


def walk_methods(resources: dict):
    for resource in (resources or {}).values():
        for method in (resource.get("methods") or {}).values():
            if method.get("httpMethod", "").upper() in HTTP_METHODS:
                yield method
        yield from walk_methods(resource.get("resources"))


def generate(documents: list[tuple[dict, dict]]) -> dict:
    operations = []
    apis = []
    for source, document in documents:
        apis.append({
            "name": source["name"],
            "version": source["version"],
            "status": source["status"],
            "title": document.get("title"),
            "description": document.get("description"),
            "discoveryUrl": source["url"],
            "rootUrl": document.get("rootUrl") or document.get("baseUrl"),
        })
        operations.extend(build_operation(document, source, method) for method in walk_methods(document.get("resources", {})))

    operations.sort(key=lambda item: item["name"])
    names = [operation["name"] for operation in operations]
    identifiers = [(operation["apiName"], operation["apiVersion"], operation["operationId"]) for operation in operations]
    if len(names) != len(set(names)):
        raise ValueError("Generated MCP tool names are not unique.")
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Google Discovery operation identifiers are not unique.")
    return {
        "source": "Google API Discovery documents",
        "operationCount": len(operations),
        "apis": apis,
        "operations": operations,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", nargs="+", required=True, help="Downloaded Discovery JSON files in API_SOURCES order.")
    parser.add_argument("--output", type=Path, default=Path(__file__).parents[1] / "operations.json")
    args = parser.parse_args()
    if len(args.documents) != len(API_SOURCES):
        raise SystemExit(f"Expected {len(API_SOURCES)} discovery documents in this order: " + ", ".join(f"{item['name']} {item['version']}" for item in API_SOURCES))
    documents = []
    hashes = []
    for source, path_value in zip(API_SOURCES, args.documents):
        path = Path(path_value)
        raw = path.read_bytes()
        document = json.loads(raw)
        if document.get("name") != source["name"] or document.get("version") != source["version"]:
            raise SystemExit(f"{path} is not the expected {source['name']} {source['version']} Discovery document.")
        hashes.append({"api": source["name"], "version": source["version"], "sha256": hashlib.sha256(raw).hexdigest()})
        documents.append((source, document))
    catalog = generate(documents)
    catalog["specSha256"] = hashes
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"operationCount": catalog["operationCount"], "apis": catalog["apis"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
