"""Per-user Python runtime and native credential store for App Store Connect."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import venv


# Preserve the original runtime location for existing installations.
APP_NAME = "app-store-connect-mcp"
SERVICE = "tech.jala.app-store-connect"
ACCOUNT = "api-key"


class StorageError(ValueError):
    pass


def state_directory() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    path = base / APP_NAME
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == "posix":
        path.chmod(0o700)
    return path


def runtime_python() -> Path:
    runtime = state_directory() / "runtime"
    return runtime / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def _runtime_has_dependencies(python: Path) -> bool:
    if not python.is_file():
        return False
    result = subprocess.run(
        [str(python), "-c", "import cryptography, keyring"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def install_runtime(plugin_root: Path) -> dict:
    python = runtime_python()
    if not _runtime_has_dependencies(python):
        venv_path = python.parents[1]
        venv.EnvBuilder(with_pip=True).create(venv_path)
        requirements = plugin_root / "scripts" / "requirements.txt"
        try:
            subprocess.run(
                [str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(requirements)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=240,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            raise StorageError("Could not install the local runtime. Check Python 3.9+, network access, then retry setup.") from None
    if not _runtime_has_dependencies(python):
        raise StorageError("The local runtime is incomplete. Run setup again to repair it.")
    return {"installed": True, "python": str(python)}


def _native_keyring():
    try:
        if sys.platform == "darwin":
            from keyring.backends.macOS import Keyring

            store = Keyring()
        elif sys.platform == "win32":
            from keyring.backends.Windows import WinVaultKeyring

            store = WinVaultKeyring()
            store.persist = "local machine"
        elif sys.platform.startswith("linux"):
            from keyring.backends.SecretService import Keyring

            store = Keyring()
        else:
            raise StorageError("Native credential storage is not supported on this operating system.")
        priority = store.priority
        if not isinstance(priority, (int, float)) or priority <= 0:
            raise StorageError("The OS secret store is unavailable or locked.")
        return store
    except StorageError:
        raise
    except Exception:
        raise StorageError("The OS secret store is unavailable or locked. Unlock it, then retry.") from None


def _store_call(store, method: str, *args):
    try:
        return getattr(store, method)(SERVICE, ACCOUNT, *args)
    except Exception:
        raise StorageError("Cannot access the OS secret store. Unlock it or allow access, then retry.") from None


def _validate_connection(value: dict) -> dict:
    if not isinstance(value, dict) or value.get("key_type") not in {"team", "individual"}:
        raise StorageError("Saved App Store Connect credentials are invalid. Run setup again.")
    expected = {"key_type", "key_id", "private_key"}
    if value["key_type"] == "team":
        expected.add("issuer_id")
    if set(value) != expected:
        raise StorageError("Saved App Store Connect credentials are invalid. Run setup again.")
    if not isinstance(value["key_id"], str) or not value["key_id"].strip():
        raise StorageError("Saved App Store Connect credentials are invalid. Run setup again.")
    if value["key_type"] == "team" and (not isinstance(value["issuer_id"], str) or not value["issuer_id"].strip()):
        raise StorageError("Saved team key is missing its Issuer ID. Run setup again.")
    if not isinstance(value["private_key"], str) or not value["private_key"].startswith("-----BEGIN PRIVATE KEY-----"):
        raise StorageError("Saved private key is invalid. Run setup again.")
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        key = serialization.load_pem_private_key(value["private_key"].encode("utf-8"), password=None)
        if not isinstance(key, ec.EllipticCurvePrivateKey) or key.curve.name != "secp256r1":
            raise ValueError
    except Exception:
        raise StorageError("The .p8 must contain an unencrypted P-256 private key. Run setup with the downloaded key.") from None
    return value


def save_connection(value: dict) -> str:
    connection = _validate_connection(value)
    store = _native_keyring()
    serialized = json.dumps(connection, separators=(",", ":"), ensure_ascii=False)
    _store_call(store, "set_password", serialized)
    saved = _store_call(store, "get_password")
    if not isinstance(saved, str) or saved != serialized:
        raise StorageError("Could not verify the saved credential in the OS secret store.")
    return "native"


def load_connection() -> dict:
    store = _native_keyring()
    raw = _store_call(store, "get_password")
    if raw is None:
        raise StorageError("App Store Connect is not connected. Run the app-store-connect-setup skill.")
    try:
        return _validate_connection(json.loads(raw))
    except (ValueError, TypeError, json.JSONDecodeError):
        raise StorageError("Saved App Store Connect credentials are invalid. Run setup again.") from None


def connection_status() -> dict:
    store = _native_keyring()
    raw = _store_call(store, "get_password")
    if raw is None:
        return {"configured": False, "storage": "native"}
    try:
        connection = _validate_connection(json.loads(raw))
    except (ValueError, TypeError, json.JSONDecodeError):
        raise StorageError("Saved App Store Connect credentials are invalid. Run setup again.") from None
    return {
        "configured": True,
        "storage": "native",
        "keyType": connection["key_type"],
        "keyId": connection["key_id"],
    }


def forget_connection() -> dict:
    store = _native_keyring()
    if _store_call(store, "get_password") is not None:
        _store_call(store, "delete_password")
    return {"forgotten": True, "note": "Local credential removed. The App Store Connect API key was not revoked."}
