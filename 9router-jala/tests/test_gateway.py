import importlib.util
import io
import json
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

    def test_image_defaults_match_verified_minimal_request(self):
        body = {"prompt": "an orange car"}
        catalog, endpoint, prepared = gateway.prepare_skill_request("9router-image", body)
        self.assertEqual(catalog, "/v1/models/image")
        self.assertEqual(endpoint, "/v1/images/generations")
        self.assertEqual(prepared, {"prompt": "an orange car", "model": "openai/gpt-image-2.5-sunburst", "n": 1})
        self.assertEqual(body, {"prompt": "an orange car"})
        catalog_response = b'{"data":[{"id":"openai/gpt-image-2.5-sunburst"}]}'
        with patch.object(gateway, "send", side_effect=[(catalog_response, "application/json"), (b'{"data":[]}', "application/json")]) as send:
            gateway.run_skill("9router-image", body, "test-secret")
            self.assertEqual(send.call_args.args[2], prepared)
            self.assertEqual(send.call_count, 2)

    def test_image_explicit_options_are_preserved(self):
        body = {"prompt": "car", "n": 2, "size": "1536x1024", "response_format": "b64_json"}
        prepared = gateway.prepare_skill_request("9router-image", body)[2]
        self.assertEqual(prepared, {**body, "model": "openai/gpt-image-2.5-sunburst"})

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

    def post_setup(self, server, key, token=None, origin=None, auth_mode=None):
        port = server.server_port
        import json
        payload = {"key": key}
        if auth_mode is not None:
            payload["auth_mode"] = auth_mode
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}{server.setup_endpoint}",
            data=json.dumps(payload).encode(),
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

    def test_codex_config_merge_preserves_other_provider_and_settings(self):
        existing = '''model = "another-model"
model_provider = "another-provider"
approval_policy = "on-request"
preferred_auth_method = "apikey"

[model_providers.another-provider]
base_url = "https://example.test/v1"

[model_providers.9router-jala]
custom_setting = "preserve"
wire_api = "chat" # retain this note
'''
        merged = gateway.merge_codex_config(existing, "/tmp/codex/models_9router_jala.json", 'key"\\value')
        parsed = gateway.tomllib.loads(merged)
        self.assertEqual(parsed["approval_policy"], "on-request")
        self.assertEqual(parsed["model"], "9router-jala")
        self.assertEqual(parsed["model_provider"], "9router-jala")
        self.assertNotIn("preferred_auth_method", parsed)
        self.assertEqual(parsed["forced_login_method"], "chatgpt")
        self.assertEqual(parsed["model_reasoning_effort"], "high")
        self.assertEqual(parsed["model_catalog_json"], "/tmp/codex/models_9router_jala.json")
        self.assertEqual(parsed["model_providers"]["another-provider"]["base_url"], "https://example.test/v1")
        self.assertEqual(parsed["model_providers"]["9router-jala"]["custom_setting"], "preserve")
        self.assertEqual(parsed["model_providers"]["9router-jala"]["name"], "9Router JALA")
        self.assertEqual(parsed["model_providers"]["9router-jala"]["wire_api"], "responses")
        self.assertEqual(parsed["model_providers"]["9router-jala"]["experimental_bearer_token"], 'key"\\value')
        self.assertIn("# retain this note", merged)

    def test_codex_config_merge_establishes_provider_auth_for_existing_chatgpt_sign_in(self):
        merged = gateway.merge_codex_config('forced_login_method = "chatgpt"\n', "/tmp/models.json", "test-auth-secret")
        document = gateway.tomllib.loads(merged)
        self.assertEqual(document["forced_login_method"], "chatgpt")
        self.assertTrue(document["model_providers"]["9router-jala"]["requires_openai_auth"])
        self.assertEqual(document["model_providers"]["9router-jala"]["experimental_bearer_token"], "test-auth-secret")

    def test_codex_config_merge_keeps_existing_provider_chatgpt_auth_without_login_restriction(self):
        existing = '[model_providers.9router-jala]\nrequires_openai_auth = true\n'
        merged = gateway.merge_codex_config(existing, "/tmp/models.json", "test-auth-secret")
        document = gateway.tomllib.loads(merged)
        self.assertEqual(document["forced_login_method"], "chatgpt")
        self.assertTrue(document["model_providers"]["9router-jala"]["requires_openai_auth"])

    def test_codex_config_merge_uses_toml_structure_not_header_looking_string_content(self):
        existing = '''prompt = """
[model_providers.9router-jala]
model = "keep this string content"
"""

[other]
model = "keep this table value"
'''
        merged = gateway.merge_codex_config(existing, "/tmp/codex/models_9router_jala.json", "test-secret")
        parsed = gateway.tomllib.loads(merged)
        self.assertEqual(parsed["prompt"], '[model_providers.9router-jala]\nmodel = "keep this string content"\n')
        self.assertEqual(parsed["other"]["model"], "keep this table value")
        self.assertEqual(parsed["model"], "9router-jala")
        self.assertEqual(parsed["model_providers"]["9router-jala"]["experimental_bearer_token"], "test-secret")

    def test_codex_config_merge_rejects_invalid_toml(self):
        with self.assertRaisesRegex(ValueError, "valid TOML"):
            gateway.merge_codex_config("[invalid", "/tmp/models.json", "test-secret")

    def test_configure_codex_leaves_invalid_config_untouched(self):
        root = Path(self.temporary.name) / "codex-home"
        root.mkdir()
        config = root / "config.toml"
        config.write_text("model = [\n")
        with patch.dict(os.environ, {"CODEX_HOME": str(root)}), self.assertRaisesRegex(ValueError, "valid TOML"):
            gateway.configure_codex("test-codex-secret")
        self.assertEqual(config.read_text(), "model = [\n")
        self.assertFalse((root / "9router-jala").exists())

    def test_codex_setup_rejects_invalid_config_before_opening_key_form(self):
        root = Path(self.temporary.name) / "codex-home"
        root.mkdir()
        config = root / "config.toml"
        config.write_text("model = [\n")
        with patch.dict(os.environ, {"CODEX_HOME": str(root)}), self.assertRaisesRegex(ValueError, "valid TOML"):
            gateway.setup_server(configure=True)
        self.assertEqual(config.read_text(), "model = [\n")
        self.assertFalse((root / "models_9router_jala.json").exists())

    def test_configure_codex_installs_bundled_catalog_and_private_config(self):
        root = Path(self.temporary.name) / "codex-home"
        root.mkdir()
        root.chmod(0o755)
        with patch.dict(os.environ, {"CODEX_HOME": str(root)}):
            config_path = gateway.configure_codex("test-codex-secret")
        parsed = gateway.tomllib.loads(config_path.read_text())
        provider = parsed["model_providers"]["9router-jala"]
        self.assertEqual(parsed["model"], "9router-jala")
        self.assertEqual(parsed["model_provider"], "9router-jala")
        self.assertNotIn("preferred_auth_method", parsed)
        self.assertEqual(parsed["forced_login_method"], "chatgpt")
        self.assertEqual(parsed["model_reasoning_effort"], "high")
        self.assertEqual(provider["name"], "9Router JALA")
        self.assertEqual(provider["base_url"], "https://9router.jala.tech/v1")
        self.assertEqual(provider["wire_api"], "responses")
        self.assertTrue(provider["requires_openai_auth"])
        self.assertEqual(provider["experimental_bearer_token"], "test-codex-secret")
        self.assertEqual(parsed["model_catalog_json"], str(root.resolve() / "models_9router_jala.json"))
        catalog = json.loads(Path(parsed["model_catalog_json"]).read_text())
        self.assertNotIn("fetched_at", catalog)
        self.assertNotIn("etag", catalog)
        self.assertNotIn("client_version", catalog)
        model = next(item for item in catalog["models"] if item["slug"] == "9router-jala")
        self.assertNotIn("GPT-", model["description"])
        self.assertEqual(config_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(Path(parsed["model_catalog_json"]).stat().st_mode & 0o777, 0o600)
        self.assertEqual(root.stat().st_mode & 0o777, 0o755)

    def test_codex_web_setup_configures_provider_after_key_verification(self):
        root = Path(self.temporary.name) / "codex-home"
        root.mkdir()
        (root / "config.toml").write_text('preferred_auth_method = "custom-auth"\n')
        with patch.dict(os.environ, {"CODEX_HOME": str(root)}), patch.object(gateway, "send", return_value=(b'{"data":[]}', "application/json")) as send:
            with gateway.setup_server(configure=True) as server:
                worker = threading.Thread(target=server.handle_request)
                worker.start()
                with self.post_setup(server, "test-codex-web-secret") as response:
                    body = response.read()
                    self.assertEqual(response.status, 200)
                    self.assertNotIn(b"test-codex-web-secret", body)
                    self.assertIn(b"Unsupported preferred_auth_method was retained", body)
                worker.join(timeout=5)
                self.assertTrue(server.completed)
            config = gateway.tomllib.loads((root / "config.toml").read_text())
            self.assertEqual(config["preferred_auth_method"], "custom-auth")
            self.assertEqual(config["forced_login_method"], "chatgpt")
            self.assertTrue(config["model_providers"]["9router-jala"]["requires_openai_auth"])
            self.assertEqual(config["model_providers"]["9router-jala"]["experimental_bearer_token"], "test-codex-web-secret")
            self.assertEqual(self.values[(gateway.KEYRING_SERVICE, gateway.KEYRING_ACCOUNT)], "test-codex-web-secret")
            send.assert_called_once_with("/v1/models", "test-codex-web-secret")

    def test_codex_web_form_respects_command_auth_mode_without_payload_choice(self):
        root = Path(self.temporary.name) / "codex-home"
        with patch.dict(os.environ, {"CODEX_HOME": str(root)}), patch.object(gateway, "send", return_value=(b'{"data":[]}', "application/json")):
            for mode in ("api", "chatgpt"):
                with self.subTest(mode=mode), gateway.setup_server(configure=True, auth_mode=mode) as server:
                    worker = threading.Thread(target=server.handle_request)
                    worker.start()
                    try:
                        with self.post_setup(server, "test-command-mode-secret") as response:
                            self.assertEqual(response.status, 200)
                    finally:
                        worker.join(timeout=5)
                    config = gateway.tomllib.loads((root / "config.toml").read_text())
                    self.assertEqual(config["forced_login_method"], mode)
                    self.assertEqual(config["model_providers"]["9router-jala"]["requires_openai_auth"], mode == "chatgpt")

    def test_codex_web_setup_supports_explicit_auth_mode_choices(self):
        root = Path(self.temporary.name) / "codex-home"
        with patch.dict(os.environ, {"CODEX_HOME": str(root)}), patch.object(gateway, "send", return_value=(b'{"data":[]}', "application/json")):
            for mode in ("chatgpt", "api"):
                with self.subTest(mode=mode), gateway.setup_server(configure=True) as server:
                    worker = threading.Thread(target=server.handle_request)
                    worker.start()
                    try:
                        with self.post_setup(server, "test-mode-web-secret", auth_mode=mode) as response:
                            self.assertEqual(response.status, 200)
                            self.assertNotIn(b"test-mode-web-secret", response.read())
                    finally:
                        worker.join(timeout=5)
                    config = gateway.tomllib.loads((root / "config.toml").read_text())
                    self.assertEqual(config["forced_login_method"], mode)
                    self.assertEqual(config["model_providers"]["9router-jala"]["requires_openai_auth"], mode == "chatgpt")
                    self.assertEqual(config["model_providers"]["9router-jala"]["experimental_bearer_token"], "test-mode-web-secret")

    def test_codex_web_setup_rejects_unknown_auth_modes_before_verifying_or_saving(self):
        root = Path(self.temporary.name) / "codex-home"
        root.mkdir()
        config = root / "config.toml"
        original = 'forced_login_method = "chatgpt"\n'
        config.write_text(original)
        with patch.dict(os.environ, {"CODEX_HOME": str(root)}), patch.object(gateway, "send") as send:
            with gateway.setup_server(configure=True) as server:
                for mode in ("invalid", ["chatgpt"], {"mode": "api"}):
                    with self.subTest(mode=mode):
                        worker = threading.Thread(target=server.handle_request)
                        worker.start()
                        try:
                            with self.assertRaises(urllib.error.HTTPError) as caught:
                                self.post_setup(server, "test-invalid-mode-secret", auth_mode=mode)
                            self.assertEqual(caught.exception.code, 400)
                            self.assertNotIn(b"test-invalid-mode-secret", caught.exception.read())
                        finally:
                            worker.join(timeout=5)
                        self.assertFalse(server.completed)
                        self.assertEqual(config.read_text(), original)
                        self.assertEqual(self.values, {})
                        self.assertFalse((root / "models_9router_jala.json").exists())
                send.assert_not_called()

    def test_codex_setup_form_discloses_plaintext_storage_and_restart(self):
        root = Path(self.temporary.name) / "codex-home"
        with patch.dict(os.environ, {"CODEX_HOME": str(root)}):
            with gateway.setup_server(configure=True) as server:
                worker = threading.Thread(target=server.handle_request)
                worker.start()
                with urllib.request.urlopen(server.setup_url.split("#")[0], timeout=5) as response:
                    page = response.read()
                worker.join(timeout=5)
        self.assertIn(b"const configureCodex = true", page)
        self.assertIn(b"stored as plaintext in Codex config.toml", page)
        self.assertIn(b"Restart Codex to apply the settings", page)
        self.assertNotIn(b"Codex sign-in", page)
        self.assertNotIn(b"<select", page)
        self.assertNotIn(b"authMode", page)
        self.assertNotIn(b"__CONFIGURE__", page)
        self.assertNotIn(b"__AUTH_MODE__", page)

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

    def test_validation_error_exposes_diagnostics_and_redacts_secrets(self):
        import json
        payload = {"error": {"message": "Unsupported size; key=test-secret; api_key=other-private; Bearer hidden-token; sk-provider-secret " + "A" * 100, "code": "invalid_size", "type": "invalid_request_error", "param": "size", "api_key": "other-private", "b64_json": "A" * 100}, "request": {"Authorization": "Bearer hidden-token"}}
        error = urllib.error.HTTPError(gateway.GATEWAY + "/v1/images/generations", 400, "rejected", {}, io.BytesIO(json.dumps(payload).encode()))
        with patch.object(gateway.urllib.request, "build_opener") as builder:
            builder.return_value.open.side_effect = error
            with self.assertRaises(ValueError) as caught:
                gateway.send("/v1/images/generations", "test-secret", {"prompt": "car"})
            message = str(caught.exception)
            for expected in ("Unsupported size", "invalid_size", "param: size", "Correct the rejected inputs"):
                self.assertIn(expected, message)
            for secret in ("test-secret", "other-private", "hidden-token", "sk-provider-secret", "A" * 100):
                self.assertNotIn(secret, message)
            builder.return_value.open.assert_called_once()

    def test_unstructured_and_oversized_errors_are_suppressed(self):
        for raw in (b"<html>private backend dump</html>", b"not-json", b'[]', b'{"error":"private"}', b"x" * 16385):
            with self.subTest(raw=raw[:20]):
                error = urllib.error.HTTPError(gateway.GATEWAY + "/v1/models", 502, "failed", {}, io.BytesIO(raw))
                self.assertEqual(gateway.safe_error_details(error, "test-secret"), "")

    def test_error_fields_are_bounded_and_unknown_fields_omitted(self):
        import json
        raw = json.dumps({"error": {"message": "word " * 300, "param": "size", "debug": "private dump", "headers": {"Authorization": "private"}}}).encode()
        error = urllib.error.HTTPError(gateway.GATEWAY + "/v1/models", 422, "rejected", {}, io.BytesIO(raw))
        details = gateway.safe_error_details(error, "test-secret")
        self.assertLessEqual(len(details), 430)
        self.assertIn("param: size", details)
        self.assertNotIn("private", details)

    def test_timeout_does_not_retry(self):
        with patch.object(gateway.urllib.request, "build_opener") as builder:
            builder.return_value.open.side_effect = TimeoutError()
            with self.assertRaisesRegex(ValueError, "timed out; request was not retried"):
                gateway.send("/v1/images/generations", "test-secret", {"prompt": "car"})
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


class UpstreamCopiesTests(unittest.TestCase):
    def test_vendored_upstream_files_match_pinned_hashes(self):
        import hashlib
        import json
        root = Path(__file__).parents[1]
        manifest = json.loads((root / "upstream.json").read_text())
        self.assertEqual(len(manifest["adapted_files"]), 8)
        for name, digest in manifest["files"].items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest)


    def test_capability_adaptations_preserve_upstream_content(self):
        import hashlib
        import json
        root = Path(__file__).parents[1]
        manifest = json.loads((root / "upstream.json").read_text())
        original = 'Requires `NINEROUTER_URL` (and `NINEROUTER_KEY` if auth enabled). See https://raw.githubusercontent.com/decolua/9router/refs/heads/master/skills/9router/SKILL.md for setup.'
        setup_template = 'Before execution, including direct invocation, read [JALA instructions](../9router/SKILL.md)\nand its required references for credentials, model defaults, and retry rules.\nUse `gateway.py run SKILL_NAME --body request.json` with the helper resolved as\ninstructed there; omit `model` to use the configured default. The JALA instructions\nand allowed models take precedence over the generic examples below.'
        capabilities = [name for name in manifest["adapted_files"] if name != "skills/9router/SKILL.md"]
        self.assertEqual(len(capabilities), 7)
        for name in capabilities:
            with self.subTest(file=name):
                text = (root / name).read_text()
                setup = setup_template.replace("SKILL_NAME", Path(name).parent.name)
                self.assertEqual(text.count(setup), 1)
                self.assertTrue((root / name).parent.joinpath("../9router/SKILL.md").is_file())
                restored = text.replace(setup, original).encode()
                self.assertEqual(hashlib.sha256(restored).hexdigest(), manifest["adapted_files"][name]["upstream_sha256"])


if __name__ == "__main__":
    unittest.main()
