"""Discovery over a real loopback XML-RPC transport, with metadata fixtures."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from xmlrpc.server import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer
import xmlrpc.client

from helpers import isolated_environment


CLIENT = Path(__file__).resolve().parents[1] / "skills/odoo-jala-xmlrpc/scripts/odoo_rpc.py"
SECRET = "discovery-test-secret-never-export"


class Handler(SimpleXMLRPCRequestHandler):
    rpc_paths = ("/xmlrpc/2/common", "/xmlrpc/2/object")


class DiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = SimpleXMLRPCServer(("127.0.0.1", 0), Handler, logRequests=False, allow_none=True)
        cls.server.register_function(lambda: cls.version, "version")
        cls.server.register_function(lambda db, login, secret, context: cls.uid if secret == SECRET else False, "authenticate")
        cls.server.register_function(cls.execute, "execute_kw")
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.env = isolated_environment(self.directory.name)
        self.env.update(ODOO_URL=self.url, ODOO_DB="test-db", ODOO_USERNAME="test-user",
                        ODOO_API_KEY=SECRET)
        cls = type(self)
        cls.uid, cls.calls, cls.denied = 42, [], set()
        cls.version = {"server_version": "16.0", "server_serie": "16.0"}
        cls.fields = {"purchase.order": {
            "name": {"string": "Reference", "type": "char", "required": True},
            "state": {"string": "Status", "type": "selection", "selection": [["draft", "RFQ"], ["jala_review", "JALA review"]]},
            "approval_stage": {"string": "Approval stage", "type": "many2one", "relation": "jala.approval.stage"},
        }}
        cls.data = {
            "ir.module.module": [
                {"id": 1, "name": "purchase", "shortdesc": "Purchase", "author": "Odoo S.A.", "state": "installed", "latest_version": "16.0.1", "installed_version": "16.0.2", "application": True},
                {"id": 2, "name": "jala_approvals", "shortdesc": "JALA Purchase", "author": "JALA", "state": "installed", "latest_version": "16.0.3", "installed_version": "16.0.3", "application": False},
                {"id": 3, "name": "approval_matrix", "shortdesc": "Approval Matrix", "author": "JALA", "state": "installed", "latest_version": "16.0.1", "installed_version": "16.0.1", "application": False},
                {"id": 4, "name": "uninstalled_addon", "state": "uninstalled", "author": "Other"},
            ],
            "ir.module.module.dependency": [
                {"id": 1, "module_id": [2, "JALA Purchase"], "name": "purchase"},
                {"id": 2, "module_id": [3, "Approval Matrix"], "name": "mail"},
            ],
            "ir.model": [
                {"id": 1, "model": "purchase.order", "name": "Purchase Order", "state": "base", "transient": False, "modules": "purchase, jala_approvals, approval_matrix"},
                {"id": 2, "model": "x_expense", "name": "Manual Expense", "state": "manual", "transient": False, "modules": False},
                {"id": 3, "model": "jala.approval.stage", "name": "Approval Stage", "state": "base", "transient": False, "modules": "approval_matrix"},
            ],
            "ir.model.fields": [
                {"id": 1, "model": "purchase.order", "name": "approval_stage", "ttype": "many2one", "state": "base", "modules": "approval_matrix", "relation": "jala.approval.stage", "required": False},
                {"id": 2, "model": "purchase.order", "name": "restricted_cost", "ttype": "float", "state": "base", "modules": "jala_approvals"},
            ],
            "ir.ui.menu": [{"id": 1, "name": "Purchases", "parent_id": False, "action": "ir.actions.act_window,1"}],
            "ir.actions.act_window": [{"id": 1, "name": "Purchase Orders", "res_model": "purchase.order", "view_mode": "tree,form", "domain": "[]", "context": "{'search_default_my': 1}"}],
            "ir.ui.view": [{"id": 1, "name": "Custom purchase form", "model": "purchase.order", "type": "form", "inherit_id": [99, "Base purchase form"], "active": True}],
            "res.company": [
                {"id": 1, "name": "Company A", "currency_id": [1, "IDR"]},
                {"id": 2, "name": "Company B", "currency_id": [2, "USD"]},
            ],
        }

    @classmethod
    def execute(cls, db, uid, secret, model, method, args, kwargs):
        if uid != cls.uid or secret != SECRET:
            raise xmlrpc.client.Fault(1, "AccessDenied")
        cls.calls.append((model, method, args, copy.deepcopy(kwargs)))
        if model in cls.denied:
            raise xmlrpc.client.Fault(1, "odoo.exceptions.AccessError: " + SECRET)
        if model == "res.users" and method == "read":
            return [{"id": uid, "company_id": [1, "Company A"], "company_ids": [1, 2], "lang": "en_US", "tz": "Asia/Jakarta"}]
        if method == "fields_get":
            if model in cls.fields:
                return cls.fields[model]
            if model not in cls.data:
                raise xmlrpc.client.Fault(1, "Missing model")
            names = set().union(*(record.keys() for record in cls.data[model]))
            return {name: {"type": "char", "string": name} for name in names}
        if method == "check_access_rights":
            return args[0] == "read"
        if method != "search_read":
            raise xmlrpc.client.Fault(1, "Unexpected method")
        records = cls.data[model]
        for field, operator, value in args[0]:
            def match(record):
                actual = record.get(field)
                if isinstance(actual, list) and actual and isinstance(actual[0], int):
                    actual = actual[0]
                return {"=": lambda: actual == value, "in": lambda: actual in value,
                        ">": lambda: actual > value}[operator]()
            records = list(filter(match, records))
        return [{field: row.get(field, False) for field in kwargs["fields"]}
                for row in sorted(records, key=lambda row: row["id"])[:kwargs["limit"]]]

    def discover(self, *args, success=True):
        result = subprocess.run([sys.executable, str(CLIENT), "discover", *args], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertNotIn(SECRET, result.stdout + result.stderr)
        if not success:
            self.assertNotEqual(result.returncode, 0)
            return result
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        path = Path(summary["profile_path"])
        contents = path.read_text()
        self.assertNotIn(SECRET, contents)
        self.assertNotIn('"secret"', contents)
        return summary, json.loads(contents)

    def test_inventory_maps_python_addons_and_manual_models_without_reading_business_records(self):
        summary, profile = self.discover("--model", "purchase.order")
        self.assertFalse(summary["inventory_reused"])
        modules = profile["inventory"]["installed_addons"]["records"]
        self.assertEqual([row["name"] for row in modules], ["purchase", "jala_approvals", "approval_matrix"])
        origins = profile["inventory"]["model_origins"]["records"]
        self.assertIn("approval_matrix", origins[0]["modules"])
        candidates = {row["name"]: row for row in profile["customization_signals"]["addon_candidates"]}
        self.assertIn("approval_matrix", candidates)
        self.assertEqual(candidates["approval_matrix"]["classification"], "unverified_candidate")
        self.assertNotIn("purchase", candidates)
        self.assertIn("jala_approvals", profile["source_reference"]["matching_installed_names"])
        locations = profile["source_reference"]["model_source_candidates"]["purchase.order"]
        self.assertTrue(any(row["addon"] == "jala_approvals" and row["file"] == "jala_approvals/models/purchase_order.py" for row in locations))
        self.assertEqual(profile["customization_signals"]["manual_models"], ["x_expense"])
        detail = profile["model_details"]["purchase.order"]
        self.assertEqual(detail["fields"]["value"]["approval_stage"]["relation"], "jala.approval.stage")
        self.assertEqual(detail["fields"]["value"]["state"]["selection"][-1][0], "jala_review")
        self.assertEqual([row["name"] for row in detail["field_origins"]["records"]], ["approval_stage"])
        self.assertFalse(detail["model_access"]["write"]["value"])
        for model, method, args, kwargs in type(self).calls:
            self.assertIn(method, {"fields_get", "read", "search_read", "check_access_rights"})
            if model == "purchase.order":
                self.assertIn(method, {"fields_get", "check_access_rights"})
            if method == "search_read":
                self.assertGreater(kwargs["limit"], 0)
                self.assertEqual(kwargs["order"], "id asc")
        if os.name == "posix":
            self.assertEqual(Path(summary["profile_path"]).stat().st_mode & 0o777, 0o600)

    def test_permission_denial_is_incomplete_and_target_schema_still_available(self):
        type(self).denied = {"ir.module.module", "ir.model"}
        summary, profile = self.discover("--model", "purchase.order")
        self.assertEqual(summary["inventory"]["installed_addons"]["status"], "denied")
        self.assertEqual(summary["inventory"]["models"]["status"], "denied")
        self.assertEqual(summary["inventory"]["model_origins"]["status"], "not_attempted")
        self.assertEqual(profile["model_details"]["purchase.order"]["fields"]["status"], "ok")

    def test_pagination_is_bounded_and_reports_truncation(self):
        summary, profile = self.discover("--limit", "2")
        self.assertEqual(summary["inventory"]["models"], {"status": "truncated", "count": 2})
        self.assertEqual(len(profile["inventory"]["installed_addons"]["records"]), 2)
        self.assertLessEqual(max(call[3].get("limit", 0) for call in type(self).calls), 3)

    def test_inventory_cache_reused_but_requested_schema_and_permissions_are_fresh(self):
        first, _ = self.discover("--model", "purchase.order")
        type(self).calls = []
        type(self).fields["purchase.order"]["new_field"] = {"type": "char", "string": "New field"}
        second, profile = self.discover("--model", "purchase.order")
        self.assertTrue(second["inventory_reused"])
        self.assertEqual(first["inventory_at"], second["inventory_at"])
        self.assertIn("new_field", profile["model_details"]["purchase.order"]["fields"]["value"])
        self.assertFalse(any(call[0] == "ir.module.module" for call in type(self).calls))
        self.assertTrue(any(call[:2] == ("purchase.order", "check_access_rights") for call in type(self).calls))
        type(self).denied.add("purchase.order")
        _, profile = self.discover("--model", "purchase.order")
        self.assertEqual(profile["model_details"]["purchase.order"]["fields"]["status"], "denied")
        self.assertNotIn("value", profile["model_details"]["purchase.order"]["fields"])

    def test_company_user_and_database_profiles_do_not_mix(self):
        first, _ = self.discover()
        type(self).calls = []
        second, _ = self.discover("--company-id", "2")
        self.assertNotEqual(first["profile_path"], second["profile_path"])
        self.assertEqual(second["context"]["allowed_company_ids"], [2])
        for model, method, args, kwargs in type(self).calls:
            if model != "res.users":
                self.assertEqual(kwargs["context"]["allowed_company_ids"], [2])
        type(self).uid = 99
        third, _ = self.discover()
        self.assertNotEqual(first["profile_path"], third["profile_path"])
        self.env["ODOO_DB"] = "another-db"
        fourth, _ = self.discover()
        self.assertNotEqual(third["profile_path"], fourth["profile_path"])

    def test_invalid_scope_is_rejected_before_inventory(self):
        self.discover("--company-id", "999", success=False)
        self.assertEqual([call[0] for call in type(self).calls], ["res.users"])
        self.discover("--model", "_private.model", success=False)
        self.discover("--limit", "0", success=False)
        self.discover("--company-id", "-1", success=False)

    def test_expiry_version_change_and_refresh_invalidate_inventory(self):
        first, profile = self.discover()
        path = Path(first["profile_path"])
        profile["inventory_at"] = "2000-01-01T00:00:00+00:00"
        path.write_text(json.dumps(profile))
        second, _ = self.discover()
        self.assertFalse(second["inventory_reused"])
        type(self).version["server_version"] = "16.0+updated"
        third, _ = self.discover()
        self.assertFalse(third["inventory_reused"])
        type(self).denied.add("ir.module.module")
        fourth, _ = self.discover("--refresh")
        self.assertFalse(fourth["inventory_reused"])
        self.assertEqual(fourth["inventory"]["installed_addons"]["status"], "denied")


    def test_requested_company_priority_is_preserved_and_cached_separately(self):
        second_first, _ = self.discover("--company-id", "2", "--company-id", "1", "--company-id", "2")
        self.assertEqual(second_first["context"]["allowed_company_ids"], [2, 1])
        first_second, _ = self.discover("--company-id", "1", "--company-id", "2")
        self.assertEqual(first_second["context"]["allowed_company_ids"], [1, 2])
        self.assertNotEqual(second_first["profile_path"], first_second["profile_path"])
        repeat, _ = self.discover("--company-id", "2", "--company-id", "1")
        self.assertTrue(repeat["inventory_reused"])
        self.assertEqual(repeat["profile_path"], second_first["profile_path"])


if __name__ == "__main__":
    unittest.main()
