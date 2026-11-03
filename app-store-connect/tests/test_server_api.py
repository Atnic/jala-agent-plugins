"""Read-only StoreKit behavior; synthetic keys and responses, no live accounts."""

import base64
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import threading
import urllib.request
import urllib.error
from urllib.parse import urlsplit, parse_qs
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import manage
import runtime
import server_api as api
import server_store as store
import local_setup
import unified_setup
from appstoreserverlibrary.api_client import APIException
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier, VerificationException, VerificationStatus


def connection():
    key = ec.generate_private_key(ec.SECP256R1())
    return {"key_id": "ABCDEFGHIJ", "issuer_id": "11111111-2222-3333-4444-555555555555",
            "private_key": key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                             serialization.NoEncryption()).decode(),
            "bundle_id": "com.example.app", "app_apple_id": 123, "verified_environments": {}}


def signed_page(items, more=False, revision="end"):
    return NS(signedTransactions=items, hasMore=more, revision=revision,
              bundleId="com.example.app", environment=Environment.PRODUCTION)


def decoded(tid="10", revocation=None):
    return NS(transactionId=tid, originalTransactionId=tid, productId="com.example.monthly",
              purchaseDate=1000, revocationDate=revocation, environment=Environment.PRODUCTION)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.values = {}
        self.keyring = Mock()
        self.keyring.get_password.side_effect = lambda s, a: self.values.get((s, a))
        self.keyring.set_password.side_effect = lambda s, a, v: self.values.__setitem__((s, a), v)
        self.keyring.delete_password.side_effect = lambda s, a: self.values.pop((s, a))
        patcher = patch("server_store._native_keyring", return_value=self.keyring)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_profiles_isolated_from_legacy_credentials(self):
        self.values[(runtime.SERVICE, runtime.ACCOUNT)] = "legacy-report-key"
        value = connection()
        store.save("one", value)
        store.save("two", value)
        store.mark_verified("one", "production", value)
        self.assertTrue(store.status("one")["verifiedEnvironments"]["production"])
        self.assertEqual(store.status("two")["verifiedEnvironments"], {})
        store.forget("one")
        self.assertFalse(store.status("one")["configured"])
        self.assertEqual(self.values[(runtime.SERVICE, runtime.ACCOUNT)], "legacy-report-key")
        self.assertNotIn(value["private_key"], json.dumps(store.status("two")))

    def test_storage_unavailable_has_no_plaintext_fallback(self):
        self.keyring.set_password.side_effect = OSError("private material")
        with self.assertRaises(runtime.StorageError) as raised:
            store.save("one", connection())
        self.assertNotIn("private material", str(raised.exception))

    def test_replaced_credentials_cannot_inherit_an_inflight_verification(self):
        previous, replacement = connection(), connection()
        store.save("one", previous)
        store.save("one", replacement)
        with self.assertRaises(runtime.StorageError):
            store.mark_verified("one", "production", previous)
        self.assertEqual(store.status("one")["verifiedEnvironments"], {})

    def test_profile_validation_and_setup_is_explicitly_unverified(self):
        with self.assertRaises(ValueError):
            store.profile_name("../one")
        with patch("local_setup.run_setup") as setup:
            store.setup("one")
        options = setup.call_args.kwargs
        value = connection()
        payload = {"keyId": value["key_id"], "issuerId": value["issuer_id"],
                   "privateKey": value["private_key"], "bundleId": value["bundle_id"], "appAppleId": "123"}
        parsed = options["validate"](payload)
        self.assertEqual(parsed["verified_environments"], {})
        self.assertEqual(options["describe"](parsed)["verification"], "unverified")
        options["save"](parsed)
        self.assertTrue(store.status("one")["configured"])


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.connection = connection()
        self.client, self.verifier = Mock(), Mock()
        self.verifier.verify_and_decode_signed_transaction.side_effect = lambda s: decoded(s, 2000 if s == "refund" else None)
        for target, value in [("server_api.server_store.load", self.connection),
                              ("server_api.services", (self.client, self.verifier))]:
            p = patch(target, return_value=value)
            p.start()
            self.addCleanup(p.stop)

    def run_cli(self, command, *extra):
        argv = ["server", command, "--profile", "one", "--environment", "production"]
        if command != "notification-history":
            argv.extend(["--transaction-id", "10"])
        argv.extend(extra)
        out, err = io.StringIO(), io.StringIO()
        with patch("manage.runtime_python", return_value=Path(sys.executable)), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = manage.main(argv)
        return code, json.loads(out.getvalue() or err.getvalue())

    def test_all_pages_keep_filters_and_v2(self):
        self.client.get_transaction_history.side_effect = [signed_page(["11"], True, "next"), signed_page(["12"])]
        code, result = self.run_cli("transaction-history", "--query", '{"productIds":["a","b"],"revoked":false}')
        self.assertEqual(code, 0)
        self.assertTrue(result["complete"])
        self.assertEqual(len(result["transactions"]), 2)
        calls = self.client.get_transaction_history.call_args_list
        self.assertIs(calls[0].args[2], calls[1].args[2])
        self.assertEqual(calls[1].args[1], "next")
        self.assertEqual(calls[0].args[3].value, "v2")
        self.assertFalse(calls[0].args[2].revoked)

    def test_page_cap_exposes_incomplete_cursor(self):
        self.client.get_refund_history.return_value = signed_page(["refund"], True, "next")
        code, result = self.run_cli("refund-history", "--max-pages", "1")
        self.assertEqual(code, 0)
        self.assertFalse(result["complete"])
        self.assertEqual(result["nextCursor"], "next")

    def test_repeated_history_snapshot_keeps_latest_signed_state(self):
        self.client.get_transaction_history.side_effect = [signed_page(["old"], True, "next"), signed_page(["new"])]
        older, newer = decoded("10"), decoded("10", 2000)
        older.signedDate, newer.signedDate = 1000, 3000
        self.verifier.verify_and_decode_signed_transaction.side_effect = [older, newer]
        code, result = self.run_cli("transaction-history")
        self.assertEqual(code, 0)
        self.assertEqual(len(result["transactions"]), 1)
        self.assertEqual(result["transactions"][0]["revocationDate"], 2000)
        self.assertEqual(result["duplicateSnapshotsRemoved"], 1)

    def test_missing_and_repeated_cursor_fail(self):
        for cursor in [None, "next"]:
            self.client.get_refund_history.side_effect = [signed_page([], True, "next"), signed_page([], True, cursor)]
            code, result = self.run_cli("refund-history")
            self.assertEqual(code, 1)
            self.assertIn("error", result)

    def test_missing_list_is_not_successful_empty_result(self):
        self.client.get_refund_history.return_value = signed_page(None)
        code, result = self.run_cli("refund-history")
        self.assertEqual(code, 1)
        self.assertIn("completeness", result["error"])

    def test_refund_filter_uses_revocation_not_purchase_date(self):
        self.client.get_refund_history.return_value = signed_page(["old-purchase", "refund"])
        code, result = self.run_cli("refund-history", "--revocation-start", "2000", "--revocation-end", "2001")
        self.assertEqual(code, 0)
        self.assertEqual([r["transactionId"] for r in result["transactions"]], ["refund"])
        self.assertEqual(result["transactions"][0]["purchaseDate"], 1000)

    def test_error_status_never_becomes_zero_results_or_leaks_message(self):
        for status, kind in [(401, "unauthenticated"), (403, "forbidden"), (404, "not-found"), (429, "rate-limited")]:
            self.client.get_transaction_info.side_effect = APIException(status, 123, "private-token")
            code, result = self.run_cli("transaction-info")
            self.assertEqual(code, 1)
            self.assertEqual(result["error"]["kind"], kind)
            self.assertIsNone(result["transactions"])
            self.assertNotIn("private-token", json.dumps(result))
        self.assertEqual(self.client.get_transaction_info.call_count, 4)

    def test_verification_failure_does_not_export_or_mark_verified(self):
        self.client.get_transaction_info.return_value = NS(signedTransactionInfo="forged")
        self.verifier.verify_and_decode_signed_transaction.side_effect = VerificationException(VerificationStatus.VERIFICATION_FAILURE)
        with tempfile.TemporaryDirectory() as d, patch("server_store.mark_verified") as mark:
            target = Path(d) / "data.json"
            code, result = self.run_cli("transaction-info", "--output-file", str(target))
            self.assertEqual(code, 1)
            self.assertEqual(result["error"]["kind"], "signature-verification-failed")
            self.assertFalse(target.exists())
            mark.assert_not_called()

    def test_notification_post_reads_all_pages_and_verifies_both_payloads(self):
        self.client.get_notification_history.side_effect = [
            NS(notificationHistory=[NS(signedPayload="outer")], hasMore=True, paginationToken="next"),
            NS(notificationHistory=[], hasMore=False, paginationToken=None)]
        self.verifier.verify_and_decode_notification.return_value = NS(notificationUUID="uuid", notificationType="REFUND",
            subtype=None, signedDate=3000, data=NS(signedTransactionInfo="refund"))
        code, result = self.run_cli("notification-history", "--body", '{"startDate":0,"endDate":4000,"notificationType":"REFUND"}')
        self.assertEqual(code, 0)
        self.assertTrue(result["complete"])
        self.assertEqual(result["scope"], "attempted-notification-deliveries")
        self.assertEqual(result["transactions"][0]["notificationUUID"], "uuid")
        self.assertEqual(result["transactions"][0]["notificationSignedDate"], 3000)
        self.assertIsNone(result["transactions"][0]["signedDate"])
        self.assertIsNone(result["transactions"][0]["signedDateUTC"])
        self.verifier.verify_and_decode_notification.assert_called_once_with("outer")
        self.verifier.verify_and_decode_signed_transaction.assert_called_once_with("refund")

    def test_csv_sidecar_preserves_completeness_and_does_not_overwrite(self):
        self.client.get_refund_history.return_value = signed_page(["refund"], True, "next")
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "rows.csv"
            code, result = self.run_cli("refund-history", "--max-pages", "1", "--format", "csv", "--output-file", str(target))
            self.assertEqual(code, 0)
            metadata = json.loads(Path(result["metadataFile"]).read_text())
            self.assertFalse(metadata["complete"])
            self.assertEqual(metadata["requestedTransactionId"], "10")
            self.assertEqual(metadata["bundleId"], "com.example.app")
            self.assertEqual(metadata["appAppleId"], 123)
            original = target.read_bytes()
            code, _ = self.run_cli("refund-history", "--max-pages", "1", "--format", "csv", "--output-file", str(target))
            self.assertEqual(code, 1)
            self.assertEqual(target.read_bytes(), original)

    def test_sidecar_collision_rolls_back_only_new_csv(self):
        self.client.get_refund_history.return_value = signed_page([])
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "rows.csv"
            sidecar = Path(str(target) + ".metadata.json")
            sidecar.write_text("existing")
            code, _ = self.run_cli("refund-history", "--format", "csv", "--output-file", str(target))
            self.assertEqual(code, 1)
            self.assertFalse(target.exists())
            self.assertEqual(sidecar.read_text(), "existing")

    def test_verify_records_only_verified_result(self):
        self.client.get_transaction_info.return_value = NS(signedTransactionInfo="10")
        with patch("server_store.mark_verified") as mark:
            code, result = self.run_cli("verify")
            self.assertEqual(code, 0)
            self.assertTrue(result["authenticationVerified"])
            mark.assert_called_once_with("one", "production", self.connection)

    def test_invalid_filters_fail_before_network(self):
        for query in ['{"startDate":"yesterday"}', '{"revoked":"false"}', '{"unknown":1}', '{"productIds":"a"}']:
            code, _ = self.run_cli("transaction-history", "--query", query)
            self.assertEqual(code, 1)
        self.client.get_transaction_history.assert_not_called()


class TransportAndSignatureTests(unittest.TestCase):
    def setUp(self):
        self.value = connection()
        self.client = api.ReadOnlyClient(self.value["private_key"].encode(), self.value["key_id"],
                                        self.value["issuer_id"], self.value["bundle_id"], Environment.PRODUCTION)

    def test_sdk_jwt_has_correct_app_claim_and_signature(self):
        token = self.client._generate_token()
        key = serialization.load_pem_private_key(self.value["private_key"].encode(), None)
        claims = jwt.decode(token, key.public_key(), algorithms=["ES256"], audience="appstoreconnect-v1")
        self.assertEqual(claims["bid"], "com.example.app")
        self.assertEqual(claims["iss"], self.value["issuer_id"])
        self.assertLessEqual(abs(claims["exp"] - int(time.time()) - 300), 2)

    def test_sdk_repeats_product_ids_and_disables_redirects(self):
        response = Mock(status_code=200, headers={"content-type": "application/json"})
        response.json.return_value = {"signedTransactions": [], "hasMore": False}
        with patch("server_api.requests.request", return_value=response) as request:
            self.client.get_transaction_history("10", None, api.filters({"productIds": ["a", "b"]}), api.GetTransactionHistoryVersion.V2)
        self.assertEqual(request.call_args.kwargs["params"]["productId"], ["a", "b"])
        self.assertFalse(request.call_args.kwargs["allow_redirects"])
        self.assertEqual(request.call_args.kwargs["timeout"], 30)

    def test_mutations_and_other_hosts_cannot_send_auth(self):
        with patch("server_api.requests.request") as request:
            for method, url in [("POST", "https://api.storekit.apple.com/inApps/v1/notifications/test"),
                                ("PUT", "https://api.storekit.apple.com/inApps/v1/transactions/10"),
                                ("GET", "https://example.com/inApps/v1/transactions/10"),
                                ("GET", "https://api.storekit.apple.com@evil.example/inApps/v1/transactions/10")]:
                with self.assertRaises(ValueError):
                    self.client._execute_request(method, url, {}, {"Authorization": "secret"}, None, None)
            request.assert_not_called()

    def test_real_verifier_rejects_untrusted_certificate_and_bad_signature(self):
        # Exercise the SDK verifier with a real signed JWT; no production root may trust this key.
        verifier = SignedDataVerifier([b"untrusted"], True, Environment.PRODUCTION, "com.example.app", 123)
        token = jwt.encode({"bundleId": "com.example.app", "environment": "Production"},
                           self.value["private_key"], algorithm="ES256", headers={"x5c": [base64.b64encode(b"invalid").decode()]})
        with self.assertRaises(VerificationException):
            api.transaction(verifier, token)

    def test_verifier_rejects_wrong_bundle_environment_and_tampering(self):
        key = serialization.load_pem_private_key(self.value["private_key"].encode(), None)
        public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        verifier = SignedDataVerifier([], False, Environment.PRODUCTION, "com.example.app", 123)
        # Isolate certificate-chain resolution; real ES256 and payload checks still run.
        with patch.object(verifier._chain_verifier, "verify_chain", return_value=public):
            for bundle, env in [("other.app", "Production"), ("com.example.app", "Sandbox")]:
                token = jwt.encode({"bundleId": bundle, "environment": env}, self.value["private_key"], algorithm="ES256", headers={"x5c": ["fixture"]})
                with self.assertRaises(VerificationException):
                    api.transaction(verifier, token)
            token = jwt.encode({"bundleId": "com.example.app", "environment": "Production"}, connection()["private_key"], algorithm="ES256", headers={"x5c": ["fixture"]})
            with self.assertRaises(VerificationException):
                api.transaction(verifier, token)

    def test_real_signed_transaction_retains_timestamps_and_missing_fields(self):
        key = serialization.load_pem_private_key(self.value["private_key"].encode(), None)
        public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        verifier = SignedDataVerifier([], False, Environment.PRODUCTION, "com.example.app", 123)
        token = jwt.encode({"bundleId": "com.example.app", "environment": "Production", "transactionId": "10",
                            "originalTransactionId": "10", "productId": "com.example.monthly", "purchaseDate": 1000},
                           self.value["private_key"], algorithm="ES256", headers={"x5c": ["fixture"]})
        with patch.object(verifier._chain_verifier, "verify_chain", return_value=public):
            result = api.transaction(verifier, token)
        self.assertEqual(result["purchaseDate"], 1000)
        self.assertEqual(result["purchaseDateUTC"], "1970-01-01T00:00:01+00:00")
        self.assertIsNone(result["appAccountToken"])
        self.assertIsNone(result["revocationDate"])

    def test_notification_verification_rejects_wrong_apple_app_id(self):
        key = serialization.load_pem_private_key(self.value["private_key"].encode(), None)
        public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        verifier = SignedDataVerifier([], False, Environment.PRODUCTION, "com.example.app", 123)
        token = jwt.encode({"notificationType": "REFUND", "data": {"bundleId": "com.example.app",
                           "environment": "Production", "appAppleId": 999}}, self.value["private_key"],
                           algorithm="ES256", headers={"x5c": ["fixture"]})
        with patch.object(verifier._chain_verifier, "verify_chain", return_value=public), self.assertRaises(VerificationException):
            verifier.verify_and_decode_notification(token)

    def test_bundled_roots_match_provenance_and_services_select_environment(self):
        import hashlib
        from cryptography import x509
        roots = Path(api.__file__).parents[1] / "assets" / "apple-roots"
        for name, info in json.loads((roots / "sources.json").read_text()).items():
            data = (roots / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), info["sha256"])
            cert = x509.load_der_x509_certificate(data)
            self.assertEqual(cert.subject, cert.issuer)
        with patch("server_api.SignedDataVerifier") as verifier:
            client, _ = api.services(self.value, "sandbox")
            with patch("server_api.requests.request") as request:
                request.return_value = Mock(status_code=200, headers={"content-type": "application/json"})
                request.return_value.json.return_value = {"signedTransactionInfo": "signed"}
                client.get_transaction_info("10")
            self.assertTrue(request.call_args.args[1].startswith("https://api.storekit-sandbox.apple.com/"))
            self.assertTrue(verifier.call_args.args[1])  # online certificate checks remain enabled


class LocalSetupTests(unittest.TestCase):
    def test_form_origin_session_validation_and_unverified_save(self):
        saved = Mock(return_value="native")
        server = local_setup.setup_server(
            form_path=Path(api.__file__).parents[1] / "assets" / "server-setup.html",
            validate=lambda payload: payload, verify=lambda value: None, save=saved,
            describe=lambda value: {"profile": "fixture", "verification": "unverified"})
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        token = parse_qs(urlsplit(server.setup_url).fragment)["session"][0]
        try:
            with urllib.request.urlopen(base) as page:
                self.assertIn(b"Access remains unverified", page.read())
                self.assertIn("frame-ancestors 'none'", page.headers["Content-Security-Policy"])
            payload = json.dumps({"keyId": "fixture"}).encode()
            headers = {"Content-Type": "application/json", "X-Setup-Token": token, "Origin": "https://untrusted.example"}
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(urllib.request.Request(base + "/api/setup", data=payload, headers=headers))
            self.assertEqual(raised.exception.code, 403)
            saved.assert_not_called()
            headers["Origin"] = base
            with urllib.request.urlopen(urllib.request.Request(base + "/api/setup", data=payload, headers=headers)) as response:
                result = json.load(response)
            self.assertEqual(result["verification"], "unverified")
            self.assertNotIn("connected", result)
            saved.assert_called_once_with({"keyId": "fixture"})
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(urllib.request.Request(base + "/api/setup", data=payload, headers=headers))
            self.assertEqual(raised.exception.code, 410)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


class UnifiedSetupTests(unittest.TestCase):
    def setUp(self):
        self.values = {}
        keyring = Mock()
        keyring.get_password.side_effect = lambda s, a: self.values.get((s, a))
        keyring.set_password.side_effect = lambda s, a, v: self.values.__setitem__((s, a), v)
        keyring.delete_password.side_effect = lambda s, a: self.values.pop((s, a))
        for target in ("runtime._native_keyring", "server_store._native_keyring"):
            p = patch(target, return_value=keyring)
            p.start()
            self.addCleanup(p.stop)
        value = connection()
        self.payload = {"keyId": value["key_id"], "issuerId": value["issuer_id"],
                        "privateKey": value["private_key"], "bundleId": value["bundle_id"], "appAppleId": "123"}
        self.reporting = {"keyType": "team", **{k: self.payload[k] for k in ("keyId", "issuerId", "privateKey")}}

    def test_reporting_only_keeps_server_unconfigured_and_requires_done(self):
        process = unified_setup.processor()
        with patch("local_setup.verify_key") as verify:
            result = process({"action": "connect-reporting", "connection": self.reporting})
        self.assertFalse(result["completed"])
        self.assertTrue(result["reporting"]["configured"])
        self.assertIsNone(result["server"])
        verify.assert_called_once()
        self.assertTrue(process({"action": "finish"})["completed"])
        self.assertEqual(set(self.values), {(runtime.SERVICE, runtime.ACCOUNT)})

    def test_server_only_and_both_do_not_reuse_or_replace_other_credentials(self):
        process = unified_setup.processor("fixture")
        first = process({"action": "connect-server", "connection": self.payload})
        self.assertFalse(first["reporting"]["configured"])
        self.assertEqual(first["server"]["verifiedEnvironments"], {})
        original = self.values[(store.SERVICE, "fixture")]
        with patch("local_setup.verify_key"):
            second = process({"action": "connect-reporting", "connection": self.reporting})
        self.assertTrue(second["reporting"]["configured"])
        self.assertEqual(self.values[(store.SERVICE, "fixture")], original)
        self.assertTrue(process({"action": "finish"})["completed"])

    def test_failed_reporting_verification_preserves_server_success_and_reporting_key(self):
        process = unified_setup.processor("fixture")
        process({"action": "connect-server", "connection": self.payload})
        with patch("local_setup.verify_key", side_effect=ValueError("Rejected")), self.assertRaises(ValueError):
            process({"action": "connect-reporting", "connection": self.reporting})
        state = process({"action": "status"})
        self.assertTrue(state["server"]["configured"])
        self.assertFalse(state["reporting"]["configured"])
        self.assertTrue(process({"action": "finish"})["completed"])

    def test_server_failure_preserves_existing_reporting_connection(self):
        process = unified_setup.processor("fixture")
        with patch("local_setup.verify_key"):
            process({"action": "connect-reporting", "connection": self.reporting})
        original = self.values[(runtime.SERVICE, runtime.ACCOUNT)]
        with self.assertRaises(ValueError):
            process({"action": "connect-server", "connection": {}})
        self.assertEqual(self.values[(runtime.SERVICE, runtime.ACCOUNT)], original)

    def test_no_default_profile_or_implicit_issuer(self):
        process = unified_setup.processor()
        with self.assertRaises(ValueError):
            process({"action": "connect-server", "connection": self.payload})
        with self.assertRaises(ValueError):
            process({"action": "connect-server", "profile": "fixture", "connection": {**self.payload, "issuerId": ""}})
        with self.assertRaises(ValueError):
            process({"action": "finish"})
        self.assertEqual(self.values, {})

    def test_invalid_purchase_profile_does_not_block_reporting_setup(self):
        process = unified_setup.processor()
        with patch("local_setup.verify_key"):
            result = process({"action": "connect-reporting", "profile": "unfinished profile name", "connection": self.reporting})
        self.assertTrue(result["reporting"]["configured"])
        self.assertIsNone(result["server"])

    def test_inline_verification_error_is_not_success_and_saved_profile_remains(self):
        process = unified_setup.processor("fixture")
        process({"action": "connect-server", "connection": self.payload})
        with patch("server_api.execute", return_value={"error": {"kind": "unauthenticated"}, "transactions": None}) as verify:
            result = process({"action": "verify-server", "environment": "production", "transactionId": "10"})
        self.assertTrue(result["server"]["configured"])
        self.assertEqual(result["server"]["verifiedEnvironments"], {})
        self.assertIn("error", result["lastVerification"])
        self.assertEqual(verify.call_args.args[0].profile, "fixture")
        self.assertFalse(result["completed"])

    def test_unified_loopback_accepts_multiple_actions_until_done(self):
        server = local_setup.setup_server(
            form_path=Path(api.__file__).parents[1] / "assets" / "unified-setup.html",
            process=unified_setup.processor("fixture"), replacements={"__SERVER_PROFILE__": "fixture"})
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        token = parse_qs(urlsplit(server.setup_url).fragment)["session"][0]

        def post(payload):
            request = urllib.request.Request(base + "/api/setup", data=json.dumps(payload).encode(), headers={
                "Content-Type": "application/json", "Origin": base, "X-Setup-Token": token})
            with urllib.request.urlopen(request) as response:
                return json.load(response)

        try:
            self.assertFalse(post({"action": "status"})["completed"])
            self.assertFalse(post({"action": "connect-server", "connection": self.payload})["completed"])
            self.assertFalse(server.completed)
            self.assertTrue(post({"action": "finish"})["completed"])
            self.assertTrue(server.completed)
            with self.assertRaises(urllib.error.HTTPError) as raised:
                post({"action": "status"})
            self.assertEqual(raised.exception.code, 410)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_legacy_loopback_setup_still_verifies_before_save(self):
        validate, verify, save = Mock(return_value={"key_type": "team", "key_id": "fixture"}), Mock(), Mock(return_value="native")
        server = local_setup.setup_server(validate=validate, verify=verify, save=save)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        token = parse_qs(urlsplit(server.setup_url).fragment)["session"][0]
        try:
            with urllib.request.urlopen(urllib.request.Request(base + "/api/setup", data=b"{}", headers={
                    "Content-Type": "application/json", "Origin": base, "X-Setup-Token": token})) as response:
                self.assertEqual(json.load(response)["keyType"], "team")
            verify.assert_called_once_with(validate.return_value)
            save.assert_called_once_with(validate.return_value)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
