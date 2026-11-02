#!/usr/bin/env python3
"""Import local Google Play Console OAuth or service-account credentials."""

from __future__ import annotations

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
from pathlib import Path
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser

from google_auth import build_authorization_url, exchange_code, new_pkce_pair, validate_oauth_client, validate_service_account
from runtime import PROFILE_NAME_RE, StorageError, list_profiles, save_profile


FORM_PATH = Path(__file__).parents[1] / "assets" / "setup.html"
ICON_PATH = Path(__file__).parents[1] / "assets" / "google-play-console-icon.png"
MAX_SETUP_BODY = 1_048_576


def _validate_profile_name(payload: dict) -> str:
    name = payload.get("profileName")
    if not isinstance(name, str) or not PROFILE_NAME_RE.fullmatch(name.strip()):
        raise ValueError("Profile name must start with a letter or number and contain at most 64 letters, numbers, spaces, dots, underscores, or hyphens.")
    for profile in list_profiles()["profiles"]:
        if profile["name"].casefold() == name.strip().casefold():
            raise ValueError(f"A Play Console profile named {name.strip()!r} already exists. Choose another name or forget the existing profile first.")
    return name.strip()


def setup_server():
    session = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(20)
    icon_data = base64.b64encode(ICON_PATH.read_bytes()).decode("ascii")
    html = (
        FORM_PATH.read_text(encoding="utf-8")
        .replace("__NONCE__", nonce)
        .replace("__ICON_DATA__", icon_data)
        .encode("utf-8")
    )

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(5)
            super().setup()

        def log_message(self, _format, *_args):
            return

        def send_json(self, status: int, value: dict):
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; img-src data:; connect-src 'self'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            try:
                self.wfile.write(body)
            except OSError:
                pass

        def send_page(self, body: bytes, status: int = 200):
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; img-src data:; connect-src 'self'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            try:
                self.wfile.write(body)
            except OSError:
                pass

        def authorized_host(self) -> bool:
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def authorized_post(self, path: str) -> bool:
            origin = f"http://127.0.0.1:{self.server.server_port}"
            token = self.headers.get("X-Setup-Token", "")
            return (
                self.authorized_host()
                and self.path == path
                and self.headers.get("Origin") == origin
                and hmac.compare_digest(token.encode(), session.encode())
                and self.headers.get("Content-Type") == "application/json"
            )

        def read_payload(self) -> dict:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise ValueError("The local setup request has an invalid length.") from None
            if not 0 < length <= MAX_SETUP_BODY:
                raise ValueError("The local setup request is empty or too large.")
            try:
                payload = json.loads(self.rfile.read(length))
            except (UnicodeError, ValueError):
                raise ValueError("The local setup request was not valid JSON.") from None
            if not isinstance(payload, dict):
                raise ValueError("The local setup request must be a JSON object.")
            return payload

        def do_GET(self):
            if not self.authorized_host():
                self.send_json(404, {"error": "Not found."})
                return
            if self.server.completed or time.monotonic() >= self.server.deadline:
                self.send_json(410, {"error": "This setup session has ended. Run setup again."})
                return
            parsed = urllib.parse.urlsplit(self.path)
            if parsed.path == "/":
                if parsed.query:
                    self.send_json(404, {"error": "Not found."})
                    return
                self.send_page(html)
                return
            if parsed.path != "/oauth/callback":
                self.send_json(404, {"error": "Not found."})
                return

            flow = self.server.pending_oauth
            params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            supplied_state = params.get("state", [""])[0]
            if not flow or not hmac.compare_digest(supplied_state.encode(), flow["state"].encode()):
                self.send_json(403, {"error": "Invalid OAuth state. Run setup again."})
                return
            if params.get("error"):
                self.server.completed = True
                self.server.result = {"error": "Google OAuth was cancelled or denied. No profile was saved."}
                self.send_page(b"<!doctype html><html><meta charset=utf-8><title>Connection cancelled</title><p>Google sign-in was cancelled. Return to your agent and run setup again.</p></html>")
                return
            code = params.get("code", [""])[0]
            try:
                secret_data = exchange_code(flow["oauthClient"], code, flow["redirectUri"], flow["verifier"])
                result = save_profile(
                    flow["profileName"],
                    "oauth",
                    secret_data,
                )
            except (ValueError, StorageError) as error:
                self.server.completed = True
                self.server.result = {"error": str(error)}
                self.send_page(b"<!doctype html><html><meta charset=utf-8><title>Connection failed</title><p>Google sign-in completed, but the profile could not be saved. Return to your agent for details.</p></html>", 400)
                return
            self.server.completed = True
            self.server.result = result
            self.send_page(b"<!doctype html><html><meta charset=utf-8><title>Connected</title><p>Google Play Console profile connected. Return to your agent.</p></html>")

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if (
                not self.authorized_host()
                or self.headers.get("Origin") != origin
                or not hmac.compare_digest(self.headers.get("X-Setup-Token", "").encode(), session.encode())
            ):
                self.send_json(403, {"error": "Invalid local setup session. Run setup again."})
                return
            if self.headers.get("Content-Type") != "application/json":
                self.send_json(415, {"error": "Expected a local JSON setup request."})
                return
            if self.server.completed or time.monotonic() >= self.server.deadline:
                self.send_json(410, {"error": "This setup session has ended. Run setup again."})
                return
            if not self.server.setup_lock.acquire(blocking=False):
                self.send_json(409, {"error": "Another setup action is already in progress."})
                return
            try:
                if self.path == "/api/oauth/start":
                    payload = self.read_payload()
                    if set(payload) != {"profileName", "oauthClientJson"}:
                        raise ValueError("Provide a profile name and the downloaded Desktop OAuth client JSON file.")
                    name = _validate_profile_name(payload)
                    raw_client = payload["oauthClientJson"]
                    if not isinstance(raw_client, str) or not raw_client or len(raw_client) > 256_000:
                        raise ValueError("The OAuth client JSON file is empty or too large.")
                    try:
                        oauth_client = validate_oauth_client(json.loads(raw_client))
                    except (UnicodeError, ValueError):
                        raise ValueError("Choose a valid Google Cloud Desktop OAuth client JSON file.") from None
                    verifier, challenge = new_pkce_pair()
                    state = secrets.token_urlsafe(32)
                    redirect_uri = f"http://127.0.0.1:{self.server.server_port}/oauth/callback"
                    authorization_url = build_authorization_url(oauth_client, redirect_uri, state, challenge)
                    self.server.pending_oauth = {
                        "profileName": name,
                        "oauthClient": oauth_client,
                        "verifier": verifier,
                        "state": state,
                        "redirectUri": redirect_uri,
                    }
                    self.send_json(200, {"authorizationUrl": authorization_url})
                    return
                if self.path == "/api/service-account":
                    payload = self.read_payload()
                    if set(payload) != {"profileName", "serviceAccountJson"}:
                        raise ValueError("Provide a profile name and the downloaded service-account JSON file.")
                    name = _validate_profile_name(payload)
                    raw_account = payload["serviceAccountJson"]
                    if not isinstance(raw_account, str) or len(raw_account) > 256_000:
                        raise ValueError("The service-account JSON file is empty or too large.")
                    try:
                        service_account = json.loads(raw_account)
                    except (UnicodeError, ValueError):
                        raise ValueError("The selected file is not valid JSON.") from None
                    service_account = validate_service_account(service_account)
                    result = save_profile(
                        name,
                        "service-account",
                        {"authType": "service-account", "serviceAccount": service_account},
                    )
                    self.server.completed = True
                    self.server.result = result
                    self.send_json(200, {"connected": True, **result})
                    return
                self.send_json(404, {"error": "Not found."})
            except (ValueError, StorageError) as error:
                self.send_json(400, {"error": str(error)})
            except Exception:
                self.send_json(400, {"error": "Credential import failed. Check the OS secret store, OAuth client details, and network, then retry."})
            finally:
                self.server.setup_lock.release()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    server.timeout = 0.5
    server.completed = False
    server.result = {}
    server.pending_oauth = None
    server.setup_lock = threading.Lock()
    server.deadline = time.monotonic() + 900
    server.setup_url = f"http://127.0.0.1:{server.server_port}/#session={session}"
    return server


def _serve_to_completion(server) -> dict:
    while not server.completed and time.monotonic() < server.deadline:
        server.handle_request()
    if not server.completed:
        raise ValueError("Setup expired without a saved profile. Run setup again.")
    if "error" in server.result:
        raise ValueError(server.result["error"])
    return {"connected": True, **server.result}


def run_setup() -> dict:
    with setup_server() as server:
        print("Local Google Play Console setup form: " + server.setup_url, flush=True)
        webbrowser.open(server.setup_url)
        return _serve_to_completion(server)


def start_background_setup() -> dict:
    server = setup_server()

    def serve_until_done():
        try:
            while not server.completed and time.monotonic() < server.deadline:
                server.handle_request()
        finally:
            server.server_close()

    threading.Thread(target=serve_until_done, name="google-play-console-setup", daemon=True).start()
    opened = webbrowser.open(server.setup_url)
    return {
        "started": True,
        "url": server.setup_url,
        "expiresInSeconds": 900,
        "storage": "OS secret store only",
        "browserOpened": bool(opened),
    }


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] != "setup":
        print("Usage: local_setup.py setup", file=sys.stderr)
        return 2
    try:
        print(json.dumps(run_setup(), ensure_ascii=False))
        return 0
    except (StorageError, ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
