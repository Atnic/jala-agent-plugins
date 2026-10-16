#!/usr/bin/env python3
"""Read-only JSON CLI for Odoo's XML-RPC API. Requires Python 3.9+ only."""

import argparse
import base64
import datetime
import getpass
import http.client
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace
from urllib.parse import urlsplit
import xmlrpc.client
from xml.parsers.expat import ExpatError

import connection_store


DEFAULT_URL = "https://odoo.jala.tech"
DEFAULT_DB = "jala_production"

READ_METHODS = frozenset({
    "search", "search_read", "search_count", "read", "fields_get",
    "name_get", "name_search", "read_group", "check_access_rights",
})


class SingleRequest:
    # Transport.request normally retries some disconnects. Keep calls single-shot
    # so the caller receives an ambiguous response without an automatic retry.
    def request(self, host, handler, request_body, verbose=False):
        return self.single_request(host, handler, request_body, verbose)

    def make_connection(self, host):
        connection = super().make_connection(host)
        connection.timeout = self.timeout
        return connection


class HTTPTransport(SingleRequest, xmlrpc.client.Transport):
    def __init__(self, timeout):
        super().__init__(use_builtin_types=True)
        self.timeout = timeout


class HTTPSTransport(SingleRequest, xmlrpc.client.SafeTransport):
    def __init__(self, timeout):
        super().__init__(use_builtin_types=True)
        self.timeout = timeout


class InputError(ValueError):
    pass


def base_url(value):
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise InputError("Invalid Odoo URL.") from None
    if (not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment
            or (port is not None and port < 1)):
        raise InputError("Use a base URL without credentials, query, or fragment.")
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "::1", "localhost"}
    ):
        raise InputError("HTTPS is required; HTTP is permitted only for loopback testing.")
    if parsed.path.rstrip("/").endswith(("/xmlrpc/2/common", "/xmlrpc/2/object")):
        raise InputError("Use the Odoo base URL, without an XML-RPC endpoint suffix.")
    return parsed.geturl().rstrip("/")


def proxy(url, endpoint, timeout):
    transport = HTTPSTransport(timeout) if url.startswith("https:") else HTTPTransport(timeout)
    return xmlrpc.client.ServerProxy(
        url + "/xmlrpc/2/" + endpoint, transport=transport, use_builtin_types=True,
    )


def reject_constant(value):
    raise InputError("JSON must contain finite numbers.")


def validate_numbers(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise InputError("JSON must contain finite numbers.")
    if isinstance(value, list):
        for item in value:
            validate_numbers(item)
    elif isinstance(value, dict):
        for item in value.values():
            validate_numbers(item)


def load_request(filename):
    try:
        if filename == "-":
            data = json.load(sys.stdin, parse_constant=reject_constant)
        else:
            with Path(filename).open(encoding="utf-8") as source:
                data = json.load(source, parse_constant=reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise InputError("Cannot read request: supply a UTF-8 JSON file or '-' for stdin.") from None
    if not isinstance(data, dict) or set(data) - {"args", "kwargs"}:
        raise InputError("Request must be an object containing only args and kwargs.")
    args, kwargs = data.get("args", []), data.get("kwargs", {})
    if not isinstance(args, list) or not isinstance(kwargs, dict):
        raise InputError("args must be an array and kwargs must be an object.")
    if "context" in kwargs and not isinstance(kwargs["context"], dict):
        raise InputError("kwargs.context must be an object.")
    validate_numbers(data)
    # Validate before authentication or dispatch (including null and integer
    # range limitations) so invalid input never reaches the server.
    try:
        xmlrpc.client.dumps((args, kwargs), allow_none=False)
    except (TypeError, OverflowError):
        raise InputError("Request is not XML-RPC compatible; use false for unset Odoo fields, not null.") from None
    return args, kwargs


def secret_from_environment():
    return os.environ.get("ODOO_API_KEY") or os.environ.get("ODOO_PASSWORD")


def resolve_connection(options, include_secret=True):
    secret = secret_from_environment()
    saved, storage = None, None
    target_url = base_url(options.url or DEFAULT_URL)
    target_has_database = options.db or target_url == DEFAULT_URL
    # An explicit login and environment secret form an independent connection.
    # JALA's default target needs no saved URL/database or credential-store read.
    if not (target_has_database and options.username and (secret or not include_secret)):
        saved, storage = connection_store.load_connection()
    saved = saved or {}
    options.url = base_url(options.url or saved.get("url") or DEFAULT_URL)
    same_url = options.url == saved.get("url")
    options.db = options.db or (DEFAULT_DB if options.url == DEFAULT_URL else saved.get("db") if same_url else None)
    options.username = options.username or (saved.get("username") if same_url else None)
    matches = all(saved.get(key) == getattr(options, key) for key in ("url", "db", "username"))
    # Never send a saved secret to a changed host, database, or login.
    options.secret = secret or (saved.get("secret") if matches and include_secret else None)
    options.secret_source = "environment" if secret else storage if matches else None


def credentials(options):
    if not options.db or not options.username:
        raise InputError("Run setup-web to save your Odoo connection, or set ODOO_DB and ODOO_USERNAME.")
    secret = options.secret
    if not secret and sys.stdin.isatty():
        secret = getpass.getpass("Odoo API key or password (not saved): ")
    if not secret:
        raise InputError("Run setup-web, or provide ODOO_API_KEY or ODOO_PASSWORD through the local environment; do not paste it into chat.")
    return secret


def configure_web(options):
    from setup_web import setup_web
    try:
        saved, _ = connection_store.load_connection()
    except connection_store.StorageError:
        saved = None  # Setup can replace an unreadable or inaccessible credential.
    saved = saved or {}
    url = base_url(options.url or saved.get("url") or DEFAULT_URL)
    same_url = url == saved.get("url")
    defaults = {
        "url": url, "db": options.db or (DEFAULT_DB if url == DEFAULT_URL else saved.get("db") if same_url else ""),
        "username": options.username or (saved.get("username") if same_url else ""),
    }
    if not defaults["db"]:
        raise InputError("Database is missing for this alternate instance. Supply --db before setup-web.")

    return setup_web(defaults, lambda connection: verify_and_save(connection, options.timeout),
                     open_browser=not options.no_open)


def verify_and_save(connection, timeout=30):
    connection_store.validate_connection(connection)
    configured = SimpleNamespace(**connection, timeout=timeout)
    configured.url = base_url(configured.url)
    connection = dict(connection, url=configured.url)
    authenticate(configured, connection["secret"])
    return connection_store.save_connection(connection)


def authenticate(options, secret):
    with proxy(options.url, "common", options.timeout) as common:
        uid = common.authenticate(options.db, options.username, secret, {})
    if type(uid) is not int or uid < 1:
        raise InputError("Authentication failed; check the database, login, and API key or password.")
    return uid


def json_default(value):
    if isinstance(value, bytes):
        return {"base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    raise TypeError("Unsupported response type")


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--url", default=os.environ.get("ODOO_URL"))
    cli.add_argument("--db", default=os.environ.get("ODOO_DB"))
    cli.add_argument("--username", default=os.environ.get("ODOO_USERNAME"))
    cli.add_argument("--timeout", type=float, default=30, help="Seconds per RPC (default: 30)")
    commands = cli.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Report configuration without connecting or showing secrets")
    commands.add_parser("version", help="Read server version without authenticating")
    commands.add_parser("authenticate", help="Check credentials and return the user ID")
    web = commands.add_parser("setup-web", help="Open a local form to verify and save your Odoo connection")
    web.add_argument("--no-open", action="store_true", help="Print the setup link without opening a browser")
    commands.add_parser("install-runtime", help="Install native credential-store dependencies in a private Python environment")
    commands.add_parser("forget", help="Remove the saved local connection without revoking the Odoo key")
    discover = commands.add_parser("discover", help="Discover installed addons, models, navigation, and requested schemas into a private local profile")
    discover.add_argument("--model", dest="models", action="append", help="Inspect this model's fields and permissions (repeatable)")
    discover.add_argument("--company-id", dest="company_ids", type=int, action="append", help="Discover in this allowed company context (repeatable)")
    discover.add_argument("--limit", type=int, default=2000, help="Maximum rows per metadata section (default: 2000)")
    discover.add_argument("--refresh", action="store_true", help="Refresh the base inventory instead of reusing a profile up to 24 hours old")
    execute = commands.add_parser("execute", help="Call an allowed read-only model method through execute_kw")
    execute.add_argument("model")
    execute.add_argument("method")
    execute.add_argument("--input", required=True, help="JSON {args: [], kwargs: {}} file; '-' for stdin")
    return cli


def run(options):
    if not math.isfinite(options.timeout) or options.timeout <= 0:
        raise InputError("Timeout must be a positive finite number.")
    if options.command == "install-runtime":
        return connection_store.install_runtime()
    if options.command == "forget":
        return connection_store.forget_connection()
    if options.command == "setup-web":
        return configure_web(options)
    if options.command == "execute":
        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_.]*", options.model):
            raise InputError("Invalid model name.")
        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*", options.method):
            raise InputError("Use a public model method name.")
        if options.method not in READ_METHODS:
            raise InputError("This client is read-only. Writes, workflow actions, and unclassified methods are disabled.")
        args, kwargs = load_request(options.input)
    if options.command == "version" and options.url:
        options.url = base_url(options.url)
    else:
        resolve_connection(options, include_secret=options.command != "version")
    if options.command == "status":
        return {
            "url": options.url, "database": options.db, "username": options.username,
            "secret_configured": bool(options.secret), "secret_source": options.secret_source,
            "ready": bool(options.db and options.username and options.secret),
        }
    if options.command == "version":
        with proxy(options.url, "common", options.timeout) as common:
            return common.version()
    secret = credentials(options)
    uid = authenticate(options, secret)
    if options.command == "authenticate":
        return {"uid": uid}
    if options.command == "discover":
        from discovery import discover
        try:
            return discover(options, uid, secret, proxy)
        except ValueError:
            raise InputError("Discovery could not establish the requested scope or received unexpected metadata. Check model names, company IDs, and discovery limits.") from None
    with proxy(options.url, "object", options.timeout) as models:
        return models.execute_kw(
            options.db, uid, secret, options.model, options.method, args, kwargs,
        )


def main(argv=None):
    if argv is None and "install-runtime" not in sys.argv[1:] and importlib.util.find_spec("keyring") is None:
        python = connection_store.runtime_python()
        if python.is_file() and os.path.abspath(python) != os.path.abspath(sys.executable):
            os.execv(str(python), [str(python), str(Path(__file__).absolute()), *sys.argv[1:]])
    options = parser().parse_args(argv)
    try:
        result = run(options)
        print(json.dumps(result, ensure_ascii=True, default=json_default, allow_nan=False))
        return 0
    except (InputError, connection_store.StorageError) as exc:
        error = {"error": "input", "message": str(exc)}
    except subprocess.CalledProcessError:
        error = {"error": "runtime", "message": "Could not install the credential-store dependencies. Check the Python environment and package index connection."}
    except xmlrpc.client.Fault as exc:
        # Server tracebacks may include credentials or record values. Classify
        # known Odoo errors without printing the remote message or request.
        kind = next((name for name in (
            "AccessDenied", "AccessError", "ValidationError", "UserError", "MissingError",
        ) if name in exc.faultString), "RPCFault")
        error = {"error": kind, "message": "Odoo rejected the RPC call. Check access, model fields, and business rules; verify record state before retrying."}
    except xmlrpc.client.ProtocolError as exc:
        error = {"error": "http", "status": exc.errcode, "message": "RPC HTTP failure; verify record state before retrying."}
    except (OSError, http.client.HTTPException, xmlrpc.client.ResponseError, ExpatError):
        error = {"error": "transport", "message": "RPC connection or response failed. The result may be unknown; verify record state before retrying."}
    except (ValueError, TypeError, OverflowError):
        error = {"error": "encoding", "message": "RPC request or response could not be encoded. Verify record state before retrying."}
    except (KeyboardInterrupt, EOFError):
        error = {"error": "interrupted", "message": "RPC interrupted; verify record state before retrying."}
    print(json.dumps(error), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
