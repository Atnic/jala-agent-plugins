"""Verify setup and persistence using fake credentials, temp files, and loopback."""

import contextlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request
from urllib.parse import unquote, urljoin, urlsplit
from xmlrpc.server import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer

from helpers import isolated_environment


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/odoo-jala-xmlrpc/scripts"
sys.path.insert(0, str(SCRIPTS))
import connection_store as store
import odoo_rpc as rpc
import setup_web as web

NATIVE_FACTORY = store.credential_store


class LocalPreviewTests(unittest.TestCase):
    def test_images_resolve_when_html_is_opened_directly(self):
        class Images(HTMLParser):
            def __init__(self):
                super().__init__()
                self.sources = []

            def handle_starttag(self, tag, attrs):
                if tag == "img":
                    self.sources.append(dict(attrs)["src"])

        page = SCRIPTS.parent / "assets/setup.html"
        images = Images()
        images.feed(page.read_text(encoding="utf-8"))
        self.assertTrue(images.sources)
        for source in images.sources:
            with self.subTest(source=source):
                resolved = Path(unquote(urlsplit(urljoin(page.as_uri(), source)).path))
                self.assertTrue(resolved.is_file(), f"Broken local preview image: {resolved}")


class OdooHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ("/xmlrpc/2/common",)


class MemoryStore:
    def __init__(self):
        self.value = None

    def get_password(self, service, account):
        return self.value

    def set_password(self, service, account, value):
        self.value = value

    def delete_password(self, service, account):
        self.value = None


class SetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.odoo = SimpleXMLRPCServer(("127.0.0.1", 0), OdooHandler, logRequests=False)
        cls.odoo.register_function(lambda db, user, key, context: (
            42 if (db, user, key) == ("test-db", "test-user", "test-key") else False
        ), "authenticate")
        cls.odoo_thread = threading.Thread(target=cls.odoo.serve_forever, daemon=True)
        cls.odoo_thread.start()
        cls.url = f"http://127.0.0.1:{cls.odoo.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.odoo.shutdown()
        cls.odoo.server_close()
        cls.odoo_thread.join()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        clean = isolated_environment(self.directory.name)
        self.environment = patch.dict(os.environ, clean, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.native = MemoryStore()
        self.backend = patch.object(store, "credential_store", return_value=self.native)
        self.backend.start()
        self.addCleanup(self.backend.stop)
        self.connection = {"url": self.url, "db": "test-db", "username": "test-user", "secret": "test-key"}

    @contextlib.contextmanager
    def server(self, verify=None, defaults=None):
        with web.setup_server(defaults or self.connection, verify or rpc.verify_and_save) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                yield server
            finally:
                server.shutdown()
                thread.join()

    def post(self, server, payload=None, token=None, origin=None, host=None, content_type="application/json"):
        root = f"http://127.0.0.1:{server.server_port}"
        request = urllib.request.Request(
            root + "/api/setup", method="POST",
            data=json.dumps(payload if payload is not None else {key: self.connection[key] for key in ("username", "secret")}).encode(),
            headers={"Content-Type": content_type, "X-Setup-Token": token if token is not None else server.setup_url.split("token=")[1],
                     "Origin": origin or root, "Host": host or f"127.0.0.1:{server.server_port}"},
        )
        return urllib.request.urlopen(request, timeout=3)

    def test_form_never_contains_saved_secret_or_session_token(self):
        defaults = dict(self.connection, db='</script><script>alert(1)</script>')
        with self.server(defaults=defaults) as server:
            with urllib.request.urlopen(server.setup_url.split("#")[0]) as response:
                html = response.read().decode()
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
            self.assertNotIn("test-key", html)
            self.assertNotIn(server.setup_url.split("token=")[1], html)
            self.assertNotIn(defaults["db"], html)
            self.assertIn("\\u003c/script>", html)
            self.assertIn('type="password"', html)

    def test_relative_logos_are_also_served_by_setup_server(self):
        class Images(HTMLParser):
            def __init__(self):
                super().__init__()
                self.sources = []

            def handle_starttag(self, tag, attrs):
                if tag == "img":
                    self.sources.append(dict(attrs)["src"])

        with self.server() as server:
            root = server.setup_url.split("#")[0]
            with urllib.request.urlopen(root) as response:
                images = Images()
                images.feed(response.read().decode())
            self.assertEqual(len(images.sources), 2)
            for source in images.sources:
                with self.subTest(source=source):
                    with urllib.request.urlopen(urljoin(root, source)) as response:
                        self.assertTrue(response.headers["Content-Type"].startswith("image/"))
                        expected = (SCRIPTS.parent / "assets" / source).read_bytes()
                        self.assertEqual(response.read(), expected)

    def test_verified_setup_saves_native_connection_and_reuses_it_without_env(self):
        with self.server() as server:
            with self.post(server) as response:
                body = response.read()
                self.assertEqual(json.loads(body), {"ok": True, "storage": "native"})
                self.assertNotIn(b"test-key", body)
            for _ in range(50):
                if server.completed:
                    break
                time.sleep(.001)
            self.assertTrue(server.completed)
        self.assertEqual(store.load_connection(), (self.connection, "native"))
        self.assertEqual(rpc.run(rpc.parser().parse_args(["authenticate"])), {"uid": 42})
        status = rpc.run(rpc.parser().parse_args(["status"]))
        self.assertTrue(status["ready"])
        self.assertEqual(status["secret_source"], "native")
        self.assertNotIn("test-key", json.dumps(status))

    def test_setup_command_stops_after_success_and_no_open_does_not_launch_browser(self):
        original = web.setup_server
        ready = threading.Event()
        created, result, failures = [], [], []

        def create(*args):
            server = original(*args)
            created.append(server)
            ready.set()
            return server

        def run():
            try:
                result.append(rpc.run(rpc.parser().parse_args([
                    "--url", self.url, "--db", "test-db", "setup-web", "--no-open",
                ])))
            except Exception as exc:
                failures.append(type(exc).__name__)

        output = io.StringIO()
        with patch.object(web, "setup_server", side_effect=create), patch.object(web.webbrowser, "open") as launch:
            with contextlib.redirect_stdout(output):
                thread = threading.Thread(target=run, daemon=True)
                thread.start()
                self.assertTrue(ready.wait(2))
                with self.post(created[0]) as response:
                    response.read()
                thread.join(2)
            self.assertFalse(thread.is_alive())
            launch.assert_not_called()
        self.assertEqual(failures, [])
        self.assertEqual(result, [{"connected": True, "storage": "native"}])
        self.assertNotIn("test-key", output.getvalue())

    def test_failed_verification_preserves_existing_connection(self):
        store.save_connection(self.connection)
        with self.server() as server:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                self.post(server, {"username": "test-user", "secret": "wrong-key"})
            self.assertEqual(caught.exception.code, 400)
            self.assertNotIn(b"wrong-key", caught.exception.read())
            self.assertFalse(server.completed)
        self.assertEqual(store.load_connection()[0], self.connection)

    def test_expiry_waits_for_accepted_verification_and_reports_its_result(self):
        original = web.setup_server
        ready, started, release, ended = (threading.Event() for _ in range(4))
        created, results, errors = [], [], []

        def create(*args):
            server = original(*args)
            server.timeout = 0.01
            created.append(server)
            ready.set()
            return server

        def verify(connection):
            started.set()
            if not release.wait(5):
                raise ValueError("test verification timed out")
            return store.save_connection(connection)

        def setup():
            try:
                results.append(web.setup_web(self.connection, verify, open_browser=False))
            except Exception as exc:
                errors.append(type(exc).__name__)
            finally:
                ended.set()

        def submit():
            try:
                with self.post(created[0]) as response:
                    response.read()
            except Exception as exc:
                errors.append(type(exc).__name__)

        with patch.object(web, "setup_server", side_effect=create), contextlib.redirect_stdout(io.StringIO()):
            worker = threading.Thread(target=setup, daemon=True)
            worker.start()
            self.assertTrue(ready.wait(2))
            request = threading.Thread(target=submit, daemon=True)
            request.start()
            try:
                self.assertTrue(started.wait(2))
                created[0].deadline = time.monotonic() - 1
                self.assertFalse(ended.wait(0.5), "setup returned before accepted verification finished")
            finally:
                release.set()
                request.join(3)
                worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertFalse(request.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(results, [{"connected": True, "storage": "native"}])
        self.assertEqual(store.load_connection()[0], self.connection)

    def test_token_origin_host_and_content_type_are_enforced(self):
        verify = Mock()
        cases = [({"token": "wrong"}, 403), ({"origin": "https://example.com"}, 403),
                 ({"host": "evil.example"}, 403), ({"content_type": "text/plain"}, 415)]
        with self.server(verify) as server:
            for kwargs, code in cases:
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        self.post(server, **kwargs)
                    self.assertEqual(caught.exception.code, code)
        verify.assert_not_called()

    def test_replayed_and_expired_sessions_cannot_save(self):
        verify = Mock(return_value="native")
        with self.server(verify) as server:
            with self.post(server) as response:
                response.read()
            with self.assertRaises(urllib.error.HTTPError) as caught:
                self.post(server)
            self.assertEqual(caught.exception.code, 410)
        self.assertEqual(verify.call_count, 1)
        verify.reset_mock()
        with self.server(verify) as server:
            server.deadline = time.monotonic() - 1
            with self.assertRaises(urllib.error.HTTPError) as caught:
                self.post(server)
            self.assertEqual(caught.exception.code, 410)
        verify.assert_not_called()

    def test_payload_cannot_change_target_or_echo_backend_exception(self):
        verify = Mock(side_effect=RuntimeError("private test-key trace"))
        with self.server(verify) as server:
            for override in [{"url": "https://example.com"}, {"db": "other-db"}]:
                payload = {"username": "test-user", "secret": "test-key", **override}
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    self.post(server, payload)
                self.assertEqual(caught.exception.code, 400)
                verify.assert_not_called()
            with self.assertRaises(urllib.error.HTTPError) as caught:
                self.post(server)
            self.assertNotIn(b"test-key", caught.exception.read())
            self.assertFalse(server.completed)

    def test_jala_database_is_automatic_and_old_connection_secret_is_not_reused(self):
        store.save_connection(dict(self.connection, url=rpc.DEFAULT_URL, db="old-db"))
        status = rpc.run(rpc.parser().parse_args(["status"]))
        self.assertEqual(status["database"], "jala_production")
        self.assertFalse(status["secret_configured"])
        with patch.object(web, "setup_web", return_value={"connected": True}) as launch:
            rpc.run(rpc.parser().parse_args(["setup-web", "--no-open"]))
        self.assertEqual(launch.call_args.args[0]["db"], "jala_production")

    def test_alternate_instance_requires_explicit_or_saved_database(self):
        with self.assertRaises(rpc.InputError):
            rpc.run(rpc.parser().parse_args(["--url", self.url, "setup-web", "--no-open"]))

    def test_fallback_is_private_and_reused_by_another_process(self):
        with patch.object(store, "credential_store", side_effect=store.StorageError("unavailable")):
            self.assertEqual(rpc.verify_and_save(self.connection), "private-file")
        if os.name == "posix":
            self.assertEqual(store.connection_path().stat().st_mode & 0o777, 0o600)
            self.assertEqual(store.connection_path().parent.stat().st_mode & 0o777, 0o700)
        result = subprocess.run([sys.executable, str(SCRIPTS / "odoo_rpc.py"), "authenticate"],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"uid": 42})
        self.assertNotIn("test-key", result.stdout + result.stderr)

    def test_newer_fallback_wins_and_native_save_removes_it(self):
        store.save_connection(self.connection)
        newer = dict(self.connection, secret="newer-key")
        with patch.object(store, "credential_store", side_effect=store.StorageError("unavailable")):
            store.save_connection(newer)
        self.assertEqual(store.load_connection(), (newer, "private-file"))
        self.assertEqual(store.save_connection(newer), "native")
        self.assertFalse(store.connection_path().exists())
        self.assertEqual(store.load_connection(), (newer, "native"))

    def test_changed_identity_never_receives_saved_secret(self):
        store.save_connection(self.connection)
        for flag, value in [("--url", "https://example.com"), ("--db", "other-db"), ("--username", "other-user")]:
            with self.subTest(flag=flag):
                options = rpc.parser().parse_args([flag, value, "authenticate"])
                rpc.resolve_connection(options)
                self.assertIsNone(options.secret)
                with patch.object(rpc.sys.stdin, "isatty", return_value=False):
                    with self.assertRaises(rpc.InputError):
                        rpc.credentials(options)

    def test_alternate_server_does_not_inherit_saved_database_or_login(self):
        store.save_connection(self.connection)
        with patch.dict(os.environ, {"ODOO_API_KEY": "explicit-test-key"}):
            result = rpc.run(rpc.parser().parse_args(["--url", "https://alternate.example", "status"]))
            self.assertIsNone(result["database"])
            self.assertIsNone(result["username"])
            self.assertFalse(result["ready"])
            with patch.object(rpc, "proxy") as remote:
                with self.assertRaises(rpc.InputError):
                    rpc.run(rpc.parser().parse_args(["--url", "https://alternate.example", "authenticate"]))
                remote.assert_not_called()

    def test_environment_secret_takes_precedence(self):
        store.save_connection(self.connection)
        with patch.dict(os.environ, {"ODOO_API_KEY": "override-key", "ODOO_PASSWORD": "other-key"}):
            options = rpc.parser().parse_args(["authenticate"])
            rpc.resolve_connection(options)
            self.assertEqual(options.secret, "override-key")
            self.assertEqual(options.secret_source, "environment")

    def test_environment_connection_works_without_saved_storage(self):
        targets = [
            ([], rpc.DEFAULT_URL, rpc.DEFAULT_DB),
            (["--url", rpc.DEFAULT_URL], rpc.DEFAULT_URL, rpc.DEFAULT_DB),
            (["--db", "other-db"], rpc.DEFAULT_URL, "other-db"),
            (["--url", self.url, "--db", "test-db"], self.url, "test-db"),
        ]
        for secret_variable in ("ODOO_API_KEY", "ODOO_PASSWORD"):
            for flags, url, database in targets:
                with self.subTest(secret=secret_variable, flags=flags), patch.dict(
                    os.environ, {"ODOO_USERNAME": "test-user", secret_variable: "override-key"},
                ), patch.object(store, "load_connection", side_effect=store.StorageError("locked")) as load:
                    options = rpc.parser().parse_args([*flags, "status"])
                    result = rpc.run(options)
                    self.assertTrue(result["ready"])
                    self.assertEqual((result["url"], result["database"]), (url, database))
                    self.assertEqual(options.secret, "override-key")
                    self.assertEqual(result["secret_source"], "environment")
                    load.assert_not_called()

    def test_alternate_environment_target_still_requires_its_database(self):
        with patch.dict(os.environ, {"ODOO_USERNAME": "test-user", "ODOO_API_KEY": "override-key"}), patch.object(
            store, "load_connection", side_effect=store.StorageError("locked"),
        ):
            options = rpc.parser().parse_args(["--url", self.url, "authenticate"])
            with self.assertRaises(store.StorageError):
                rpc.resolve_connection(options)

    def test_file_permissions_and_symlinks_rejected(self):
        with patch.object(store, "credential_store", side_effect=store.StorageError("unavailable")):
            store.save_connection(self.connection)
        if os.name == "posix":
            store.connection_path().chmod(0o644)
            with self.assertRaises(store.StorageError):
                store.load_connection()
            store.connection_path().chmod(0o600)
        original = Path(self.directory.name) / "original.json"
        store.connection_path().rename(original)
        try:
            store.connection_path().symlink_to(original)
        except OSError:
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(store.StorageError):
            store.load_connection()
        with self.assertRaises(store.StorageError):
            store.save_private_file("{}")

    def test_forget_removes_both_copies_without_revoking_key(self):
        store.save_connection(self.connection)
        store.save_private_file(json.dumps(self.connection))
        self.assertTrue(store.forget_connection()["forgotten"])
        self.assertIsNone(self.native.value)
        self.assertFalse(store.connection_path().exists())

    def test_forget_does_not_claim_native_removal_if_locked(self):
        store.save_connection(self.connection)
        store.save_private_file(json.dumps(self.connection))
        with patch.object(store, "credential_store", side_effect=store.StorageError("locked")):
            with self.assertRaises(store.StorageError):
                store.forget_connection()
        self.assertFalse(store.connection_path().exists())
        self.assertIsNotNone(self.native.value)

    def test_native_backend_selection(self):
        modules = [
            ("darwin", "keyring.backends.macOS", "Keyring"),
            ("win32", "keyring.backends.Windows", "WinVaultKeyring"),
            ("linux", "keyring.backends.SecretService", "Keyring"),
        ]
        for platform, module_name, class_name in modules:
            with self.subTest(platform=platform):
                module = types.ModuleType(module_name)
                factory = Mock(return_value=Mock(priority=1))
                setattr(module, class_name, factory)
                with patch.dict(sys.modules, {module_name: module}), patch.object(store.sys, "platform", platform):
                    # Call the real function rather than the fixture's fake backend.
                    backend = NATIVE_FACTORY()
                factory.assert_called_once()
                if platform == "win32":
                    self.assertEqual(backend.persist, "local machine")


if __name__ == "__main__":
    unittest.main()
