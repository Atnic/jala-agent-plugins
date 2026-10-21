import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
import urllib.error
import urllib.request


spec = importlib.util.spec_from_file_location(
    "crisp_api", Path(__file__).parents[1] / "skills/crisp-jala/scripts/crisp_api.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
CONNECTION = {"token_id": "test-id", "token_key": "test-secret", "website_id": "test-workspace"}


class CrispTests(unittest.TestCase):
    def test_secret_store_round_trip(self):
        store = MagicMock()
        saved = {}
        store.set_password.side_effect = lambda service, account, value: saved.update(value=value)
        store.get_password.side_effect = lambda *args: saved.get("value")
        with patch.object(api, "credential_store", return_value=store):
            api.save_connection(CONNECTION)
            self.assertEqual(api.load_connection(), CONNECTION)
        self.assertEqual(store.set_password.call_args.args[:2], (api.SERVICE, api.ACCOUNT))

    def test_backend_failure_is_redacted(self):
        store = MagicMock()
        store.get_password.side_effect = RuntimeError(CONNECTION["token_key"])
        with patch.object(api, "credential_store", return_value=store):
            with self.assertRaises(ValueError) as error:
                api.load_connection()
        self.assertNotIn(CONNECTION["token_key"], str(error.exception))

    def test_request_uses_saved_workspace_and_basic_auth(self):
        response = MagicMock(status=200)
        response.read.return_value = b'{"error":false,"data":[]}'
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value = response
        with patch.object(api.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(api.request(CONNECTION, path="conversations/1?per_page=20")["status"], 200)
        req = opener.open.call_args.args[0]
        self.assertEqual(req.full_url, api.API_URL + "/v1/website/test-workspace/conversations/1?per_page=20")
        self.assertEqual(req.get_header("Authorization"), "Basic dGVzdC1pZDp0ZXN0LXNlY3JldA==")
        self.assertEqual(req.get_header("Accept"), "application/json")
        self.assertIsNone(req.get_header("X-crisp-tier"))

    def test_rejects_routes_outside_workspace(self):
        for path in ("https://example.com", "//example.com", "/v1/website/other", "../other", "%2e%2e/other", "a/../other", "a\\..\\other"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                api.request(CONNECTION, path=path)

    def test_redirects_are_not_followed(self):
        self.assertIsNone(api.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com"))

    def test_verify_failure_does_not_save(self):
        with patch.object(api, "request", side_effect=ValueError("Unauthorized")), patch.object(api, "save_connection") as save:
            with self.assertRaises(ValueError):
                api.verify_and_save(CONNECTION)
            save.assert_not_called()

    def test_ambiguous_write_is_not_retried(self):
        opener = MagicMock()
        opener.open.side_effect = TimeoutError()
        with patch.object(api.urllib.request, "build_opener", return_value=opener):
            with self.assertRaisesRegex(ValueError, "not retried"):
                api.request(CONNECTION, "POST", "conversation/session/message", {"content": "test"})
        self.assertEqual(opener.open.call_count, 1)

    def test_import_browser_session_verifies_before_saving(self):
        value = {"request_url": "https://app.crisp.chat/api/v1/website/bca9165d-d26a-4a8f-a8d5-5625fb1a3f2b/conversations/1?per_page=20",
                 "authorization": "Basic dGVzdC1pZDp0ZXN0LXNlY3JldA=="}
        with patch.object(api, "verify_and_save") as save:
            result = api.import_session(value)
        self.assertTrue(result["saved"])
        save.assert_called_once_with({**CONNECTION, "website_id": "bca9165d-d26a-4a8f-a8d5-5625fb1a3f2b"})
        self.assertNotIn("test-secret", json.dumps(result))

    def test_import_rejects_other_origins_and_malformed_credentials(self):
        path = "/api/v1/website/bca9165d-d26a-4a8f-a8d5-5625fb1a3f2b/conversations/1"
        for origin, auth in (("https://example.com", "Basic dGVzdC1pZDp0ZXN0LXNlY3JldA=="),
                             ("https://app.crisp.chat", "Basic invalid!"),
                             ("https://app.crisp.chat", "Bearer secret")):
            with self.subTest(origin=origin, auth=auth), patch.object(api, "save_connection") as save:
                with self.assertRaises(ValueError):
                    api.import_session({"request_url": origin + path, "authorization": auth})
                save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
