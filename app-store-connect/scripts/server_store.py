"""Independent named StoreKit connections in the OS-native secret store."""

import json
import re
from datetime import datetime, timezone

from runtime import StorageError, _native_keyring, _store_call, _validate_connection

SERVICE = "tech.jala.app-store-server"


def profile_name(name):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", name):
        raise ValueError("Profile must be 1–64 letters, digits, underscores, or hyphens.")
    return name


def validate(value):
    if not isinstance(value, dict) or set(value) != {
        "key_id", "issuer_id", "private_key", "bundle_id", "app_apple_id", "verified_environments"
    }:
        raise ValueError("Invalid Server API profile. Run server setup for this profile.")
    # Reuse key parsing while retaining an independent storage schema and namespace.
    _validate_connection({"key_type": "team", **{k: value[k] for k in ("key_id", "issuer_id", "private_key")}})
    if not re.fullmatch(r"[A-Z0-9]{10}", value["key_id"]):
        raise ValueError("Key ID must contain 10 uppercase letters or digits.")
    if not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value["issuer_id"]):
        raise ValueError("Issuer ID must be the UUID paired with the In-App Purchase key.")
    if not isinstance(value["bundle_id"], str) or not re.fullmatch(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", value["bundle_id"]):
        raise ValueError("Provide the app bundle ID, for example com.example.app.")
    if type(value["app_apple_id"]) is not int or value["app_apple_id"] <= 0:
        raise ValueError("Apple app ID must be a positive integer.")
    verified = value["verified_environments"]
    if not isinstance(verified, dict) or not set(verified) <= {"production", "sandbox"}:
        raise ValueError("Invalid verification state.")
    if any(not isinstance(v, str) for v in verified.values()):
        raise ValueError("Invalid verification timestamps.")
    return value


def _call(name, method, *args):
    return _store_call(_native_keyring(), method, *args, service=SERVICE, account=profile_name(name))


def load(name):
    raw = _call(name, "get_password")
    if raw is None:
        raise StorageError("Server API profile is not configured. Run server setup --profile NAME.")
    try:
        return validate(json.loads(raw))
    except (ValueError, TypeError):
        raise StorageError("Invalid Server API profile. Run server setup for this profile.") from None


def save(name, value):
    encoded = json.dumps(validate(value), separators=(",", ":"))
    _call(name, "set_password", encoded)
    if _call(name, "get_password") != encoded:
        raise StorageError("Could not verify the Server API profile in the OS secret store.")
    return "native"


def status(name):
    if _call(name, "get_password") is None:
        return {"profile": name, "configured": False, "storage": "native"}
    value = load(name)
    return {"profile": name, "configured": True, "storage": "native",
            "bundleId": value["bundle_id"], "appAppleId": value["app_apple_id"],
            "verifiedEnvironments": value["verified_environments"],
            "note": "Saved verification timestamps describe past successful checks, not current access."}


def forget(name):
    if _call(name, "get_password") is not None:
        _call(name, "delete_password")
    return {"profile": name, "forgotten": True, "note": "Local Server API profile removed; Apple key unchanged."}


def mark_verified(name, environment, expected_connection):
    value = load(name)
    identity_fields = ("key_id", "issuer_id", "private_key", "bundle_id", "app_apple_id")
    if any(value[field] != expected_connection[field] for field in identity_fields):
        raise StorageError("Server API profile changed during verification. Verify the current profile again.")
    value["verified_environments"][environment] = datetime.now(timezone.utc).isoformat()
    save(name, value)


def parse_setup(payload):
    if not isinstance(payload, dict) or set(payload) != {"keyId", "issuerId", "privateKey", "bundleId", "appAppleId"}:
        raise ValueError("Provide the In-App Purchase Key ID, matching Issuer ID, .p8 file, bundle ID and Apple app ID.")
    try:
        app_id = int(payload["appAppleId"])
    except (ValueError, TypeError):
        raise ValueError("Apple app ID must be a positive integer.") from None
    return validate({"key_id": payload["keyId"].strip().upper(),
                     "issuer_id": payload["issuerId"].strip(),
                     "private_key": payload["privateKey"],
                     "bundle_id": payload["bundleId"].strip(), "app_apple_id": app_id,
                     "verified_environments": {}})


def setup(name):
    from pathlib import Path
    from local_setup import run_setup

    profile_name(name)

    return run_setup(form_path=Path(__file__).parents[1] / "assets" / "server-setup.html",
                     validate=parse_setup, verify=lambda value: None,
                     save=lambda value: save(name, value),
                     describe=lambda value: {"profile": name, "verification": "unverified"})
