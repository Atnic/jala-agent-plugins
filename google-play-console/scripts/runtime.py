"""Per-user runtime, profile metadata, and native credential storage."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid
import venv


APP_NAME = "google-play-console-mcp"
SERVICE = "tech.jala.google-play-console"
PROFILE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}$")


class StorageError(ValueError):
    pass


def state_directory() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    directory = base / APP_NAME
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == "posix":
        directory.chmod(0o700)
    return directory


def profiles_path() -> Path:
    return state_directory() / "profiles.json"


def runtime_python() -> Path:
    runtime = state_directory() / "runtime"
    return runtime / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def _runtime_has_dependencies(python: Path) -> bool:
    if not python.is_file():
        return False
    result = subprocess.run(
        [str(python), "-c", "import google.auth, google.oauth2.credentials, google.oauth2.service_account, jsonschema, keyring, requests"],
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


def _store_call(store, method: str, account: str, *args):
    try:
        return getattr(store, method)(SERVICE, account, *args)
    except Exception:
        raise StorageError("Cannot access the OS secret store. Unlock it or allow access, then retry.") from None


def _validate_profile(profile: dict) -> dict:
    if not isinstance(profile, dict):
        raise StorageError("Saved Play Console profile metadata is invalid. Run setup again.")
    profile_id = profile.get("id")
    name = profile.get("name")
    auth_type = profile.get("authType")
    if not isinstance(profile_id, str) or not re.fullmatch(r"[0-9a-f]{32}", profile_id):
        raise StorageError("Saved Play Console profile metadata is invalid. Run setup again.")
    if not isinstance(name, str) or not PROFILE_NAME_RE.fullmatch(name):
        raise StorageError("Saved Play Console profile metadata is invalid. Run setup again.")
    if auth_type not in {"oauth", "service-account"}:
        raise StorageError("Saved Play Console profile metadata is invalid. Run setup again.")
    return {
        "id": profile_id,
        "name": name,
        "authType": auth_type,
        "createdAt": profile.get("createdAt", ""),
    }


def _read_profiles() -> list[dict]:
    path = profiles_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise StorageError("Saved Play Console profile metadata could not be read. Remove the damaged profiles.json after preserving any needed profile names, then reconnect.") from None
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("profiles"), list):
        raise StorageError("Saved Play Console profile metadata is invalid. Repair profiles.json or reconnect.")
    profiles = [_validate_profile(profile) for profile in data["profiles"]]
    ids = [profile["id"] for profile in profiles]
    names = [profile["name"].casefold() for profile in profiles]
    if len(ids) != len(set(ids)) or len(names) != len(set(names)):
        raise StorageError("Saved Play Console profiles contain duplicate IDs or names. Repair profiles.json before reconnecting.")
    return profiles


def _write_profiles(profiles: list[dict]) -> None:
    path = profiles_path()
    serialized = json.dumps({"version": 1, "profiles": profiles}, ensure_ascii=False, indent=2) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".profiles-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name == "posix":
            temporary.chmod(0o600)
        os.replace(temporary, path)
        if os.name == "posix":
            path.chmod(0o600)
    except OSError:
        if temporary:
            temporary.unlink(missing_ok=True)
        raise StorageError("Could not save local Play Console profile metadata.") from None


def profile_by_name(name: str) -> dict:
    if not isinstance(name, str) or not name.strip():
        raise StorageError("Choose a named Play Console account profile.")
    for profile in _read_profiles():
        if profile["name"].casefold() == name.strip().casefold():
            return profile
    raise StorageError(f"No Play Console profile named {name!r} is connected. Call gpc_list_profiles or gpc_setup.")


def list_profiles() -> dict:
    profiles = []
    for profile in _read_profiles():
        profiles.append({
            "name": profile["name"],
            "authType": profile["authType"],
        })
    return {"profiles": profiles, "storage": "native"}


def _validate_secret(profile: dict, value: dict) -> dict:
    if not isinstance(value, dict) or value.get("authType") != profile["authType"]:
        raise StorageError("Saved Play Console credentials are invalid. Run setup again.")
    if profile["authType"] == "oauth":
        if not isinstance(value.get("clientId"), str) or not value["clientId"].endswith(".apps.googleusercontent.com"):
            raise StorageError("Saved Desktop OAuth client details are invalid. Run setup again.")
        if not isinstance(value.get("clientSecret", ""), str):
            raise StorageError("Saved Desktop OAuth client details are invalid. Run setup again.")
        if not isinstance(value.get("refreshToken"), str) or not value["refreshToken"]:
            raise StorageError("Saved OAuth refresh token is missing. Reconnect this profile.")
    else:
        service_account = value.get("serviceAccount")
        if not isinstance(service_account, dict) or service_account.get("type") != "service_account":
            raise StorageError("Saved service-account credentials are invalid. Run setup again.")
        if not isinstance(service_account.get("private_key"), str) or "PRIVATE KEY" not in service_account["private_key"]:
            raise StorageError("Saved service-account private key is invalid. Run setup again.")
    return value


def save_secret(profile_id: str, value: dict) -> None:
    serialized = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    store = _native_keyring()
    _store_call(store, "set_password", profile_id, serialized)
    saved = _store_call(store, "get_password", profile_id)
    if not isinstance(saved, str) or saved != serialized:
        raise StorageError("Could not verify the credential in the OS secret store.")


def load_secret(profile: dict) -> dict:
    store = _native_keyring()
    raw = _store_call(store, "get_password", profile["id"])
    if raw is None:
        raise StorageError(f"The secret for Play Console profile {profile['name']!r} is missing. Reconnect that profile.")
    try:
        value = json.loads(raw)
    except (UnicodeError, ValueError):
        raise StorageError("Saved Play Console credentials are invalid. Run setup again.") from None
    return _validate_secret(profile, value)


def save_profile(name: str, auth_type: str, credential: dict) -> dict:
    name = name.strip() if isinstance(name, str) else ""
    if not PROFILE_NAME_RE.fullmatch(name):
        raise StorageError("Profile name must start with a letter or number and contain at most 64 letters, numbers, spaces, dots, underscores, or hyphens.")
    if auth_type not in {"oauth", "service-account"}:
        raise StorageError("Choose OAuth or service-account authentication.")
    profiles = _read_profiles()
    if any(profile["name"].casefold() == name.casefold() for profile in profiles):
        raise StorageError(f"A Play Console profile named {name!r} already exists. Choose another name or forget the existing profile first.")
    profile = {
        "id": uuid.uuid4().hex,
        "name": name,
        "authType": auth_type,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    _validate_profile(profile)
    _validate_secret(profile, credential)
    save_secret(profile["id"], credential)
    try:
        _write_profiles([*profiles, profile])
    except Exception:
        try:
            _store_call(_native_keyring(), "delete_password", profile["id"])
        except Exception:
            pass
        raise
    return {"name": name, "authType": auth_type, "storage": "native"}


def update_secret(profile: dict, value: dict) -> None:
    _validate_secret(profile, value)
    save_secret(profile["id"], value)


def forget_profile(name: str) -> dict:
    profile = profile_by_name(name)
    profiles = _read_profiles()
    store = _native_keyring()
    if _store_call(store, "get_password", profile["id"]) is not None:
        _store_call(store, "delete_password", profile["id"])
    _write_profiles([item for item in profiles if item["id"] != profile["id"]])
    return {"forgotten": profile["name"], "note": "Local credentials were removed. Google Play Console access for the identity was not revoked."}


def connection_status() -> dict:
    profiles = []
    for profile in _read_profiles():
        try:
            load_secret(profile)
            configured = True
        except StorageError as error:
            if str(error).startswith("The secret for Play Console profile"):
                configured = False
            else:
                raise
        profiles.append({
            "name": profile["name"],
            "authType": profile["authType"],
            "configured": configured,
        })
    return {"configured": bool(profiles) and all(item["configured"] for item in profiles), "profiles": profiles, "storage": "native"}
