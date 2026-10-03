#!/usr/bin/env python3
"""Local credential setup and authenticated requests to the JALA gateway."""
import argparse
import getpass
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
import secrets
import subprocess
import tempfile
import re
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import venv
import webbrowser

GATEWAY = "https://9router.jala.tech"
KEYRING_SERVICE = "tech.jala.9router"
KEYRING_ACCOUNT = "api-key"


def runtime_python():
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "9router-jala"
        return base / "runtime" / "Scripts" / "python.exe"
    return Path.home() / ".config" / "9router-jala" / "runtime" / "bin" / "python"


def install_runtime():
    python = runtime_python()
    directory = python.parents[1]
    venv.EnvBuilder(with_pip=True).create(directory)
    subprocess.run([str(python), "-m", "pip", "install", "-r", str(Path(__file__).parents[1] / "requirements.txt")], check=True)
    print("Credential helper dependencies installed in a private Python environment.")


def credential_store():
    """Choose native encrypted storage explicitly; never select fallback plugins."""
    try:
        if sys.platform == "darwin":
            from keyring.backends.macOS import Keyring
            return Keyring()
        if sys.platform == "win32":
            from keyring.backends.Windows import WinVaultKeyring
            store = WinVaultKeyring()
            store.persist = "local machine"
            _ = store.priority  # Ensure the native Windows bindings are available.
            return store
    except ImportError:
        raise ValueError("Run gateway.py install-runtime before setup.") from None
    except Exception:
        raise ValueError("Native credential storage is unavailable in this Python environment.") from None
    raise ValueError("Saved keys require macOS Keychain or Windows Credential Manager. On other systems, supply NINEROUTER_KEY from a managed secret store.")


def store_operation(store, operation, *args):
    try:
        return getattr(store, operation)(KEYRING_SERVICE, KEYRING_ACCOUNT, *args)
    except Exception:
        # Native backend exceptions can include sensitive data. Never display them.
        raise ValueError("Credential store operation failed. Unlock or allow access to your OS credential store and try again.") from None


def credential_path():
    return Path.home() / ".config" / "9router-jala" / "api-key"


def validate_key(key):
    if not isinstance(key, str) or not key or not key.isascii() or any(char.isspace() or ord(char) < 32 for char in key):
        raise ValueError("API key must be nonempty and contain no whitespace.")
    return key


def read_plaintext_key():
    path = credential_path()
    if path.is_symlink() or not path.is_file() or (os.name == "posix" and path.stat().st_mode & 0o077):
        raise ValueError("Plaintext key must be a regular private file (chmod 600 on macOS/Linux).")
    return validate_key(path.read_text().strip())


def save_plaintext_key(key):
    path = credential_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise ValueError("Credential directory cannot be a symlink.")
    if os.name == "posix":
        path.parent.chmod(0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        if os.name == "nt":
            identity = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"], capture_output=True, check=True).stdout
            sid = re.search(rb'S-1-[0-9-]+', identity)
            if not sid:
                raise ValueError("Could not identify the Windows user for private file permissions.")
            subprocess.run(["icacls", temporary, "/inheritance:r", "/grant:r", "*" + sid.group().decode("ascii") + ":F"], capture_output=True, check=True)
        with os.fdopen(fd, "w") as handle:
            fd = None
            handle.write(key + "\n")
        os.replace(temporary, path)
    except subprocess.CalledProcessError:
        raise ValueError("Could not set private Windows file permissions; key was not saved to plaintext.") from None
    finally:
        if fd is not None:
            os.close(fd)
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_key():
    key = os.environ.get("NINEROUTER_KEY")
    if key:
        return validate_key(key)
    # A fallback file can contain a newer key than an inaccessible native store.
    if credential_path().exists():
        return read_plaintext_key()
    key = store_operation(credential_store(), "get_password")
    if key:
        return validate_key(key)
    raise ValueError("API key missing. Run gateway.py setup-web.")


def save_key(key, allow_fallback=True):
    key = validate_key(key)
    try:
        store = credential_store()
        store_operation(store, "set_password", key)
        saved = store_operation(store, "get_password")
        if not isinstance(saved, str) or not saved.isascii() or not hmac.compare_digest(saved, key):
            raise ValueError("Could not confirm credential storage. Legacy key was not removed.")
    except ValueError:
        if not allow_fallback:
            raise
        save_plaintext_key(key)
        return
    # Remove an obsolete plaintext copy only after a verified native-store write.
    credential_path().unlink(missing_ok=True)


def migrate_key():
    path = credential_path()
    if not path.exists():
        raise ValueError("No legacy plaintext key to migrate.")
    if path.is_symlink() or not path.is_file() or (os.name == "posix" and path.stat().st_mode & 0o077):
        raise ValueError("Legacy key must be a regular private file (chmod 600 on macOS/Linux).")
    existing = store_operation(credential_store(), "get_password")
    if existing:
        raise ValueError("A key is already saved in the OS store. Use setup-web to replace it and remove the legacy file.")
    save_key(read_plaintext_key(), allow_fallback=False)
    print("Legacy key moved to the OS credential store; plaintext file removed.")


def forget_key():
    try:
        store = credential_store()
        if store_operation(store, "get_password") is not None:
            store_operation(store, "delete_password")
    except ValueError:
        raise ValueError("Could not remove the native credential. Restore access to the OS store and run forget again.") from None
    finally:
        credential_path().unlink(missing_ok=True)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward a user's Bearer key to another URL.
        return None


def send(path, key, body=None, audio=None):
    parsed = urllib.parse.urlsplit(path)
    if (parsed.scheme or parsed.netloc or parsed.fragment
            or not parsed.path.startswith("/v1/")
            or "\\" in path or any(p in (".", "..") for p in parsed.path.split("/"))):
        raise ValueError("Request path must be a gateway-relative /v1/ endpoint.")
    headers = {"Authorization": "Bearer " + validate_key(key)}
    data = None
    if audio is not None:
        if parsed.path != "/v1/audio/transcriptions" or not body or not body.get("model"):
            raise ValueError("Audio upload requires /v1/audio/transcriptions and a JSON body with model.")
        boundary = uuid.uuid4().hex
        chunks = []
        for field, value in body.items():
            if field not in {"model", "language", "prompt", "response_format", "temperature"}:
                raise ValueError("Unsupported transcription field.")
            chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n{value}\r\n'.encode())
        mime = mimetypes.guess_type(audio.name)[0] or "application/octet-stream"
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio{audio.suffix.lower()}"\r\nContent-Type: {mime}\r\n\r\n'.encode())
        chunks.extend([audio.read_bytes(), f'\r\n--{boundary}--\r\n'.encode()])
        data = b"".join(chunks)
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(GATEWAY + path, data=data, headers=headers)
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=120) as response:
            return response.read(), response.headers.get_content_type()
    except urllib.error.HTTPError as error:
        # Do not echo upstream error bodies, which may contain credentials.
        if error.code == 401:
            raise ValueError("Gateway rejected the API key (401). Run setup to replace it.") from None
        raise ValueError(f"Gateway returned HTTP {error.code}; request was not retried.") from None
    except (urllib.error.URLError, TimeoutError):
        raise ValueError("Gateway connection failed or timed out; request was not retried.") from None


def prepare_skill_request(skill, body, model=None, finance=False):
    config = json.loads((Path(__file__).parents[1] / "models.json").read_text())
    item = config["skills"].get(skill)
    if not item or not item["default_model"]:
        raise ValueError("This skill has no configured model for the configured JALA connections.")
    if not isinstance(body, dict):
        raise ValueError("Request body must be a JSON object.")
    if finance and skill != "9router-chat":
        raise ValueError("The finance combo is available for chat only.")
    if finance and (model or body.get("model")):
        raise ValueError("Choose --finance or an explicit model, not both.")
    if model and body.get("model") and model != body["model"]:
        raise ValueError("The --model option conflicts with the request body model.")
    selected = "9router-jala-finance" if finance else (model or body.get("model") or item["default_model"])
    if selected not in item["models"]:
        raise ValueError("Model is not in the configured allowed list for this skill.")
    prepared = {**body, "model": selected}
    if skill == "9router-chat":
        prepared.setdefault("stream", False)
    return item["catalog"], item["endpoint"], prepared


def run_skill(skill, body, key, model=None, finance=False, audio=None):
    catalog, endpoint, prepared = prepare_skill_request(skill, body, model, finance)
    data, content_type = send(catalog, key)
    result = json.loads(data)
    if content_type != "application/json" or not isinstance(result, dict) or not isinstance(result.get("data"), list):
        raise ValueError("Gateway returned an invalid model catalog; generation was not submitted.")
    ids = {item.get("id") for item in result["data"] if isinstance(item, dict)}
    if prepared["model"] not in ids:
        raise ValueError("Selected model is no longer listed by the gateway; generation was not submitted.")
    if skill == "9router-stt" and audio is None:
        raise ValueError("Transcription requires --audio-file.")
    if skill == "9router-tts":
        voice = prepared.pop("voice", "alloy")
        if not isinstance(voice, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", voice):
            raise ValueError("Voice must be a name such as alloy.")
        prepared["model"] += "/" + voice
    elif skill in {"9router-web-search", "9router-web-fetch"}:
        prepared["model"] = "exa"
    return send(endpoint, key, prepared, audio)


def setup():
    if not sys.stdin.isatty():
        raise ValueError("Run setup in your own interactive terminal; do not paste the key into chat.")
    key = validate_key(getpass.getpass("JALA 9Router API key (hidden): ").strip())
    verify_and_save(key)
    print("API key verified and saved locally. Ready to use JALA 9Router.")


def verify_and_save(key):
    key = validate_key(key)
    data, content_type = send("/v1/models", key)
    result = json.loads(data)
    if content_type != "application/json" or not isinstance(result, dict) or not isinstance(result.get("data"), list):
        raise ValueError("Gateway did not return a model list; key was not saved.")
    save_key(key)


def setup_server():
    token = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(24)
    html = (Path(__file__).parents[1] / "assets" / "setup.html").read_text().replace("__NONCE__", nonce).encode()

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(5)
            super().setup()

        def log_message(self, format, *args):
            pass

        def reply(self, status, body, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def allowed_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.allowed_host() or self.path != "/":
                self.reply(404, b'{"error":"Not found."}')
                return
            self.reply(200, html, "text/html; charset=utf-8")

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            supplied = self.headers.get("X-Setup-Token", "")
            if (not self.allowed_host() or self.path != "/api/setup"
                    or self.headers.get("Origin") != origin
                    or not hmac.compare_digest(supplied.encode(), token.encode())):
                self.reply(403, b'{"error":"Invalid setup session. Launch setup-web again."}')
                return
            if self.headers.get("Content-Type") != "application/json":
                self.reply(415, b'{"error":"Expected JSON."}')
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192:
                    raise ValueError("Invalid request size.")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict) or not isinstance(payload.get("key"), str):
                    raise ValueError("Enter a valid API key.")
                verify_and_save(payload["key"].strip())
            except (ValueError, OSError):
                self.reply(400, b'{"error":"Could not verify and save the key. Check your API key, gateway connection, and local file permissions."}')
                return
            self.reply(200, b'{"ok":true}')
            self.server.completed = True

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.timeout = 1
    server.completed = False
    server.setup_url = f"http://127.0.0.1:{server.server_port}/#token={token}"
    return server


def setup_web(open_browser=True):
    with setup_server() as server:
        print("Open this local API-key form: " + server.setup_url, flush=True)
        print("Session closes after saving or after 15 minutes. Ctrl+C cancels.", flush=True)
        if open_browser:
            webbrowser.open(server.setup_url)
        deadline = time.monotonic() + 900
        while not server.completed and time.monotonic() < deadline:
            server.handle_request()
        print("API key verified and saved." if server.completed else "Setup session expired.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("setup", help="Enter, verify, and save an API key in a hidden prompt")
    web = commands.add_parser("setup-web", help="Open a local HTML form to verify and save your API key")
    web.add_argument("--no-open", action="store_true", help="Print the local URL without opening a browser")
    commands.add_parser("status", help="Report whether a key is configured without displaying it")
    commands.add_parser("forget", help="Remove the locally saved key (does not revoke it)")
    commands.add_parser("migrate", help="Move a legacy plaintext key to the OS credential store")
    commands.add_parser("install-runtime", help="Install credential helper dependencies in a private Python environment")
    request = commands.add_parser("request", help="Make an authenticated GET or JSON POST")
    request.add_argument("path", help="Relative endpoint, for example /v1/models")
    request.add_argument("--body", type=Path, help="JSON request file; makes this a POST")
    request.add_argument("--output", type=Path, help="Save the response to a new file")
    request.add_argument("--audio-file", type=Path, help="Transcription audio; --body supplies model and options")
    run = commands.add_parser("run", help="Execute a skill with its configured model and endpoint")
    run.add_argument("skill", choices=["9router-chat", "9router-image", "9router-tts", "9router-stt", "9router-embeddings", "9router-web-search", "9router-web-fetch"])
    run.add_argument("--body", type=Path, required=True, help="Task input as JSON; model is optional")
    run.add_argument("--model", help="Override the default with an allowed model")
    run.add_argument("--finance", action="store_true", help="Use 9router-jala-finance for chat")
    run.add_argument("--output", type=Path, help="Save the response to a new file")
    run.add_argument("--audio-file", type=Path, help="Audio input for transcription")
    args = parser.parse_args()
    if args.command != "install-runtime" and sys.platform in ("darwin", "win32"):
        # Preserve the simple setup command across plugin upgrades and host interpreters.
        import importlib.util
        if importlib.util.find_spec("keyring") is None:
            python = runtime_python()
            if python.is_file() and os.path.abspath(python) != os.path.abspath(sys.executable):
                os.execv(str(python), [str(python), str(Path(__file__).absolute()), *sys.argv[1:]])
    try:
        if args.command == "install-runtime":
            install_runtime()
        elif args.command == "setup":
            setup()
        elif args.command == "setup-web":
            setup_web(not args.no_open)
        elif args.command == "status":
            load_key()
            print("API key configured. Gateway: " + GATEWAY)
        elif args.command == "forget":
            forget_key()
            print("Saved key removed. Any NINEROUTER_KEY environment override remains active.")
        elif args.command == "migrate":
            migrate_key()
        else:
            body = json.loads(args.body.read_text()) if args.body else None
            if args.body and not isinstance(body, dict):
                raise ValueError("Request body must be a JSON object.")
            if not args.output and ((args.command == "run" and args.skill == "9router-tts")
                    or (args.command == "request" and urllib.parse.urlsplit(args.path).path == "/v1/audio/speech"
                        and urllib.parse.parse_qs(urllib.parse.urlsplit(args.path).query).get("response_format") != ["json"])):
                raise ValueError("Speech audio requires --output.")
            if args.command == "run" and args.skill == "9router-stt" and not args.audio_file:
                raise ValueError("Transcription requires --audio-file.")
            # Reserve the output before any paid request; fail early on permissions,
            # missing directories, or an existing file. Remove it on request failure.
            output = args.output.open("xb") if args.output else None
            try:
                if args.command == "run":
                    data, content_type = run_skill(args.skill, body, load_key(), args.model, args.finance, args.audio_file)
                else:
                    data, content_type = send(args.path, load_key(), body, args.audio_file)
                if output:
                    output.write(data)
                    output.close()
                    print("Response saved: " + str(args.output))
                elif content_type == "application/json" or content_type.startswith("text/"):
                    sys.stdout.write(data.decode("utf-8") + "\n")
                else:
                    raise ValueError("Binary response requires --output.")
            except BaseException:
                if output:
                    output.close()
                    args.output.unlink(missing_ok=True)
                raise
    except subprocess.CalledProcessError:
        print("Dependency installation failed; no credentials were saved.", file=sys.stderr)
        return 1
    except (ValueError, OSError) as error:
        # Avoid printing OS exception filenames or JSON document contents.
        message = str(error) if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError) else "Local file or JSON operation failed."
        print(message, file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("Cancelled.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
