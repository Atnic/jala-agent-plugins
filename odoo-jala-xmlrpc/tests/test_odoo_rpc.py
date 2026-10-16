"""Exercise the CLI over loopback XML-RPC; never contact JALA."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from xmlrpc.server import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer
import xmlrpc.client

from helpers import isolated_environment


CLIENT = Path(__file__).resolve().parents[1] / "skills/odoo-jala-xmlrpc/scripts/odoo_rpc.py"
SECRET = "test-only-secret-do-not-echo"


class Handler(SimpleXMLRPCRequestHandler):
    rpc_paths = ("/xmlrpc/2/common", "/xmlrpc/2/object")

    def do_POST(self):
        if self.path == "/xmlrpc/2/object" and self.server.lose_response:
            body = self.rfile.read(int(self.headers["Content-Length"]))
            args, method = xmlrpc.client.loads(body)
            self.server.funcs[method](*args)
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        super().do_POST()


class ClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = SimpleXMLRPCServer(("127.0.0.1", 0), Handler, logRequests=False, allow_none=True)
        cls.server.register_function(lambda: {"server_version": "16.0"}, "version")
        cls.server.register_function(cls.authenticate, "authenticate")
        cls.server.register_function(cls.execute, "execute_kw")
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:" + str(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    @classmethod
    def authenticate(cls, db, login, secret, context):
        cls.calls.append(("authenticate", db, login, context))
        return 42 if (db, login, secret) == ("test-db", "test-user", SECRET) else False

    @classmethod
    def execute(cls, db, uid, secret, model, method, args, kwargs):
        if (db, uid, secret) != ("test-db", 42, SECRET):
            raise ValueError("Incorrect authenticated arguments")
        cls.calls.append((model, method, args, kwargs))
        if model == "test.fault":
            raise xmlrpc.client.Fault(1, "odoo.exceptions.AccessError: " + SECRET)
        if method == "create":
            cls.records[123] = dict(args[0], id=123)
            return 123
        if method == "write":
            for record_id in args[0]:
                cls.records[record_id].update(args[1])
            return True
        if method == "unlink":
            for record_id in args[0]:
                del cls.records[record_id]
            return True
        if method == "read":
            return [cls.records[record_id] for record_id in args[0] if record_id in cls.records]
        if method == "fields_get":
            return {"name": {"type": "char", "required": True}}
        if method == "search_read":
            return [{"id": 123, "name": "Example"}]
        if method == "binary_data":
            return xmlrpc.client.Binary(b"test")
        return True

    def setUp(self):
        self.calls = type(self).calls = []
        self.records = type(self).records = {123: {"id": 123, "name": "Before"}}
        self.server.lose_response = False
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.env = isolated_environment(directory.name)
        self.env.update(ODOO_URL=self.url, ODOO_DB="test-db", ODOO_USERNAME="test-user", ODOO_API_KEY=SECRET)

    def cli(self, *args, payload=None, env=None):
        result = subprocess.run(
            [sys.executable, str(CLIENT), *args],
            input=json.dumps(payload) if payload is not None else "",
            capture_output=True, text=True, env=self.env if env is None else env, timeout=5,
        )
        self.assertNotIn(SECRET, result.stdout + result.stderr)
        return result

    def call(self, method, payload=None, write=False, model="res.partner"):
        args = ["execute", model, method, "--input", "-"]
        if write:
            args.append("--allow-write")
        return self.cli(*args, payload=payload if payload is not None else {})

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_status_never_connects(self):
        result = self.assert_ok(self.cli("status"))
        self.assertTrue(result["ready"])
        self.assertTrue(result["secret_configured"])
        self.assertEqual(self.calls, [])

    def test_version_without_credentials(self):
        env = {key: value for key, value in self.env.items() if not key.startswith("ODOO_") or key == "ODOO_JALA_CONFIG_DIR"}
        result = self.assert_ok(self.cli("--url", self.url, "version", env=env))
        self.assertEqual(result["server_version"], "16.0")
        self.assertEqual(self.calls, [])

    def test_explicit_version_target_ignores_unreadable_saved_connection(self):
        state = Path(self.env["ODOO_JALA_CONFIG_DIR"])
        state.mkdir(parents=True)
        saved = state / "connection.json"
        saved.write_text("invalid-test-connection")
        saved.chmod(0o600)
        env = {key: value for key, value in self.env.items() if not key.startswith("ODOO_") or key == "ODOO_JALA_CONFIG_DIR"}
        result = self.assert_ok(self.cli("--url", self.url, "version", env=env))
        self.assertEqual(result["server_version"], "16.0")
        self.assertEqual(self.calls, [])

    def test_authentication_and_password_fallback(self):
        self.assertEqual(self.assert_ok(self.cli("authenticate")), {"uid": 42})
        self.env.pop("ODOO_API_KEY")
        self.env["ODOO_PASSWORD"] = SECRET
        self.assertEqual(self.assert_ok(self.cli("authenticate")), {"uid": 42})

    def test_key_precedence_and_failed_auth_blocks_model_call(self):
        self.env["ODOO_API_KEY"] = "incorrect-key"
        self.env["ODOO_PASSWORD"] = SECRET
        result = self.call("read", {"args": [[123]]})
        self.assertEqual(result.returncode, 1)
        self.assertIn("Authentication failed", result.stderr)
        self.assertEqual([call[0] for call in self.calls], ["authenticate"])

    def test_missing_credentials_are_actionable(self):
        for key in ["ODOO_API_KEY", "ODOO_PASSWORD"]:
            self.env.pop(key, None)
        result = self.cli("authenticate")
        self.assertEqual(result.returncode, 1)
        self.assertIn("ODOO_API_KEY", result.stderr)
        self.assertEqual(self.calls, [])

    def test_query_preserves_domain_fields_pagination_and_company(self):
        payload = {"args": [[["is_company", "=", True]]], "kwargs": {
            "fields": ["id", "name"], "limit": 5, "offset": 10, "order": "id asc",
            "context": {"allowed_company_ids": [7]},
        }}
        result = self.assert_ok(self.call("search_read", payload))
        self.assertEqual(result[0]["id"], 123)
        self.assertEqual(self.calls[-1], ("res.partner", "search_read", payload["args"], payload["kwargs"]))

    def test_fields_get_from_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps({"kwargs": {"attributes": ["type"]}}))
            result = self.assert_ok(self.cli("execute", "res.partner", "fields_get", "--input", str(path)))
        self.assertEqual(result["name"]["type"], "char")

    def test_writes_and_unknown_methods_block_before_auth(self):
        for method in ["create", "write", "unlink", "action_post", "custom_report"]:
            with self.subTest(method=method):
                result = self.call(method)
                self.assertEqual(result.returncode, 1)
                self.assertIn("read-only", result.stderr)
        self.assertEqual(self.calls, [])

    def test_allow_write_flag_cannot_enable_mutations(self):
        cases = [
            ("write", {"args": [[123], {"name": "Changed"}]}),
            ("create", {"args": [{"name": "Created"}]}),
            ("unlink", {"args": [[123]]}),
            ("action_post", {"args": [[123]]}),
            ("custom_report", {}),
        ]
        for method, payload in cases:
            with self.subTest(method=method):
                result = self.call(method, payload, write=True)
                self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.records, {123: {"id": 123, "name": "Before"}})

    def test_invalid_inputs_do_not_authenticate(self):
        payloads = [[], {"args": {}}, {"kwargs": []}, {"unexpected": True},
                    {"args": [None]}, {"kwargs": {"context": []}}, {"args": [2**40]},
                    {"args": [float("inf")]}]
        for payload in payloads:
            with self.subTest(payload=payload):
                self.assertEqual(self.call("read", payload).returncode, 1)
        self.assertEqual(self.calls, [])

    def test_uppercase_scheme_keeps_https_transport(self):
        result = self.assert_ok(self.cli("--url", "HTTPS://odoo.jala.tech/", "status"))
        self.assertEqual(result["url"], "https://odoo.jala.tech")

    def test_overflow_float_and_malformed_json_do_not_authenticate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            for body in ['{"args": [1e400]}', '{"args": [']:
                with self.subTest(body=body):
                    path.write_text(body)
                    result = self.cli("execute", "res.partner", "read", "--input", str(path))
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(json.loads(result.stderr)["error"], "input")
        self.assertEqual(self.calls, [])

    def test_invalid_url_and_timeout_do_not_connect(self):
        for args in [("--url", "http://example.com"),
                     ("--url", "https://user:secret@example.com"),
                     ("--url", "https://example.com/?token=secret"),
                     ("--timeout", "nan"), ("--timeout", "0")]:
            with self.subTest(args=args):
                self.assertEqual(self.cli(*args, "version").returncode, 1)
        self.assertEqual(self.calls, [])

    def test_fault_hides_server_traceback(self):
        result = self.call("read", model="test.fault")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr)["error"], "AccessError")
        self.assertNotIn("Traceback", result.stderr)

    def test_lost_response_does_not_repeat_read(self):
        self.server.lose_response = True
        result = self.call("read", {"args": [[123]]})
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr)["error"], "transport")
        self.assertEqual(self.records[123]["name"], "Before")
        self.assertEqual(sum(call[0] == "res.partner" for call in self.calls), 1)

    def test_binary_result_is_json(self):
        self.records[123]["attachment"] = xmlrpc.client.Binary(b"test")
        result = self.assert_ok(self.call("read", {"args": [[123]]}))
        self.assertEqual(result[0]["attachment"], {"base64": "dGVzdA=="})

    def test_unicode_result_survives_legacy_stdout_encoding(self):
        self.records[123]["name"] = "供应商 🦐"
        env = dict(self.env, PYTHONIOENCODING="cp1252")
        result = self.assert_ok(self.cli(
            "execute", "res.partner", "read", "--input", "-",
            payload={"args": [[123]]}, env=env,
        ))
        self.assertEqual(result[0]["name"], "供应商 🦐")


if __name__ == "__main__":
    unittest.main()
