"""Temporary loopback setup form; secrets never appear in URLs or responses."""

import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
import time
import webbrowser


def setup_server(defaults, verify_and_save):
    token = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(24)
    public_defaults = {key: defaults.get(key, "") or "" for key in ("url", "db", "username")}
    if not public_defaults["db"].strip():
        raise ValueError("Database is missing for this alternate instance. Supply --db before setup-web.")
    encoded = json.dumps(public_defaults).replace("<", "\\u003c")
    template = (Path(__file__).parents[1] / "assets/setup.html").read_text(encoding="utf-8")
    html = template.replace("__NONCE__", nonce).replace(
        "/*__CONNECTION__*/", f"Object.assign(defaults, {encoded});",
    ).encode()
    assets = Path(__file__).parents[1] / "assets"
    logos = {
        "/jala-logo.jpg": ((assets / "jala-logo.jpg").read_bytes(), "image/jpeg"),
        "/odoo-logo-dark.svg": ((assets / "odoo-logo-dark.svg").read_bytes(), "image/svg+xml"),
    }
    save_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(5)
            super().setup()

        def log_message(self, format, *args):
            pass

        def reply(self, status, value, content_type="application/json"):
            body = value if isinstance(value, bytes) else json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            try:
                self.wfile.write(body)
            except OSError:
                pass  # A closed browser must not log request details.

        def active(self):
            return not self.server.completed and time.monotonic() < self.server.deadline

        def allowed_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.allowed_host() or (self.path != "/" and self.path not in logos):
                self.reply(404, {"error": "Not found."})
            elif not self.active():
                self.reply(410, {"error": "Setup session has ended. Run setup-web again."})
            elif self.path in logos:
                logo, content_type = logos[self.path]
                self.reply(200, logo, content_type)
            else:
                self.reply(200, html, "text/html; charset=utf-8")

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            supplied = self.headers.get("X-Setup-Token", "")
            if (not self.allowed_host() or self.path != "/api/setup"
                    or self.headers.get("Origin") != origin
                    or not hmac.compare_digest(supplied.encode(), token.encode())):
                self.reply(403, {"error": "Invalid setup session. Run setup-web again and use the new link."})
                return
            if self.headers.get("Content-Type") != "application/json":
                self.reply(415, {"error": "Expected JSON."})
                return
            if not save_lock.acquire(blocking=False):
                self.reply(409, {"error": "A connection check is already in progress."})
                return
            try:
                if not self.active():
                    self.reply(410, {"error": "Setup session has ended. Run setup-web again."})
                    return
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    raise ValueError("Invalid request size")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict) or set(payload) != {"username", "secret"}:
                    raise ValueError("Invalid fields")
                if any(not isinstance(value, str) or not value or len(value) > 4096 for value in payload.values()):
                    raise ValueError("Invalid fields")
                connection = {
                    "url": public_defaults["url"], "db": public_defaults["db"].strip(),
                    "username": payload["username"].strip(), "secret": payload["secret"],
                }
                # URL and database come from the launched command, never the form.
                storage = verify_and_save(connection)
                self.server.storage = storage
                self.reply(200, {"ok": True, "storage": storage})
                self.server.completed = True
            except (ValueError, OSError, TimeoutError):
                self.reply(400, {"error": "Could not verify and save the connection. Check your email, API key or password, network connection, and local storage access."})
            except Exception:
                # RPC faults and backend exceptions can contain credentials.
                self.reply(400, {"error": "Odoo could not verify the connection. Check your details and try again."})
            finally:
                save_lock.release()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.timeout = 0.5
    server.daemon_threads = True
    server.completed = False
    server.storage = None
    server.save_lock = save_lock
    server.deadline = time.monotonic() + 900
    server.setup_url = f"http://127.0.0.1:{server.server_port}/#token={token}"
    return server


def setup_web(defaults, verify_and_save, open_browser=True):
    with setup_server(defaults, verify_and_save) as server:
        print("Open this local Odoo connection form: " + server.setup_url, flush=True)
        print("Session closes after saving or after 15 minutes. Ctrl+C cancels.", flush=True)
        if open_browser:
            webbrowser.open(server.setup_url)
        while not server.completed and time.monotonic() < server.deadline:
            server.handle_request()
        # New submissions expire, but an accepted verification must finish before
        # we report its outcome; native-store prompts can outlast the deadline.
        with server.save_lock:
            if not server.completed:
                raise ValueError("Setup session expired without a confirmed connection. Run setup-web again.")
            return {"connected": True, "storage": server.storage}
