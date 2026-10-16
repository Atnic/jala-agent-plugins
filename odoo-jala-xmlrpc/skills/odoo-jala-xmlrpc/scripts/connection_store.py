"""Per-user Odoo connection storage, independent of the plugin install/cache."""

import hmac
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import venv


SERVICE = "tech.jala.odoo.xmlrpc"
ACCOUNT = "connection"


class StorageError(ValueError):
    pass


def state_directory():
    override = os.environ.get("ODOO_JALA_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "odoo-jala-xmlrpc"
    return Path.home() / ".config/odoo-jala-xmlrpc"


def connection_path():
    return state_directory() / "connection.json"


def runtime_python():
    runtime = state_directory() / "runtime"
    return runtime / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def install_runtime():
    python = runtime_python()
    venv.EnvBuilder(with_pip=True).create(python.parents[1])
    subprocess.run([
        str(python), "-m", "pip", "install", "-r",
        str(Path(__file__).with_name("requirements.txt")),
    ], check=True)
    return {"installed": True, "message": "Native credential storage dependencies installed."}


def credential_store():
    """Select native backends explicitly, never a third-party plaintext backend."""
    try:
        if sys.platform == "darwin":
            from keyring.backends.macOS import Keyring
            return Keyring()
        if sys.platform == "win32":
            from keyring.backends.Windows import WinVaultKeyring
            store = WinVaultKeyring()
            store.persist = "local machine"
            _ = store.priority
            return store
        if sys.platform.startswith("linux"):
            from keyring.backends.SecretService import Keyring
            store = Keyring()
            _ = store.priority
            return store
    except ImportError:
        raise StorageError("Run install-runtime to enable native credential storage.") from None
    except Exception:
        raise StorageError("Native credential storage is unavailable or locked.") from None
    raise StorageError("Native credential storage is not supported on this operating system.")


def store_operation(store, operation, *args):
    try:
        return getattr(store, operation)(SERVICE, ACCOUNT, *args)
    except Exception:
        # Backend exceptions can contain the secret. Keep them out of logs/UI.
        raise StorageError("Cannot access native credential storage. Unlock it or allow access and retry.") from None


def validate_connection(value):
    if not isinstance(value, dict) or set(value) != {"url", "db", "username", "secret"}:
        raise StorageError("Saved connection is invalid. Run setup-web again.")
    if any(not isinstance(item, str) or not item or len(item) > 4096 for item in value.values()):
        raise StorageError("Connection fields must be nonempty strings up to 4096 characters.")
    return value


def restrict_windows_file(path):
    identity = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"], capture_output=True, check=True).stdout
    sid = re.search(rb"S-1-[0-9-]+", identity)
    if not sid:
        raise StorageError("Cannot identify the Windows user for private file permissions.")
    subprocess.run([
        "icacls", str(path), "/inheritance:r", "/grant:r", "*" + sid.group().decode("ascii") + ":F",
    ], capture_output=True, check=True)


def save_private_file(serialized, path=None):
    path = Path(path) if path is not None else connection_path()
    if path.parent.is_symlink() or path.is_symlink():
        raise StorageError("Credential path cannot be a symlink.")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == "posix":
        path.parent.chmod(0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".connection-")
    try:
        if os.name == "posix":
            os.fchmod(fd, 0o600)
        elif os.name == "nt":
            restrict_windows_file(temporary)
        else:
            raise StorageError("Private-file storage is unavailable on this operating system.")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except (OSError, subprocess.CalledProcessError):
        raise StorageError("Could not save connection with private file permissions.") from None
    finally:
        if fd is not None:
            os.close(fd)
        if os.path.exists(temporary):
            os.unlink(temporary)


def decode_connection(raw):
    try:
        return validate_connection(json.loads(raw))
    except (ValueError, TypeError):
        raise StorageError("Saved connection is invalid. Run setup-web again.") from None


def load_connection():
    path = connection_path()
    # A fallback may be newer than an inaccessible native copy.
    if path.exists() or path.is_symlink():
        if (path.is_symlink() or not path.is_file() or path.parent.is_symlink()
                or (os.name == "posix" and path.stat().st_mode & 0o077)):
            raise StorageError("Saved connection must be a regular private file (chmod 600 on macOS/Linux).")
        try:
            return decode_connection(path.read_text(encoding="utf-8")), "private-file"
        except (OSError, UnicodeError):
            raise StorageError("Cannot read saved connection. Run setup-web again.") from None
    try:
        store = credential_store()
    except StorageError:
        # No file and no native backend: allow environment-only use and setup.
        return None, None
    raw = store_operation(store, "get_password")
    return (decode_connection(raw), "native") if raw is not None else (None, None)


def save_connection(connection):
    serialized = json.dumps(validate_connection(connection), ensure_ascii=False)
    try:
        store = credential_store()
        store_operation(store, "set_password", serialized)
        saved = store_operation(store, "get_password")
        if not isinstance(saved, str) or not hmac.compare_digest(saved.encode(), serialized.encode()):
            raise StorageError("Cannot verify native credential storage.")
    except StorageError:
        save_private_file(serialized)
        return "private-file"
    connection_path().unlink(missing_ok=True)
    return "native"


def forget_connection():
    try:
        store = credential_store()
        if store_operation(store, "get_password") is not None:
            store_operation(store, "delete_password")
    except StorageError:
        raise StorageError("Could not confirm removal of the native credential. Restore access and run forget again.") from None
    finally:
        connection_path().unlink(missing_ok=True)
    return {"forgotten": True, "message": "Saved connection removed locally; the Odoo key is not revoked. Environment overrides remain active."}
