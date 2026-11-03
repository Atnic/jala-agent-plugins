"""One setup page; independently selected, stored and verified Apple connections."""

import html
from pathlib import Path
from types import SimpleNamespace

import local_setup
import runtime
import server_store


def processor(profile=None):
    """Keep partial successes intact while the owner configures either connection."""
    selected = server_store.profile_name(profile) if profile is not None else None

    def state():
        def checked(read):
            try:
                return read()
            except (runtime.StorageError, ValueError):
                return {"configured": None, "error": "Connection status could not be read. Check the OS secret store or repair this connection."}
        return {"reporting": checked(runtime.connection_status),
                "server": checked(lambda: server_store.status(selected)) if selected else None,
                "completed": False}

    def process(payload):
        nonlocal selected
        if not isinstance(payload, dict) or set(payload) - {"action", "connection", "profile", "transactionId", "environment"}:
            raise ValueError("Use the setup page to select a connection.")
        action = payload.get("action")
        if action not in {"status", "connect-reporting", "connect-server", "verify-server", "finish"}:
            raise ValueError("Unknown setup action.")
        if "profile" in payload and action != "connect-reporting":
            selected = server_store.profile_name(payload["profile"])
        if action == "connect-reporting":
            connection = local_setup.validate_payload(payload.get("connection"))
            local_setup.verify_key(connection)
            runtime.save_connection(connection)
        elif action == "connect-server":
            if selected is None:
                raise ValueError("Choose a Server API profile name before saving its key.")
            connection = server_store.parse_setup(payload.get("connection"))
            server_store.save(selected, connection)
        verification = None
        if action == "verify-server":
            if selected is None or payload.get("environment") not in {"production", "sandbox"}:
                raise ValueError("Select a profile and its production or sandbox environment.")
            from server_api import execute
            verification = execute(SimpleNamespace(server_command="verify", profile=selected,
                                                   environment=payload["environment"],
                                                   transaction_id=payload.get("transactionId")), None)
        result = state()
        if verification is not None:
            result["lastVerification"] = verification
        if action == "finish":
            if not result["reporting"]["configured"] and not (result["server"] or {}).get("configured"):
                raise ValueError("Connect at least one service before finishing, or close the page to cancel.")
            result["completed"] = True
        return result

    return process


def run_setup(profile=None):
    if profile is not None:
        server_store.profile_name(profile)
    return local_setup.run_setup(
        form_path=Path(__file__).parents[1] / "assets" / "unified-setup.html",
        process=processor(profile),
        replacements={"__SERVER_PROFILE__": html.escape(profile or "", quote=True)})
