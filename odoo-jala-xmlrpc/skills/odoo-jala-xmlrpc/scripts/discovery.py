"""Bounded, read-only Odoo metadata discovery and per-account local profiles."""

import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import xmlrpc.client

import connection_store


SCHEMA_VERSION = 1
CACHE_HOURS = 24
FIELD_ATTRIBUTES = [
    "string", "type", "required", "readonly", "relation", "selection",
    "store", "company_dependent",
]


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def fault_result(exc):
    denied = any(name in exc.faultString for name in ("AccessError", "AccessDenied"))
    return {"status": "denied" if denied else "unavailable", "fetched_at": now().isoformat()}


def optional(call):
    try:
        return {"status": "ok", "fetched_at": now().isoformat(), "value": call()}
    except xmlrpc.client.Fault as exc:
        return fault_result(exc)


def table(call, model, fields, domain, limit, context):
    """Inspect available columns first, then use bounded keyset pagination."""
    rows = []
    try:
        metadata = call(model, "fields_get", [], {"attributes": ["type", "string"], "context": context})
        selected = [field for field in fields if field in metadata]
        if "id" not in selected or len(selected) < 2:
            return {"status": "unavailable", "fetched_at": now().isoformat()}
        last_id = 0
        while len(rows) <= limit:
            page_limit = min(200, limit + 1 - len(rows))
            batch = call(model, "search_read", [domain + [["id", ">", last_id]]], {
                "fields": selected, "limit": page_limit, "order": "id asc", "context": context,
            })
            if not isinstance(batch, list):
                raise ValueError("Unexpected discovery response.")
            for record in batch:
                record_id = record.get("id") if isinstance(record, dict) else None
                if type(record_id) is not int or record_id <= last_id:
                    raise ValueError("Unexpected discovery pagination.")
                last_id = record_id
            rows.extend(batch)
            if len(batch) < page_limit or len(rows) > limit:
                break
        return {
            "status": "truncated" if len(rows) > limit else "ok",
            "fetched_at": now().isoformat(), "records": rows[:limit],
            "fields": {field: metadata[field] for field in selected},
        }
    except xmlrpc.client.Fault as exc:
        result = fault_result(exc)
        if rows:
            result.update(status="partial", records=rows[:limit])
        return result


def scope_for_user(call, uid, requested_companies):
    user = optional(lambda: call("res.users", "read", [[uid]], {
        "fields": ["company_id", "company_ids", "lang", "tz"],
    }))
    context = {}
    if user["status"] != "ok" or not user.get("value"):
        if requested_companies:
            raise ValueError("Cannot establish the requested company scope from this account.")
        return user, context
    record = user["value"][0]
    allowed = record.get("company_ids", [])
    current = record.get("company_id")
    current_id = current[0] if isinstance(current, list) and current else None
    if requested_companies and not set(requested_companies).issubset(allowed):
        raise ValueError("Requested company is outside this account's allowed companies.")
    selected = requested_companies or ([current_id] if current_id else [])
    if selected:
        context["allowed_company_ids"] = selected
    for name in ("lang", "tz"):
        if record.get(name):
            context[name] = record[name]
    return user, context


def profile_path(identity, context):
    key = json.dumps([identity, context], sort_keys=True).encode()
    digest = hashlib.sha256(key).hexdigest()
    return connection_store.state_directory() / "profiles" / (digest + ".json")


def cached_profile(path, identity, context, version, limit):
    if (path.is_symlink() or path.parent.is_symlink() or not path.is_file()
            or (os.name == "posix" and path.stat().st_mode & 0o077)):
        return None
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
        age = now() - datetime.datetime.fromisoformat(profile["inventory_at"])
        if (profile["schema_version"] == SCHEMA_VERSION and profile["identity"] == identity
                and profile["context"] == context and profile["server_version"] == version
                and profile["limit"] == limit and isinstance(profile["inventory"], dict)
                and isinstance(profile["model_details"], dict)
                and datetime.timedelta() <= age < datetime.timedelta(hours=CACHE_HOURS)):
            return profile
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return None


def customization_signals(inventory):
    candidates = []
    for addon in inventory["installed_addons"].get("records", []):
        name, author = addon.get("name", ""), addon.get("author") or ""
        evidence = []
        if name.startswith("jala"):
            evidence.append("jala_name_prefix")
        if author and "odoo" not in author.lower():
            evidence.append("non_odoo_author_metadata")
        if name == "studio_customization":
            evidence.append("studio_module_name")
        if evidence:
            candidates.append({"name": name, "author": author, "evidence": evidence, "classification": "unverified_candidate"})
    return {
        "addon_candidates": candidates,
        "manual_models": [record["model"] for record in inventory["models"].get("records", [])
                          if record.get("state") == "manual" and record.get("model")],
        "note": "Names/authors are hints, not proof of ownership. Base-state models can come from custom Python addons. Missing candidates do not prove a standard installation.",
    }


def source_reference(inventory, models):
    path = Path(__file__).parents[1] / "references/jala-addons-index.json"
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
        addons = catalog["addons"]
        revision = catalog["revision"]
    except (OSError, ValueError, KeyError, TypeError):
        return {"status": "unavailable"}
    observed = {row["name"] for row in inventory["installed_addons"].get("records", []) if row.get("name")}
    return {
        "status": "ok", "repository": catalog["repository"], "revision": revision,
        "catalog_path": str(path.resolve()),
        "matching_installed_names": sorted(addon["name"] for addon in addons if addon["name"] in observed),
        "model_source_candidates": {model: [
            {"addon": addon["name"], "source_version": addon["version"],
             "file": declaration["file"], "line": declaration["line"],
             "installation": "observed_installed" if addon["name"] in observed else "not_observed"}
            for addon in addons for declaration in addon["model_declarations"]
            if declaration["model"] == model or model in declaration["inherits"]
        ] for model in models},
        "note": "Matching names link to source candidates, not verified deployed revisions. Missing names may be hidden or truncated. Read source to interpret workflow state; this client does not execute workflow methods.",
    }


def inventory_for(call, context, limit):
    def read(model, fields, domain=None):
        return table(call, model, fields, domain or [], limit, context)

    inventory = {
        "installed_addons": read("ir.module.module", [
            "id", "name", "shortdesc", "author", "state", "latest_version", "installed_version", "application",
        ], [["state", "=", "installed"]]),
        "models": read("ir.model", ["id", "model", "name", "state", "transient"]),
        "menus": read("ir.ui.menu", ["id", "name", "parent_id", "action"]),
        "window_actions": read("ir.actions.act_window", ["id", "name", "res_model", "view_mode"]),
    }
    # The computed `modules` column can require ir.module.module access. Keep
    # provenance separate so an access failure never erases the model inventory.
    if inventory["installed_addons"]["status"] in {"ok", "truncated"}:
        inventory["model_origins"] = read("ir.model", ["id", "model", "modules"])
        installed_ids = [row["id"] for row in inventory["installed_addons"].get("records", [])]
        inventory["addon_dependencies"] = read("ir.module.module.dependency", ["id", "module_id", "name"], [
            ["module_id", "in", installed_ids],
        ]) if installed_ids else {"status": "ok", "records": [], "fetched_at": now().isoformat()}
    else:
        for section in ("model_origins", "addon_dependencies"):
            inventory[section] = {"status": "not_attempted", "reason": "addon_inventory_unavailable"}
    return inventory


def details_for(call, model, context, limit, origins_available):
    fields = optional(lambda: call(model, "fields_get", [], {
        "attributes": FIELD_ATTRIBUTES, "context": context,
    }))
    access = {operation: optional(lambda operation=operation: call(model, "check_access_rights", [operation], {
        "raise_exception": False, "context": context,
    })) for operation in ("read", "create", "write", "unlink")}
    columns = ["id", "name", "model", "ttype", "state", "relation", "related", "store", "required", "readonly"]
    if origins_available:
        columns.append("modules")
    if fields["status"] == "ok" and isinstance(fields["value"], dict):
        provenance = table(call, "ir.model.fields", columns, [
            ["model", "=", model], ["name", "in", list(fields["value"])],
        ], limit, context)
    else:
        provenance = {"status": "not_attempted", "reason": "fields_unavailable"}
    return {
        "fetched_at": now().isoformat(), "fields": fields, "model_access": access,
        "field_origins": provenance,
        "views": table(call, "ir.ui.view", ["id", "name", "model", "type", "inherit_id", "active"], [
            ["model", "=", model],
        ], limit, context),
        "window_actions": table(call, "ir.actions.act_window", [
            "id", "name", "res_model", "view_mode", "domain", "context",
        ], [["res_model", "=", model]], limit, context),
    }


def discover(options, uid, secret, make_proxy):
    models = sorted(set(options.models or []))
    if len(models) > 20 or any(not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_.]*", model) for model in models):
        raise ValueError("Supply at most 20 valid model names.")
    if not 1 <= options.limit <= 10000:
        raise ValueError("Discovery limit must be between 1 and 10000 records per section.")
    companies = list(dict.fromkeys(options.company_ids or []))
    if any(company < 1 for company in companies):
        raise ValueError("Company IDs must be positive integers.")
    with make_proxy(options.url, "common", options.timeout) as common:
        version = common.version()
    identity = {"url": options.url, "database": options.db, "uid": uid}
    with make_proxy(options.url, "object", options.timeout) as remote:
        def call(model, method, args, kwargs):
            return remote.execute_kw(options.db, uid, secret, model, method, args, kwargs)

        user, context = scope_for_user(call, uid, companies)
        path = profile_path(identity, context)
        profile = None if options.refresh else cached_profile(path, identity, context, version, options.limit)
        reused = profile is not None
        if profile is None:
            inventory = inventory_for(call, context, options.limit)
            selected = context.get("allowed_company_ids", [])
            inventory["companies"] = table(call, "res.company", ["id", "name", "currency_id"], [
                ["id", "in", selected],
            ], options.limit, context) if selected else {"status": "not_attempted", "reason": "company_scope_unknown"}
            profile = {
                "schema_version": SCHEMA_VERSION, "identity": identity, "context": context,
                "server_version": version, "inventory_at": now().isoformat(),
                "limit": options.limit, "inventory": inventory, "model_details": {},
                "customization_signals": customization_signals(inventory),
            }
        profile["user_scope"] = user
        origins_available = profile["inventory"]["installed_addons"]["status"] in {"ok", "truncated"}
        for model in models:
            # Always refresh requested fields/access, even when the inventory is
            # reused. Schema visibility is not record-level permission evidence.
            profile["model_details"][model] = details_for(call, model, context, options.limit, origins_available)
    profile["updated_at"] = now().isoformat()
    profile["source_reference"] = source_reference(profile["inventory"], models)
    connection_store.save_private_file(json.dumps(profile, ensure_ascii=False, indent=2), path=path)
    return {
        "profile_path": str(path.resolve()), "identity": identity, "context": context,
        "inventory_reused": reused, "inventory_at": profile["inventory_at"],
        "inventory": {name: {"status": section["status"], "count": len(section.get("records", []))}
                      for name, section in profile["inventory"].items()},
        "requested_models": {model: profile["model_details"][model]["fields"]["status"] for model in models},
        "source_reference": {key: profile["source_reference"][key] for key in (
            "status", "revision", "matching_installed_names",
        ) if key in profile["source_reference"]},
        "note": "Metadata is account-scoped evidence. Unavailable/truncated sections are incomplete. Addon source and business-method contracts are not discovered by XML-RPC schema inspection.",
    }
