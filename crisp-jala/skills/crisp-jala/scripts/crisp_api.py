"""Import a Crisp browser session and make requests using the OS secret store."""

import argparse
import base64
import hmac
import json
import re
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import venv


API_URL = "https://api.crisp.chat"
SERVICE = "tech.jala.crisp"
ACCOUNT = "connection"


def runtime_python():
    root = Path.home() / ".config/crisp-jala/runtime"
    return root / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def install_runtime():
    python = runtime_python()
    venv.EnvBuilder(with_pip=True).create(python.parents[1])
    subprocess.run([str(python), "-m", "pip", "install", "-r",
                    str(Path(__file__).with_name("requirements.txt"))], check=True)
    return {"installed": True, "python": str(python)}


def credential_store():
    try:
        if sys.platform == "darwin":
            from keyring.backends.macOS import Keyring
            return Keyring()
        if sys.platform == "win32":
            from keyring.backends.Windows import WinVaultKeyring
            store = WinVaultKeyring()
            store.persist = "local machine"
        elif sys.platform.startswith("linux"):
            from keyring.backends.SecretService import Keyring
            store = Keyring()
        else:
            raise ValueError("Unsupported operating system for native secret storage.")
        _ = store.priority
        return store
    except ImportError:
        raise ValueError("Run install-runtime, then use its Python for this helper.") from None
    except Exception:
        raise ValueError("Native secret store unavailable. Unlock or configure it and retry.") from None


def store_operation(operation, *args):
    store = credential_store()
    try:
        return getattr(store, operation)(SERVICE, ACCOUNT, *args)
    except Exception:
        raise ValueError("Cannot access the native secret store. Unlock it or allow access and retry.") from None


def validate_connection(value):
    fields = {"token_id", "token_key", "website_id"}
    if (not isinstance(value, dict) or set(value) != fields
            or any(not isinstance(v, str) or not v.strip() or len(v) > 4096
                   or any(ord(c) < 32 or ord(c) == 127 for c in v) for v in value.values())
            or ":" in value["token_id"]):
        raise ValueError("Invalid connection fields. Enter the token pair and exact workspace ID.")
    return value


def load_connection():
    raw = store_operation("get_password")
    if raw is None:
        raise ValueError("No saved connection. Run the browser-login setup workflow.")
    try:
        return validate_connection(json.loads(raw))
    except (ValueError, TypeError):
        raise ValueError("Invalid saved connection. Repeat the browser-login setup workflow.") from None


def save_connection(value):
    serialized = json.dumps(validate_connection(value))
    store_operation("set_password", serialized)
    saved = store_operation("get_password")
    if not isinstance(saved, str) or not hmac.compare_digest(saved.encode(), serialized.encode()):
        raise ValueError("Could not verify the saved connection.")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(connection, method="GET", path="", body=None):
    validate_connection(connection)
    # Caller supplies a relative route inside this saved workspace only.
    parsed = urllib.parse.urlsplit(path)
    decoded = urllib.parse.unquote(parsed.path)
    if (parsed.scheme or parsed.netloc or parsed.fragment or path.startswith("/")
            or "\\" in decoded or any(part in (".", "..") for part in decoded.split("/"))
            or any(ord(c) < 32 or ord(c) == 127 for c in path)):
        raise ValueError("Path must be relative to the saved workspace, without traversal or a URL.")
    method = method.upper()
    if method not in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"}:
        raise ValueError("Unsupported HTTP method.")
    workspace = urllib.parse.quote(connection["website_id"], safe="")
    url = f"{API_URL}/v1/website/{workspace}"
    if path:
        url += ("" if path.startswith("?") else "/") + path
    token = base64.b64encode((connection["token_id"] + ":" + connection["token_key"]).encode()).decode()
    headers = {"Authorization": "Basic " + token, "Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=30) as response:
            raw = response.read()
            result = json.loads(raw) if raw else None
            if isinstance(result, dict) and result.get("error") is True:
                raise ValueError("Crisp reported an API error. Check route, scope, and input.")
            return {"status": response.status, "response": result}
    except urllib.error.HTTPError as error:
        raise ValueError(f"Crisp HTTP {error.code}. Check credentials, scope, and route; request was not retried.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ValueError("Crisp connection failed. Request was not retried; verify state before repeating a write.") from None
    except (json.JSONDecodeError, UnicodeError):
        raise ValueError("Crisp returned an unexpected response; verify state before repeating a write.") from None


def verify_and_save(connection):
    request(connection)
    save_connection(connection)


def import_session(value):
    """Consume only an observed Crisp read request, never a full network dump."""
    if not isinstance(value, dict) or set(value) != {"request_url", "authorization"}:
        raise ValueError("Expected request_url and authorization from a Crisp read request.")
    url, authorization = value["request_url"], value["authorization"]
    if not isinstance(url, str) or not isinstance(authorization, str):
        raise ValueError("Invalid session import fields.")
    parsed = urllib.parse.urlsplit(url)
    match = re.fullmatch(
        r"/api/v1/website/([0-9a-fA-F-]{36})/(?:conversations/[0-9]+|conversation/[^/]+/messages)",
        parsed.path,
    )
    if (parsed.scheme != "https" or parsed.netloc != "app.crisp.chat"
            or parsed.fragment or not match or not authorization.startswith("Basic ")):
        raise ValueError("Use the Basic header from a Crisp inbox or message-list request on app.crisp.chat.")
    try:
        decoded = base64.b64decode(authorization[6:], validate=True).decode("utf-8")
        token_id, token_key = decoded.split(":", 1)
        connection = validate_connection({"token_id": token_id, "token_key": token_key,
                                          "website_id": match.group(1)})
    except (ValueError, UnicodeError):
        raise ValueError("Invalid Basic session credential. Capture a fresh Crisp request.") from None
    verify_and_save(connection)
    return {"saved": True, "storage": "native", "credential_type": "user-session",
            "website_id": connection["website_id"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("install-runtime")
    commands.add_parser("import-session", help="Verify and save an observed browser request from JSON stdin")
    commands.add_parser("status")
    commands.add_parser("forget")
    req = commands.add_parser("request")
    req.add_argument("path", nargs="?", default="", help="Workspace-relative API route")
    req.add_argument("--method", default="GET")
    req.add_argument("--body", type=Path, help="JSON payload file")
    args = parser.parse_args()
    try:
        if args.command == "install-runtime":
            result = install_runtime()
        elif args.command == "import-session":
            raw = sys.stdin.read(16385)
            if len(raw) > 16384:
                raise ValueError("Session import is too large; send only request_url and authorization.")
            try:
                value = json.loads(raw)
            except ValueError:
                raise ValueError("Session import must be JSON on stdin.") from None
            result = import_session(value)
        elif args.command == "forget":
            if store_operation("get_password") is not None:
                store_operation("delete_password")
            result = {"forgotten": True, "note": "Local connection removed; Crisp token is not revoked."}
        elif args.command == "status":
            connection = load_connection()
            result = {"configured": True, "storage": "native", "website_id": connection["website_id"], "api_url": API_URL}
        else:
            body = json.loads(args.body.read_text()) if args.body else None
            result = request(load_connection(), args.method, args.path, body)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        # Only deliberately sanitized messages leave the helper.
        message = str(error) if type(error) is ValueError else "Local operation failed. Check input file and runtime setup."
        print(json.dumps({"error": message}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
