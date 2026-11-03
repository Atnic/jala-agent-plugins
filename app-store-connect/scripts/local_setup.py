#!/usr/bin/env python3
"""Import an App Store Connect key through a temporary loopback browser form."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import re
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from asc_auth import make_jwt
from runtime import StorageError, connection_status, forget_connection, save_connection


API_BASE = "https://api.appstoreconnect.apple.com"
FORM_PATH = Path(__file__).parents[1] / "assets" / "setup.html"
KEY_ID_RE = re.compile(r"^[A-Z0-9]{10}$")
ISSUER_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def verify_key(connection: dict) -> None:
    token = make_jwt(connection)
    request = urllib.request.Request(
        f"{API_BASE}/v1/apps?limit=1",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=30) as response:
            if response.status != 200:
                raise ValueError("Apple did not accept the verification request. Check the key and its App Store Connect role.")
            response.read(64 * 1024)
    except urllib.error.HTTPError as error:
        if error.code == 401:
            raise ValueError("Apple rejected the API key. Check Key ID, key type, private key, and team Issuer ID.") from None
        if error.code == 403:
            raise ValueError("Apple accepted the request format but this key cannot list apps. Grant an appropriate App Store Connect role, then retry setup.") from None
        raise ValueError(f"Apple returned HTTP {error.code} while verifying the key. Setup did not save the key.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ValueError("Could not reach Apple to verify the key. Check the network and retry setup.") from None


def validate_payload(payload) -> dict:
    if not isinstance(payload, dict) or set(payload) != {"keyType", "keyId", "issuerId", "privateKey"}:
        raise ValueError("Provide the key type, Key ID, team Issuer ID when required, and the downloaded .p8 file.")
    key_type = payload["keyType"]
    key_id = payload["keyId"]
    issuer_id = payload["issuerId"]
    private_key = payload["privateKey"]
    if key_type not in {"team", "individual"}:
        raise ValueError("Choose a team or individual API key.")
    if not isinstance(key_id, str) or not KEY_ID_RE.fullmatch(key_id.strip().upper()):
        raise ValueError("Key ID must be the 10-character identifier shown beside the downloaded key.")
    if not isinstance(private_key, str) or len(private_key) > 8192 or not private_key.startswith("-----BEGIN PRIVATE KEY-----"):
        raise ValueError("Choose the downloaded, unencrypted .p8 private key file.")
    connection = {
        "key_type": key_type,
        "key_id": key_id.strip().upper(),
        "private_key": private_key.strip() + "\n",
    }
    if key_type == "team":
        if not isinstance(issuer_id, str) or not ISSUER_RE.fullmatch(issuer_id.strip()):
            raise ValueError("A team key requires the UUID Issuer ID shown on App Store Connect's Integrations page.")
        connection["issuer_id"] = issuer_id.strip().lower()
    elif issuer_id:
        raise ValueError("Individual keys do not use an Issuer ID. Clear the Issuer ID field.")
    try:
        serialization.load_pem_private_key(connection["private_key"].encode("utf-8"), password=None)
    except Exception:
        raise ValueError("Apple's .p8 file could not be read as an unencrypted private key.") from None
    return connection


def setup_server(*, form_path=FORM_PATH, validate=validate_payload,
                 verify=verify_key, save=save_connection, describe=None,
                 process=None, replacements=None):
    session = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(20)
    html = form_path.read_text(encoding="utf-8").replace("__NONCE__", nonce)
    for key, value in (replacements or {}).items():
        html = html.replace(key, value)
    html = html.encode("utf-8")
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(5)
            super().setup()

        def log_message(self, _format, *_args):
            return

        def send_json(self, status: int, value: dict):
            body = json.dumps(value).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; connect-src 'self'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            try:
                self.wfile.write(body)
            except OSError:
                pass

        def authorized_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.authorized_host() or self.path != "/":
                self.send_json(404, {"error": "Not found."})
                return
            if self.server.completed or time.monotonic() >= self.server.deadline:
                self.send_json(410, {"error": "This setup session has ended. Run setup again."})
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; img-src data:; connect-src 'self'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(html)

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            supplied = self.headers.get("X-Setup-Token", "")
            if (not self.authorized_host() or self.path != "/api/setup"
                    or self.headers.get("Origin") != origin
                    or not hmac.compare_digest(supplied.encode(), session.encode())):
                self.send_json(403, {"error": "Invalid setup session. Run setup again and use its new local link."})
                return
            if self.headers.get("Content-Type") != "application/json":
                self.send_json(415, {"error": "Expected a local JSON upload."})
                return
            if not lock.acquire(blocking=False):
                self.send_json(409, {"error": "A key verification is already in progress."})
                return
            try:
                if self.server.completed or time.monotonic() >= self.server.deadline:
                    self.send_json(410, {"error": "This setup session has ended. Run setup again."})
                    return
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16_384:
                    raise ValueError("The local upload is empty or too large.")
                payload = json.loads(self.rfile.read(length))
                if process is not None:
                    result = process(payload)
                    self.server.connected_key = result
                    self.server.completed = result.get("completed") is True
                    self.send_json(200, {"ok": True, **result})
                    return
                connection = validate(payload)
                verify(connection)
                storage = save(connection)
                self.server.connected_key = (describe(connection) if describe else
                                             {"keyType": connection["key_type"], "keyId": connection["key_id"]})
                self.server.completed = True
                self.send_json(200, {"ok": True, "storage": storage, **self.server.connected_key})
            except (ValueError, OSError, StorageError) as error:
                message = str(error) if type(error) is ValueError else str(error)
                self.send_json(400, {"error": message})
            except Exception:
                self.send_json(400, {"error": "Key import failed. Check the key, OS secret-store access, and network, then retry."})
            finally:
                lock.release()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    server.timeout = 0.5
    server.completed = False
    server.connected_key = {}
    server.deadline = time.monotonic() + 900
    server.setup_url = f"http://127.0.0.1:{server.server_port}/#session={session}"
    return server


def run_setup(**options) -> dict:
    with setup_server(**options) as server:
        print("Local Apple API setup form: " + server.setup_url, file=sys.stderr, flush=True)
        if not webbrowser.open(server.setup_url):
            raise ValueError("Could not open a browser. Open the local setup URL printed above, then retry setup.")
        while not server.completed and time.monotonic() < server.deadline:
            server.handle_request()
        if not server.completed:
            if options.get("process") is not None:
                raise ValueError("Setup expired before Done. Connections already saved remain in the OS secret store; reopen setup to check their status.")
            raise ValueError("Setup expired without importing a key. Run setup again.")
        if server.connected_key.get("completed") is True:
            return server.connected_key
        state = {"saved": True} if server.connected_key.get("verification") == "unverified" else {"connected": True}
        return {**state, "storage": "native", **server.connected_key}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: local_setup.py setup|status|forget", file=sys.stderr)
        return 2
    command = sys.argv[1]
    try:
        if command == "setup":
            result = run_setup()
        elif command == "status":
            result = connection_status()
        elif command == "forget":
            result = forget_connection()
        else:
            raise ValueError("Unknown local action.")
        print(json.dumps(result))
        return 0
    except (StorageError, ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
