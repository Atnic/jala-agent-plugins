import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request


spec = importlib.util.spec_from_file_location("gateway_lifecycle", Path(__file__).parents[1] / "scripts" / "gateway.py")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


class CodexLifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.root = self.home / "codex"
        self.root.mkdir()
        self.config = self.root / "config.toml"
        self.catalog = self.root / "models_9router_jala.json"
        self.values = {}
        store = Mock()
        store.get_password.side_effect = lambda *args: self.values.get("key")
        store.set_password.side_effect = lambda *args: self.values.update(key=args[-1])
        store.delete_password.side_effect = lambda *args: self.values.pop("key", None)
        self.store = store
        for context in (
            patch.object(gateway.Path, "home", return_value=self.home),
            patch.dict(os.environ, {"CODEX_HOME": str(self.root)}, clear=True),
            patch.object(gateway, "credential_store", return_value=store),
            patch.object(gateway, "send", return_value=(b'{"data":[]}', "application/json")),
            patch.object(gateway.sys, "platform", "freebsd"),
        ):
            context.start()
            self.addCleanup(context.stop)

    def command(self, *args):
        output, error = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["gateway.py", *args]), patch.object(sys, "stdout", output), patch.object(sys, "stderr", error):
            result = gateway.main()
        return result, output.getvalue(), error.getvalue()

    def test_setup_then_revert_preserves_unrelated_configuration_and_saved_key(self):
        self.config.write_text('approval_policy = "on-request" # keep this note\n\n[model_providers.other]\nbase_url = "https://example.test/v1"\n')
        self.values["key"] = "test-lifecycle-secret"
        self.assertEqual(self.command("setup-codex", "--reuse-saved-key")[0], 0)
        result, output, error = self.command("revert-codex")
        self.assertEqual((result, error), (0, ""))
        document = gateway.tomllib.loads(self.config.read_text())
        self.assertEqual(document, {"approval_policy": "on-request", "model_providers": {"other": {"base_url": "https://example.test/v1"}}})
        self.assertIn("# keep this note", self.config.read_text())
        self.assertEqual(self.values["key"], "test-lifecycle-secret")
        self.assertTrue(self.catalog.exists())
        self.assertIn("restart Codex", output)
        self.assertNotIn("test-lifecycle-secret", output + error)

    def test_repeated_revert_is_a_noop_without_accessing_credentials(self):
        self.values["key"] = "test-repeat-secret"
        self.assertEqual(self.command("setup-codex", "--reuse-saved-key")[0], 0)
        self.assertEqual(self.command("revert-codex")[0], 0)
        before = self.config.read_bytes()
        self.store.get_password.side_effect = RuntimeError("store locked")
        result, output, error = self.command("revert-codex")
        self.assertEqual((result, error), (0, ""))
        self.assertIn("already reverted", output)
        self.assertEqual(self.config.read_bytes(), before)
        self.config.unlink()
        self.assertEqual(self.command("revert-codex")[0], 0)
        self.assertFalse(self.config.exists())

    def test_revert_refuses_conflicting_saved_credentials(self):
        for location in ("native", "fallback"):
            with self.subTest(location=location):
                self.values["key"] = "test-config-secret"
                self.assertEqual(self.command("setup-codex", "--reuse-saved-key")[0], 0)
                if location == "native":
                    self.values["key"] = "test-different-secret"
                else:
                    gateway.save_plaintext_key("test-different-secret")
                before = self.config.read_bytes()
                result, output, error = self.command("revert-codex")
                self.assertEqual(result, 1)
                self.assertIn("different", error)
                self.assertEqual(self.config.read_bytes(), before)
                self.assertNotIn("test-config-secret", output + error)
                self.assertNotIn("test-different-secret", output + error)
                gateway.credential_path().unlink(missing_ok=True)

    def test_revert_preserves_custom_values_and_reports_profiles_on_every_run(self):
        self.values["key"] = "test-profile-secret"
        self.assertEqual(self.command("setup-codex", "--reuse-saved-key")[0], 0)
        document = gateway.tomlkit.parse(self.config.read_text())
        document["model"] = "custom-model"
        document["model_reasoning_effort"] = "low"
        document["preferred_auth_method"] = "custom-auth"
        document["model_catalog_json"] = str(self.root / "custom-models.json")
        document["profiles"] = {"research": {"model_provider": "9router-jala", "model_catalog_json": str(self.catalog)}}
        self.config.write_text(gateway.tomlkit.dumps(document))
        for _ in range(2):
            result, output, error = self.command("revert-codex")
            self.assertEqual((result, error), (0, ""))
            parsed = gateway.tomllib.loads(self.config.read_text())
            self.assertEqual(parsed["model"], "custom-model")
            self.assertEqual(parsed["model_reasoning_effort"], "low")
            self.assertEqual(parsed["preferred_auth_method"], "custom-auth")
            self.assertEqual(parsed["model_catalog_json"], str(self.root / "custom-models.json"))
            self.assertEqual(parsed["profiles"]["research"]["model_provider"], "9router-jala")
            self.assertIn("profiles.research.model_provider", output)
            self.assertIn("profiles.research.model_catalog_json", output)
            self.assertNotIn("test-profile-secret", output + error)

    def test_revert_rejects_malformed_configuration_without_touching_credentials(self):
        for text in ('test-malformed-secret = [\n', 'model_providers = "test-malformed-secret"\n', '[model_providers]\n9router-jala = "test-malformed-secret"\n'):
            with self.subTest(text=text):
                self.config.write_text(text)
                self.store.get_password.side_effect = RuntimeError("test-locked-secret")
                result, output, error = self.command("revert-codex")
                self.assertEqual(result, 1)
                self.assertIn("left unchanged", error)
                self.assertEqual(self.config.read_text(), text)
                self.assertEqual(self.values, {})
                self.assertNotIn("test-malformed-secret", output + error)
                self.assertNotIn("test-locked-secret", output + error)

    def test_saved_key_setup_preflights_configuration_before_replacing_credentials(self):
        self.config.write_text('model = [\n')
        self.values["key"] = "test-original-secret"
        with patch.dict(os.environ, {"NINEROUTER_KEY": "test-new-secret"}):
            result, output, error = self.command("setup-codex", "--reuse-saved-key")
        self.assertEqual(result, 1)
        self.assertIn("valid TOML", error)
        self.assertEqual(self.values["key"], "test-original-secret")
        self.assertEqual(self.config.read_text(), 'model = [\n')
        self.assertFalse(self.catalog.exists())
        self.assertNotIn("test-new-secret", output + error)

    def test_setup_reports_partial_completion_and_retains_key_when_files_fail(self):
        replace = os.replace
        for failed_file in (self.catalog, self.config):
            with self.subTest(failed_file=failed_file.name):
                self.config.write_text('approval_policy = "on-request"\n')
                self.catalog.write_text('{"original": true}')
                self.values["key"] = "test-original-secret"

                def fail_replace(source, destination):
                    if Path(destination).resolve() == failed_file.resolve():
                        raise OSError("test-private-filesystem-secret")
                    return replace(source, destination)

                with patch.dict(os.environ, {"NINEROUTER_KEY": "test-retry-secret"}), patch.object(gateway.os, "replace", side_effect=fail_replace):
                    result, output, error = self.command("setup-codex", "--reuse-saved-key")
                self.assertEqual(result, 1)
                self.assertIn("Credential verified and saved", error)
                self.assertIn("Codex configuration unchanged", error)
                self.assertEqual(self.values["key"], "test-retry-secret")
                self.assertEqual(self.config.read_text(), 'approval_policy = "on-request"\n')
                if failed_file == self.catalog:
                    self.assertIn("Model catalog unchanged", error)
                    self.assertEqual(json.loads(self.catalog.read_text()), {"original": True})
                else:
                    self.assertIn("Model catalog updated", error)
                    self.assertIn("models", json.loads(self.catalog.read_text()))
                self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["config.toml", "models_9router_jala.json"])
                for secret in ("test-private-filesystem-secret", "test-retry-secret", "test-original-secret"):
                    self.assertNotIn(secret, output + error)

    def test_browser_setup_reports_saved_credential_when_configuration_write_fails(self):
        replace = os.replace

        def fail_config(source, destination):
            if Path(destination).resolve() == self.config.resolve():
                raise OSError("test-private-filesystem-secret")
            return replace(source, destination)

        with gateway.setup_server(configure=True) as server, patch.object(gateway.os, "replace", side_effect=fail_config):
            worker = threading.Thread(target=server.handle_request)
            worker.start()
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}{server.setup_endpoint}",
                data=b'{"key":"test-browser-secret"}',
                headers={"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{server.server_port}", "X-Setup-Token": server.setup_url.split("token=")[1]},
            )
            try:
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=5)
                body = caught.exception.read()
            finally:
                worker.join(timeout=5)
            self.assertEqual(caught.exception.code, 400)
            self.assertFalse(server.completed)
        self.assertIn("Credential verified and saved", json.loads(body)["error"])
        self.assertIn("Model catalog updated", json.loads(body)["error"])
        self.assertEqual(self.values["key"], "test-browser-secret")
        self.assertFalse(self.config.exists())
        self.assertNotIn(b"test-browser-secret", body)
        self.assertNotIn(b"test-private-filesystem-secret", body)

    def test_lifecycle_refuses_symlinked_home_and_configuration(self):
        self.config.write_text('approval_policy = "on-request"\n')
        self.values["key"] = "test-symlink-secret"
        link = self.home / "linked-codex"
        link.symlink_to(self.root, target_is_directory=True)
        for command in (("setup-codex", "--reuse-saved-key"), ("revert-codex",), ("backup-codex-key",)):
            with self.subTest(command=command), patch.dict(os.environ, {"CODEX_HOME": str(link)}):
                result, output, error = self.command(*command)
                self.assertEqual(result, 1)
                self.assertIn("symlink", error)
                self.assertEqual(self.config.read_text(), 'approval_policy = "on-request"\n')
                self.assertFalse(self.catalog.exists())
                self.assertNotIn("test-symlink-secret", output + error)
        original = self.home / "original.toml"
        self.config.rename(original)
        self.config.symlink_to(original)
        for command in (("setup-codex", "--reuse-saved-key"), ("revert-codex",)):
            result, _, error = self.command(*command)
            self.assertEqual(result, 1)
            self.assertIn("symlink", error)
            self.assertEqual(original.read_text(), 'approval_policy = "on-request"\n')

    def test_revert_write_failure_preserves_configuration_and_backed_up_key(self):
        original = 'model_provider = "9router-jala"\n[model_providers.9router-jala]\nexperimental_bearer_token = "test-revert-secret"\n'
        self.config.write_text(original)
        with patch.object(gateway.os, "replace", side_effect=OSError("test-private-filesystem-secret")):
            result, output, error = self.command("revert-codex")
        self.assertEqual(result, 1)
        self.assertIn("Plugin credential preserved", error)
        self.assertIn("Codex configuration unchanged", error)
        self.assertEqual(self.config.read_text(), original)
        self.assertEqual(self.values["key"], "test-revert-secret")
        self.assertEqual(list(self.root.iterdir()), [self.config])
        self.assertNotIn("test-revert-secret", output + error)
        self.assertNotIn("test-private-filesystem-secret", output + error)

    def test_revert_stops_when_native_credential_preservation_cannot_be_verified(self):
        original = 'model_provider = "9router-jala"\n[model_providers.9router-jala]\nexperimental_bearer_token = "test-preserve-secret"\n'
        for failure in ("locked", "readback", "invalid-saved-key"):
            with self.subTest(failure=failure):
                self.config.write_text(original)
                self.values.clear()
                if failure == "locked":
                    self.store.get_password.side_effect = RuntimeError("test-locked-secret")
                elif failure == "readback":
                    self.store.get_password.side_effect = lambda *args: None
                else:
                    self.store.get_password.side_effect = lambda *args: "test-invalid-\u00e9-secret"
                result, output, error = self.command("revert-codex")
                self.assertEqual(result, 1)
                self.assertEqual(self.config.read_text(), original)
                self.assertFalse(gateway.credential_path().exists())
                for secret in ("test-preserve-secret", "test-locked-secret", "test-invalid-\u00e9-secret"):
                    self.assertNotIn(secret, output + error)

    def test_setup_reports_uncertain_credential_storage_without_changing_configuration(self):
        self.config.write_text('approval_policy = "on-request"\n')
        self.store.get_password.side_effect = lambda *args: None
        with patch.dict(os.environ, {"NINEROUTER_KEY": "test-uncertain-secret"}), patch.object(gateway.os, "replace", side_effect=OSError("test-private-error")):
            result, output, error = self.command("setup-codex", "--reuse-saved-key")
        self.assertEqual(result, 1)
        self.assertIn("credential storage could not be confirmed", error)
        self.assertIn("Codex configuration unchanged", error)
        self.assertEqual(self.config.read_text(), 'approval_policy = "on-request"\n')
        self.assertFalse(self.catalog.exists())
        self.assertNotIn("test-uncertain-secret", output + error)
        self.assertNotIn("test-private-error", output + error)

    def test_backup_command_remains_compatible_and_does_not_edit_configuration(self):
        original = '[model_providers.9router-jala]\nexperimental_bearer_token = "test-backup-secret"\n'
        self.config.write_text(original)
        result, output, error = self.command("backup-codex-key")
        self.assertEqual((result, error), (0, ""))
        self.assertEqual(self.values["key"], "test-backup-secret")
        self.assertEqual(self.config.read_text(), original)
        self.assertNotIn("test-backup-secret", output)
        self.assertEqual(self.command("revert-codex")[0], 0)

    def test_revert_preserves_global_settings_when_another_provider_is_active(self):
        self.values["key"] = "test-inactive-secret"
        self.assertEqual(self.command("setup-codex", "--reuse-saved-key")[0], 0)
        document = gateway.tomlkit.parse(self.config.read_text())
        document["model_provider"] = "other"
        self.config.write_text(gateway.tomlkit.dumps(document))
        result, output, error = self.command("revert-codex")
        self.assertEqual((result, error), (0, ""))
        document = gateway.tomllib.loads(self.config.read_text())
        self.assertEqual(document["model_provider"], "other")
        self.assertEqual(document["model"], "9router-jala")
        self.assertEqual(document["preferred_auth_method"], "apikey")
        self.assertEqual(document["forced_login_method"], "api")
        self.assertEqual(document["model_reasoning_effort"], "high")
        self.assertNotIn("model_catalog_json", document)
        self.assertNotIn("9router-jala", document.get("model_providers", {}))
        self.assertIn('"model"', output)

    def test_orphaned_owned_settings_require_credential_preservation(self):
        for original in ('model_provider = "9router-jala"\n', f'model_catalog_json = {json.dumps(str(self.catalog.resolve()))}\n'):
            with self.subTest(original=original):
                self.config.write_text(original)
                result, _, error = self.command("revert-codex")
                self.assertEqual(result, 1)
                self.assertIn("valid 9Router key", error)
                self.assertEqual(self.config.read_text(), original)


if __name__ == "__main__":
    unittest.main()
