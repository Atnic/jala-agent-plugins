import importlib.util
import io
import os
from pathlib import Path
import tempfile
import threading
import types
import sys
import unittest
from unittest.mock import patch
from unittest.mock import Mock
import urllib.error
import urllib.request

spec = importlib.util.spec_from_file_location("gateway", Path(__file__).parents[1] / "scripts" / "gateway.py")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)
native_store_factory = gateway.credential_store


class GatewayTests(unittest.TestCase):
    def test_skill_defaults_and_finance_selection(self):
        catalog, endpoint, body = gateway.prepare_skill_request("9router-chat", {"messages": []})
        self.assertEqual((catalog, endpoint), ("/v1/models", "/v1/chat/completions"))
        self.assertEqual(body["model"], "9router-jala")
        self.assertFalse(body["stream"])
        self.assertEqual(gateway.prepare_skill_request("9router-chat", {}, finance=True)[2]["model"], "9router-jala-finance")

    def test_skill_rejects_wrong_provider_or_finance_for_media(self):
        with self.assertRaises(ValueError):
            gateway.prepare_skill_request("9router-image", {}, model="xai/grok-2-image-1212")
        with self.assertRaises(ValueError):
            gateway.prepare_skill_request("9router-image", {}, finance=True)
        with self.assertRaises(ValueError):
            gateway.prepare_skill_request("9router-chat", {}, finance=True, model="9router-jala")

    def test_web_skills_select_exa_models_and_correct_endpoints(self):
        for skill, model, endpoint in [("9router-web-search", "exa/search", "/v1/search"), ("9router-web-fetch", "exa/fetch", "/v1/web/fetch")]:
            catalog, selected_endpoint, body = gateway.prepare_skill_request(skill, {})
            self.assertEqual(catalog, "/v1/models/web")
            self.assertEqual(selected_endpoint, endpoint)
            self.assertEqual(body["model"], model)
        with self.assertRaises(ValueError):
            gateway.prepare_skill_request("9router-web-search", {}, model="exa/fetch")

    def test_run_does_not_generate_when_model_disappears(self):
        with patch.object(gateway, "send", return_value=(b'{"data":[]}', "application/json")) as send:
            with self.assertRaises(ValueError):
                gateway.run_skill("9router-chat", {}, "test-secret")
            send.assert_called_once_with("/v1/models", "test-secret")

    def test_run_inserts_model_after_catalog_check(self):
        with patch.object(gateway, "send", side_effect=[(b'{"data":[{"id":"openai/text-embedding-3-large"}]}', "application/json"), (b'{"data":[]}', "application/json")]) as send:
            gateway.run_skill("9router-embeddings", {"input": "hello"}, "test-secret")
            self.assertEqual(send.call_args_list[0].args[0], "/v1/models/embedding")
            self.assertEqual(send.call_args_list[1].args[2], {"input": "hello", "model": "openai/text-embedding-3-large"})

    def test_native_backend_selection_on_macos_and_windows(self):
        mac = types.ModuleType("keyring.backends.macOS")
        windows = types.ModuleType("keyring.backends.Windows")
        mac_store = Mock()
        windows_store = Mock(priority=5)
        mac.Keyring = Mock(return_value=mac_store)
        windows.WinVaultKeyring = Mock(return_value=windows_store)
        modules = {"keyring": types.ModuleType("keyring"), "keyring.backends": types.ModuleType("keyring.backends"), "keyring.backends.macOS": mac, "keyring.backends.Windows": windows}
        with patch.dict(sys.modules, modules):
            with patch.object(gateway.sys, "platform", "darwin"):
                self.assertIs(native_store_factory(), mac_store)
            with patch.object(gateway.sys, "platform", "win32"):
                self.assertIs(native_store_factory(), windows_store)
                self.assertEqual(windows_store.persist, "local machine")

    def test_linux_selects_secret_service_explicitly(self):
        module = types.ModuleType("keyring.backends.SecretService")
        store = Mock(priority=5)
        module.Keyring = Mock(return_value=store)
        with patch.dict(sys.modules, {"keyring.backends.SecretService": module}), patch.object(gateway.sys, "platform", "linux"):
            self.assertIs(native_store_factory(), store)
            module.Keyring.assert_called_once()

    def test_linux_unavailable_service_uses_private_fallback(self):
        module = types.ModuleType("keyring.backends.SecretService")
        module.Keyring = Mock(side_effect=RuntimeError("no session bus"))
        with patch.dict(sys.modules, {"keyring.backends.SecretService": module}), patch.object(gateway.sys, "platform", "linux"), patch.object(gateway, "credential_store", native_store_factory):
            gateway.save_key("test-linux")
            self.assertEqual(gateway.read_plaintext_key(), "test-linux")
            self.assertEqual(gateway.credential_path().stat().st_mode & 0o777, 0o600)

    def test_unsupported_os_does_not_fallback_to_file(self):
        with patch.object(gateway.sys, "platform", "freebsd"), self.assertRaises(ValueError):
            native_store_factory()
        self.assertFalse(gateway.credential_path().exists())

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = patch.object(gateway.Path, "home", return_value=Path(self.temporary.name))
        self.home.start()
        self.addCleanup(self.home.stop)
        self.values = {}
        self.store = Mock()
        self.store.get_password.side_effect = lambda service, account: self.values.get((service, account))
        self.store.set_password.side_effect = lambda service, account, key: self.values.__setitem__((service, account), key)
        self.store.delete_password.side_effect = lambda service, account: self.values.pop((service, account))
        self.backend = patch.object(gateway, "credential_store", return_value=self.store)
        self.backend.start()
        self.addCleanup(self.backend.stop)

    def post_setup(self, server, key, token=None, origin=None):
        port = server.server_port
        import json
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/setup",
            data=json.dumps({"key": key}).encode(),
            headers={"Content-Type": "application/json",
                     "Origin": origin or f"http://127.0.0.1:{port}",
                     "X-Setup-Token": token or server.setup_url.split("token=")[1]})
        return urllib.request.urlopen(request, timeout=5)

    def test_web_submission_verifies_then_saves(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(gateway.Path, "home", return_value=Path(temporary)), patch.object(gateway, "send", return_value=(b'{"data":[]}', "application/json")) as send:
            with gateway.setup_server() as server:
                worker = threading.Thread(target=server.handle_request)
                worker.start()
                with self.post_setup(server, "test-web-secret") as response:
                    data = response.read()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                    self.assertNotIn(b"test-web-secret", data)
                worker.join(timeout=5)
                self.assertTrue(server.completed)
                self.assertEqual(self.values[(gateway.KEYRING_SERVICE, gateway.KEYRING_ACCOUNT)], "test-web-secret")
                self.assertFalse(gateway.credential_path().exists())
                send.assert_called_once_with("/v1/models", "test-web-secret")

    def test_web_rejects_other_origins_and_bad_session_tokens(self):
        with patch.object(gateway, "verify_and_save") as verify:
            with gateway.setup_server() as server:
                for token, origin in [("wrong", None), (None, "https://example.com")]:
                    worker = threading.Thread(target=server.handle_request)
                    worker.start()
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        self.post_setup(server, "test-web-secret", token, origin)
                    self.assertEqual(caught.exception.code, 403)
                    worker.join(timeout=5)
                verify.assert_not_called()

    def test_web_failure_does_not_save_or_echo_secret(self):
        with patch.object(gateway, "send", side_effect=ValueError("test-web-secret")), patch.object(gateway, "save_key") as save:
            with gateway.setup_server() as server:
                worker = threading.Thread(target=server.handle_request)
                worker.start()
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    self.post_setup(server, "test-web-secret")
                self.assertEqual(caught.exception.code, 400)
                self.assertNotIn(b"test-web-secret", caught.exception.read())
                worker.join(timeout=5)
                self.assertFalse(server.completed)
                save.assert_not_called()

    def test_saved_key_is_replaceable_without_plaintext_file(self):
        with patch.dict(os.environ, {}, clear=True):
            gateway.save_key("test-first")
            self.assertFalse(gateway.credential_path().exists())
            gateway.save_key("test-second")
            self.assertEqual(gateway.load_key(), "test-second")
            gateway.forget_key()
            self.assertFalse(self.values)

    def legacy_file(self):
        path = gateway.credential_path()
        path.parent.mkdir(parents=True)
        path.write_text("test-legacy")
        path.chmod(0o600)
        return path

    def test_migration_removes_plaintext_after_verified_write(self):
        path = self.legacy_file()
        gateway.migrate_key()
        self.assertFalse(path.exists())
        self.assertEqual(self.values[(gateway.KEYRING_SERVICE, gateway.KEYRING_ACCOUNT)], "test-legacy")

    def test_migration_preserves_plaintext_on_storage_failure(self):
        path = self.legacy_file()
        self.store.set_password.side_effect = RuntimeError("test-legacy")
        with self.assertRaises(ValueError) as caught:
            gateway.migrate_key()
        self.assertNotIn("test-legacy", str(caught.exception))
        self.assertTrue(path.exists())

    def test_failed_readback_preserves_legacy_file(self):
        path = self.legacy_file()
        self.store.get_password.side_effect = lambda *args: None
        with self.assertRaises(ValueError):
            gateway.save_key("test-replacement", allow_fallback=False)
        self.assertTrue(path.exists())

    def test_migration_does_not_replace_existing_os_key(self):
        path = self.legacy_file()
        self.values[(gateway.KEYRING_SERVICE, gateway.KEYRING_ACCOUNT)] = "test-existing"
        with self.assertRaises(ValueError):
            gateway.migrate_key()
        self.assertTrue(path.exists())
        self.store.set_password.assert_not_called()

    def test_plaintext_key_is_loaded(self):
        self.legacy_file()
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(gateway.load_key(), "test-legacy")

    def test_unavailable_store_falls_back_to_private_plaintext(self):
        self.store.set_password.side_effect = RuntimeError("store unavailable")
        gateway.save_key("test-fallback")
        path = gateway.credential_path()
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(gateway.load_key(), "test-fallback")

    def test_fallback_key_takes_precedence_over_stale_native_key(self):
        self.values[(gateway.KEYRING_SERVICE, gateway.KEYRING_ACCOUNT)] = "test-stale"
        gateway.save_plaintext_key("test-new")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(gateway.load_key(), "test-new")

    def test_successful_native_save_removes_fallback(self):
        gateway.save_plaintext_key("test-old")
        gateway.save_key("test-new")
        self.assertFalse(gateway.credential_path().exists())

    def test_permissive_plaintext_file_is_rejected(self):
        path = self.legacy_file()
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            gateway.read_plaintext_key()

    def test_environment_override(self):
        with patch.dict(os.environ, {"NINEROUTER_KEY": "test-env"}):
            self.assertEqual(gateway.load_key(), "test-env")

    def test_no_credentials_sent_to_external_url(self):
        for path in ["https://example.com/v1/models", "//example.com/v1/models", "/v1/../api/keys", "/api/keys"]:
            with self.assertRaises(ValueError):
                gateway.send(path, "test-secret")
        self.assertIsNone(gateway.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com"))

    def test_error_body_suppressed_and_no_retry(self):
        error = urllib.error.HTTPError(gateway.GATEWAY + "/v1/models", 401, "rejected", {}, io.BytesIO(b"test-secret"))
        with patch.object(gateway.urllib.request, "build_opener") as builder:
            builder.return_value.open.side_effect = error
            with self.assertRaisesRegex(ValueError, "401") as caught:
                gateway.send("/v1/models", "test-secret")
            self.assertNotIn("test-secret", str(caught.exception))
            builder.return_value.open.assert_called_once()

    def test_auth_header_and_json_body(self):
        with patch.object(gateway.urllib.request, "build_opener") as builder:
            response = builder.return_value.open.return_value.__enter__.return_value
            response.read.return_value = b'{"data":[]}'
            response.headers.get_content_type.return_value = "application/json"
            data, content_type = gateway.send("/v1/chat/completions", "test-secret", {"model": "discovered-model"})
            request = builder.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, gateway.GATEWAY + "/v1/chat/completions")
            self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
            self.assertEqual(request.get_method(), "POST")
            self.assertNotIn(b"test-secret", request.data)
            self.assertEqual(content_type, "application/json")

    def test_forget_removes_fallback_even_when_native_store_is_locked(self):
        path = self.legacy_file()
        self.store.get_password.side_effect = RuntimeError("locked")
        with self.assertRaisesRegex(ValueError, "native credential"):
            gateway.forget_key()
        self.assertFalse(path.exists())

    def test_forget_does_not_claim_success_when_backend_unavailable(self):
        path = self.legacy_file()
        with patch.object(gateway, "credential_store", side_effect=ValueError("unavailable")):
            with self.assertRaises(ValueError):
                gateway.forget_key()
        self.assertFalse(path.exists())

    def test_live_catalog_ids_are_translated_for_tts_and_exa(self):
        for skill, catalog_id, sent_id, body in [
            ("9router-tts", "openai/gpt-4o-mini-tts", "openai/gpt-4o-mini-tts/alloy", {"input": "hello", "voice": "alloy"}),
            ("9router-web-search", "exa/search", "exa", {"query": "hello"}),
            ("9router-web-fetch", "exa/fetch", "exa", {"url": "https://example.com"}),
        ]:
            catalog = ('{"data":[{"id":"' + catalog_id + '"}]}').encode()
            with patch.object(gateway, "send", side_effect=[(catalog, "application/json"), (b"{}", "application/json")]) as send:
                gateway.run_skill(skill, body, "test-secret")
                self.assertEqual(send.call_args.args[2]["model"], sent_id)
                self.assertNotIn("voice", send.call_args.args[2])

    def test_audio_upload_preserves_extension(self):
        audio = Path(self.temporary.name) / "sample.wav"
        audio.write_bytes(b"test-audio")
        with patch.object(gateway.urllib.request, "build_opener") as builder:
            response = builder.return_value.open.return_value.__enter__.return_value
            response.read.return_value = b"{}"
            response.headers.get_content_type.return_value = "application/json"
            gateway.send("/v1/audio/transcriptions", "test-secret", {"model": "openai/whisper-1"}, audio)
            self.assertIn(b'filename="audio.wav"', builder.return_value.open.call_args.args[0].data)

    def test_cli_rejects_unsavable_audio_before_generation(self):
        body = Path(self.temporary.name) / "body.json"
        body.write_text('{"input":"hello"}')
        for extra in [[], ["--output", str(Path(self.temporary.name) / "missing" / "speech.mp3")]]:
            argv = ["gateway.py", "run", "9router-tts", "--body", str(body), *extra]
            with patch.object(gateway.sys, "platform", "freebsd"), patch.object(sys, "argv", argv), patch.object(gateway, "run_skill") as run, patch.object(sys, "stderr", io.StringIO()):
                self.assertEqual(gateway.main(), 1)
                run.assert_not_called()

    def test_failed_request_removes_reserved_output(self):
        body = Path(self.temporary.name) / "body.json"
        body.write_text('{"input":"hello"}')
        output = Path(self.temporary.name) / "speech.mp3"
        argv = ["gateway.py", "run", "9router-tts", "--body", str(body), "--output", str(output)]
        with patch.object(gateway.sys, "platform", "freebsd"), patch.object(sys, "argv", argv), patch.object(gateway, "run_skill", side_effect=ValueError("failed")), patch.object(sys, "stderr", io.StringIO()):
            self.assertEqual(gateway.main(), 1)
        self.assertFalse(output.exists())

    def test_idle_connection_does_not_block_setup_form(self):
        import socket
        with gateway.setup_server() as server:
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            try:
                with socket.create_connection(("127.0.0.1", server.server_port)):
                    with urllib.request.urlopen(server.setup_url.split("#")[0], timeout=2) as response:
                        self.assertEqual(response.status, 200)
            finally:
                server.shutdown()
                worker.join(timeout=3)

    def test_setup_refuses_noninteractive_input(self):
        with patch.object(gateway.sys.stdin, "isatty", return_value=False), patch.object(gateway.getpass, "getpass") as prompt:
            with self.assertRaises(ValueError):
                gateway.setup()
            prompt.assert_not_called()


if __name__ == "__main__":
    unittest.main()
